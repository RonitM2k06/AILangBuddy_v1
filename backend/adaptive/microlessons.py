"""Generated micro-lessons: short supplemental drills, kept apart from the canonical curriculum.

A micro-lesson is ANCHORED to one canonical vocabulary item the learner is allowed to see (it must be in their available content). The
question is built from that item, the distractors are other canonical items from the learner's own content, and the correct answer is the
canonical one: a provider may word the question, but `validate_micro_lesson` rejects anything whose right answer is not the canonical
answer, whose wrong options are not canonical distractors, or that carries links or markup. Only validated drills are stored and shown
(never expired ones, never to another age group, never in another language). Children only ever get the deterministic template.
Answering a drill awards no XP and does not touch curriculum progress."""
from datetime import datetime, timedelta

from .. import settings
from ..ai import registry, runner
from ..ai.base import AiError, MicroLessonRequest
from ..personalization import clock
from ..repositories import adaptive as repo, personalization as pers_repo, situations, speaking as speaking_repo
from ..textnorm import normalize
from .validate import validate_micro_lesson

KINDS = ("vocab_choice", "phrase_choice", "translation")
_TIME = "%Y-%m-%d %H:%M:%S"
DISTRACTORS = 3


def _phrase(item):
    return item.get("pronunciation") or item["text"]


def eligible_items(conn, ctx):
    """The canonical phrases this learner may be drilled on: exactly the phrases reachable through their own available lessons and situations."""
    ids = sorted(speaking_repo.available_prompts(conn, ctx["target_language_id"], ctx["max_rank"], ctx["age_group_id"]))
    items = situations.items_by_ids(conn, ids, ctx["native_language_id"], ctx["fallback_id"])
    return {i: items[i] for i in ids if i in items and items[i]["meaning"]}


def plan(conn, user_id, ctx, spec, mode, day, difficulty):
    """-> a job (everything a provider needs, plus the canonical answer to validate against), or None if this item cannot be drilled."""
    pool = eligible_items(conn, ctx)
    item = pool.get(spec["item_id"])
    if item is None:
        return None                                                              # not in this learner's available content: never drilled
    used = conn.execute("SELECT COUNT(*) FROM ai_micro_lessons WHERE user_id = ? AND item_id = ?", (user_id, spec["item_id"])).fetchone()[0]
    kind = KINDS[used % len(KINDS)]
    existing = repo.find_micro(conn, user_id, day, spec["item_id"], kind)
    if existing is None and used:                                                # today's drill for this item may already exist under the previous kind
        for k in KINDS:
            existing = repo.find_micro(conn, user_id, day, spec["item_id"], k)
            if existing is not None:
                break
    if existing is not None:
        return {"reuse": True, "micro_id": existing, "item_id": spec["item_id"], "spec": spec, "phrase": _phrase(item)}
    others = [it for i, it in sorted(pool.items()) if i != spec["item_id"]]
    answer = item["meaning"] if kind == "vocab_choice" else _phrase(item)
    # a phrase's feminine form is its own item ("… (said by a woman)"): it never stands as a second, near-identical wrong option
    same = lambda t: normalize(t.removesuffix(" (said by a woman)"))
    wrong, seen = [], {same(answer)}
    for it in others:
        text = it["meaning"] if kind == "vocab_choice" else _phrase(it)
        if same(text) not in seen:
            seen.add(same(text))
            wrong.append(text)
        if len(wrong) == DISTRACTORS:
            break
    if kind != "translation" and len(wrong) < DISTRACTORS:
        return None
    language = conn.execute("SELECT name FROM languages WHERE id = ?", (ctx["target_language_id"],)).fetchone()["name"]
    cefr = conn.execute("SELECT cefr_level FROM learner_profiles WHERE user_id = ?", (user_id,)).fetchone()["cefr_level"]
    topic = repo.item_topic(conn, spec["item_id"], ctx["target_language_id"], ctx["max_rank"], ctx["age_group_id"])
    canonical = {"answer": answer, "accepted": tuple(a for a in (item.get("pronunciation"), item["text"]) if a)}
    request = MicroLessonRequest(mode=mode, language=language, cefr=cefr, kind=kind, difficulty=difficulty,
                                 item={"text": item["text"], "pronunciation": item["pronunciation"], "meaning": item["meaning"]}, distractors=tuple(wrong))
    return {"reuse": False, "request": request, "canonical": canonical, "wrong": tuple(wrong), "kind": kind, "item_id": spec["item_id"], "spec": spec, "topic": topic, "phrase": _phrase(item)}


def generate(job, mode):
    """Runs the provider (children: never, only the template) and validates. -> (validated, generator, rejected_reason or None). No database here."""
    template = registry.offline()
    rejected = None
    if mode != "child":
        provider = registry.FACTORY()
        try:
            data = runner.run(provider.generate_micro_lesson, job["request"])
            return validate_micro_lesson(data, job["kind"], job["canonical"], job["wrong"]), ("llm" if provider.name == "llm" else "mock"), None
        except AiError as exc:
            rejected = exc.code
    data = template.generate_micro_lesson(job["request"])
    return validate_micro_lesson(data, job["kind"], job["canonical"], job["wrong"]), "template", rejected


def store(conn, user_id, ctx, job, validated, generator, evidence, mode, day, now, difficulty):
    expires = (datetime.strptime(now, _TIME) + timedelta(days=settings.AI_MICRO_LESSON_TTL_DAYS)).strftime(_TIME)
    topic = job["topic"]
    mid = repo.insert_micro(conn, user_id, ctx["target_language_id"], job["item_id"], job["kind"], topic["id"] if topic else None, difficulty, mode, validated["question"], generator,
                            "Answer matches the canonical item; options come from the learner's own content.", day, now, expires)
    repo.insert_options(conn, user_id, mid, validated["options"])
    repo.insert_evidence(conn, user_id, "micro_lesson", mid, evidence)
    return mid


def presentable(conn, user_id, ctx, mode, now):
    repo.expire_micro(conn, user_id, now)
    return repo.list_presentable_micro(conn, user_id, ctx["target_language_id"], mode, now)


def view(conn, user_id, m, stats):
    options = repo.options_for(conn, user_id, m["id"])
    out = {"id": m["id"], "kind": m["kind"], "question": m["question"], "difficulty": m["difficulty"], "generated_by": m["generator"], "expires_at": m["expires_at"],
           "topic": {"slug": m["topic_slug"], "name": m["topic_name"]} if m["topic_slug"] else None,
           "answer_mode": "text" if m["kind"] == "translation" else "choice", "attempts": stats.get("attempts", 0), "correct_attempts": stats.get("correct", 0),
           "evidence": repo.evidence_for(conn, user_id, "micro_lesson", m["id"]), "label": "Practice made for you (not part of your lessons)"}
    if m["kind"] != "translation":
        out["options"] = [{"choice": o["ord"], "text": o["text"]} for o in options]                  # never is_correct
    return out
