"""The AI tutor for the authenticated learner. No HTTP and no SQL in here.

What the tutor may know: the learner's own target language and CEFR level, their age group (as a mode, never the date of birth),
the lesson/situation/topic the conversation is about, and short facts drawn from the SAME services the learner can already see
(weaknesses, confidence, recent mistakes, activity counts). It is never given a name, e-mail, id, password, session, recording,
parent data or anyone else's information. The facts are stored with each reply, so they are shown apart from the generated advice.

What it is sent is bounded: the last few messages, at most 8 facts and 5 phrases, and a hard character limit on the whole prompt,
however long the stored conversation is. Children get only built-in helper questions answered by the built-in provider: no free
text, no external model. If the provider fails, nothing is stored and the learner can simply try again."""
import sqlite3

from .. import settings
from ..ai import registry, runner
from ..ai.base import AiError, TutorRequest, clean
from ..ai.mock import QUICK_PROMPTS
from ..db import connect
from ..personalization import clock, confidence, weaknesses
from ..personalization.context import Forbidden, InvalidInput, NeedsProfile, NotFound, learner_context  # noqa: F401  (re-exported)
from ..repositories import adaptive as adaptive_repo, curriculum, learner as learner_repo, parent as parent_repo, personalization as pers_repo, situations, speaking as speaking_repo, tutor as repo

LIST_LIMIT = 50
MAX_PHRASES = 5
MAX_MISTAKES = 2


class Conflict(Exception):
    pass


class AiUnavailable(Exception):
    """The provider failed. Nothing was stored; the learner can try again."""


def _mode(ctx):
    return ctx["age_group_code"]


def _language(conn, ctx, user_id):
    name = conn.execute("SELECT name FROM languages WHERE id = ?", (ctx["target_language_id"],)).fetchone()["name"]
    return name, learner_repo.get_profile(conn, user_id)["cefr_level"]


# ---------- views ----------
def _conv_view(c):
    context = None
    if c["lesson_id"]:
        context = {"type": "lesson", "id": c["lesson_id"]}
    elif c["situation_id"]:
        context = {"type": "situation", "id": c["situation_id"]}
    elif c["topic_id"]:
        context = {"type": "topic", "slug": c["topic_slug"]}
    return {"id": c["id"], "title": c["title"], "mode": c["mode"], "status": c["status"], "message_count": c["message_count"], "context": context,
            "created_at": c["created_at"], "updated_at": c["updated_at"]}


def _msg_view(m):
    out = {"seq": m["seq"], "role": m["role"], "content": m["content"], "created_at": m["created_at"]}
    if m["role"] == "tutor":
        out["generated"] = True
        out["provider"] = m["provider"]
    elif m.get("quick_prompt"):
        out["quick_prompt"] = m["quick_prompt"]
    return out


def quick_prompts():
    return [{"key": k, "text": t} for k, t in QUICK_PROMPTS.items()]


# ---------- conversations ----------
def create_conversation(db_path, user_id, *, lesson_id=None, situation_id=None, topic=None):
    with connect(db_path) as conn:
        ctx = learner_context(conn, user_id)
        if repo.count_conversations(conn, user_id) >= settings.AI_MAX_CONVERSATIONS_PER_LEARNER:
            raise Conflict("You have a lot of conversations already. Please continue one of them.")
        lang, rank, age = ctx["target_language_id"], ctx["max_rank"], ctx["age_group_id"]
        title, topic_id = "Chat with your tutor", None
        if lesson_id is not None:
            found = curriculum.get_available_lesson(conn, lesson_id, lang, rank, age)
            if found is None:
                raise NotFound()
            title = found["title"]
        elif situation_id is not None:
            found = situations.get_available(conn, situation_id, lang, rank, age)
            if found is None:
                raise NotFound()
            title = found["title"]
        elif topic is not None:
            t = pers_repo.get_topic(conn, topic)
            if t is None or t["id"] not in {x["id"] for x in pers_repo.topics_with_content(conn, lang, rank, age)}:
                raise InvalidInput("topic", "Unknown topic")
            title, topic_id = t["name"], t["id"]
        _, cefr = _language(conn, ctx, user_id)
        now = clock.now()
        cid = repo.create_conversation(conn, user_id, lang, cefr, _mode(ctx), topic_id, lesson_id, situation_id, title[:80], now)
        view = _conv_view(repo.get_conversation(conn, user_id, cid))
    return {"conversation": view, "quick_prompts": quick_prompts() if _mode(ctx) == "child" else None}


def list_conversations(db_path, user_id):
    with connect(db_path) as conn:
        learner_context(conn, user_id)
        return [_conv_view(c) for c in repo.list_conversations(conn, user_id, LIST_LIMIT)]


def get_conversation(db_path, user_id, conversation_id):
    with connect(db_path) as conn:
        ctx = learner_context(conn, user_id)
        c = repo.get_conversation(conn, user_id, conversation_id)
        if c is None:
            raise NotFound()
        return {"conversation": _conv_view(c), "quick_prompts": quick_prompts() if _mode(ctx) == "child" else None}


def get_messages(db_path, user_id, conversation_id, after_seq=0, limit=50):
    with connect(db_path) as conn:
        learner_context(conn, user_id)
        if repo.get_conversation(conn, user_id, conversation_id) is None:
            raise NotFound()
        return [_msg_view(m) for m in repo.list_messages(conn, user_id, conversation_id, after_seq, limit)]


# ---------- what the tutor is told ----------
def _phrases(conn, ctx):
    ids = sorted(speaking_repo.available_prompts(conn, ctx["target_language_id"], ctx["max_rank"], ctx["age_group_id"]))[:30]
    items = situations.items_by_ids(conn, ids, ctx["native_language_id"], ctx["fallback_id"])
    return [{"text": items[i]["text"], "pronunciation": items[i]["pronunciation"], "meaning": items[i]["meaning"]} for i in ids if i in items and items[i]["meaning"]]


def _facts(db_path, user_id, ctx, title):
    """Short stored facts about THIS learner from the services they can already see. Never invented, never another learner's."""
    facts = []
    if title and title != "Chat with your tutor":
        facts.append(("context", f"The conversation is about: {title}"))
    for w in (weaknesses.list_weaknesses(db_path, user_id) or [])[:3]:
        if w["rule"] == "low_topic_accuracy":
            facts.append(("weakness", f"Weak topic: {w['topic']['name']} ({w['attempts'] - w['incorrect']} of the last {w['attempts']} answers were correct)"))
        else:
            it = w["item"]
            facts.append(("weakness", f"Often answered wrongly: {it['text']} ({it['pronunciation']}) means “{it['meaning']}”"))
    over = confidence.overview(db_path, user_id)
    rated = sorted((t for t in over["topics"] if t["confidence"]), key=lambda t: (t["confidence"]["score"], t["topic"]["name"]))[:2]
    for t in rated:
        facts.append(("confidence", f"Self-rated confidence in {t['topic']['name']}: {t['confidence']['score']}%"))
    with connect(db_path) as conn:
        weak_text = {f[1] for f in facts}
        mistakes = situations.items_by_ids(conn, repo.recent_mistake_items(conn, user_id, ctx["target_language_id"], MAX_MISTAKES), ctx["native_language_id"], ctx["fallback_id"])
        for it in mistakes.values():
            line = f"Recent mistake: {it['text']} ({it['pronunciation']}) means “{it['meaning']}”"
            if not any(it["text"] in w for w in weak_text):
                facts.append(("mistake", line))
        by_source = parent_repo.activity_by_source(conn, user_id, ctx["target_language_id"])
        rec = adaptive_repo.top_active_recommendation(conn, user_id, clock.today())
        if rec:                                                                  # one stored, evidence-backed suggestion (Phase 12), quoted as a stored fact
            facts.append(("context", f"Suggested next step (from your learning plan): {rec['title']}. {rec['reason']}"))
    attempts = sum(s["attempts"] for s in by_source.values())
    if attempts:
        correct = sum(s["correct"] or 0 for s in by_source.values())
        facts.append(("activity", f"So far {correct} of {attempts} answers in lessons, situations and listening were correct"))
    return [(k, t[:300]) for k, t in facts][:settings.AI_MAX_FACTS]


def _bounded(req):
    """Trims the oldest history until the whole prompt fits, so a long stored history can never become an unlimited prompt."""
    history = list(req.history)

    def size(h):
        return (len(req.message) + sum(len(f) for f in req.facts) + sum(len(t) for _, t in h)
                + sum(len(p["text"]) + len(p["meaning"]) + len(p.get("pronunciation") or "") for p in req.phrases))
    while history and size(history) > settings.AI_MAX_PROMPT_CHARS:
        history.pop(0)
    return TutorRequest(**{**req.__dict__, "history": tuple(history)})


# ---------- messages ----------
def _validate_input(mode, message, quick_prompt):
    if mode == "child":
        if message is not None or quick_prompt is None:
            raise InvalidInput("quick_prompt", "Choose one of the helper questions")
        if quick_prompt not in QUICK_PROMPTS:
            raise InvalidInput("quick_prompt", "Choose one of the helper questions")
        return QUICK_PROMPTS[quick_prompt], quick_prompt
    if quick_prompt is not None or message is None:
        raise InvalidInput("message", "Type a message")
    text = message.strip()
    if not text or len(text) > settings.AI_MAX_MESSAGE_CHARS:
        raise InvalidInput("message", f"A message must be 1-{settings.AI_MAX_MESSAGE_CHARS} characters")
    return text, None


def _reply_view(learner_msg, tutor_msg, facts, replayed=False):
    return {"message": _msg_view(learner_msg), "reply": _msg_view(tutor_msg), "facts": facts, "replayed": replayed}


def send_message(db_path, user_id, conversation_id, *, message=None, quick_prompt=None, client_id=None):
    # --- step 1 (read): validate, replay check, gather the bounded context ---
    with connect(db_path) as conn:
        ctx = learner_context(conn, user_id)
        conv = repo.get_conversation(conn, user_id, conversation_id)
        if conv is None:
            raise NotFound()
        mode = _mode(ctx)
        text, quick = _validate_input(mode, message, quick_prompt)
        if client_id is not None:
            stored = repo.find_by_client_id(conn, user_id, conversation_id, client_id)
            if stored and stored[1]:
                return _reply_view({**stored[0], "role": "learner"}, {**stored[1], "role": "tutor"}, repo.facts_for(conn, user_id, stored[1]["id"]), replayed=True)
        if conv["status"] != "active" or conv["message_count"] + 2 > settings.AI_MAX_MESSAGES_PER_CONVERSATION:
            raise Conflict("This conversation is full. Please start a new one.")
        language, cefr = _language(conn, ctx, user_id)
        history = tuple((m["role"], m["content"][:settings.AI_MAX_MESSAGE_CHARS]) for m in repo.last_messages(conn, user_id, conversation_id, settings.AI_HISTORY_WINDOW))
        turn_index = repo.count_learner_messages(conn, user_id, conversation_id)
        phrases = tuple(_phrases(conn, ctx)[:MAX_PHRASES])
        title = conv["title"]
    facts = [] if mode == "child" else _facts(db_path, user_id, ctx, title)          # children get no learner-specific facts at all
    request = _bounded(TutorRequest(mode=mode, language=language, cefr=cefr, message=text, facts=tuple(t for _, t in facts), history=history,
                                    context_title=title if title != "Chat with your tutor" else None, phrases=phrases,
                                    turn_index=turn_index, quick_prompt=quick))
    # --- step 2: the provider (outside any transaction; children only ever get the built-in one) ---
    provider = registry.offline() if mode == "child" else registry.FACTORY()
    try:
        reply = clean(runner.run(provider.tutor_reply, request))
    except AiError:
        raise AiUnavailable()
    # --- step 3 (write): the learner message, the reply and the facts, together or not at all ---
    now = clock.now()
    try:
        with connect(db_path) as conn:
            conv = repo.get_conversation(conn, user_id, conversation_id)
            if conv is None:
                raise NotFound()
            if not repo.bump(conn, user_id, conversation_id, 2, settings.AI_MAX_MESSAGES_PER_CONVERSATION, now):
                raise Conflict("This conversation is full. Please start a new one.")
            seq = conv["message_count"] + 1
            lid = repo.insert_message(conn, conversation_id, user_id, seq, "learner", text, quick, client_id, None, now)
            tid = repo.insert_message(conn, conversation_id, user_id, seq + 1, "tutor", reply, None, None, provider.name, now)
            repo.insert_facts(conn, tid, facts)
            return _reply_view({"seq": seq, "content": text, "quick_prompt": quick, "created_at": now, "role": "learner"},
                               {"seq": seq + 1, "content": reply, "provider": provider.name, "created_at": now, "role": "tutor"}, repo.facts_for(conn, user_id, tid))
    except sqlite3.IntegrityError:                  # two sends raced for the same place, or the same client id arrived twice
        with connect(db_path) as conn:
            stored = repo.find_by_client_id(conn, user_id, conversation_id, client_id) if client_id else None
            if stored and stored[1]:
                return _reply_view({**stored[0], "role": "learner"}, {**stored[1], "role": "tutor"}, repo.facts_for(conn, user_id, stored[1]["id"]), replayed=True)
        raise Conflict("Another message was sent at the same time. Please try again.")

