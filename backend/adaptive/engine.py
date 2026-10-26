"""The evidence bundle and the candidate generator.

EVIDENCE: a bundle of short, sourced statements about THIS learner, each built from stored rows by deterministic code (weaknesses,
confidence, recent accuracy by activity, roleplay results, progress, speaking counts, the Phase 6 difficulty reading). Every statement has
an id (e1, e2, ...). Anything the adaptive layer later says must point at these ids; a model is never asked for a statistic.

CANDIDATES: the things that may be recommended. They come from rules only: the Phase 6 recommendations (which already respect the
learner's level, age group and language) plus a few Phase 12 kinds, each of which checks eligibility itself. A model can only reorder and
explain candidates; it cannot add one, so it can never point a learner at something they are not allowed to see."""
from dataclasses import dataclass, field

from .. import settings
from ..parent import controls as parent_controls
from ..personalization import difficulty, recommendations, rules, weaknesses
from ..repositories import adaptive as repo, curriculum, listening as listening_repo, personalization as pers_repo, progress, situations, speaking as speaking_repo

SOURCE_LABELS = {"lesson": "lesson", "situation": "situation", "listening": "listening"}
TOPIC_ROLEPLAY_MAX = 1


@dataclass
class Evidence:
    id: str
    kind: str
    text: str
    data: dict = field(default_factory=dict)


class Bundle:
    def __init__(self):
        self.items = []

    def add(self, kind, text, **data):
        e = Evidence(f"e{len(self.items) + 1}", kind, text[:300], data)
        self.items.append(e)
        return e.id

    def get(self, eid):
        return next(e for e in self.items if e.id == eid)

    def texts(self, ids):
        return [self.get(i).text for i in ids]

    def where(self, kind, **match):
        return [e for e in self.items if e.kind == kind and all(e.data.get(k) == v for k, v in match.items())]


def _pct_windows(results):
    """results newest-first. -> (recent (correct, n), previous (correct, n))."""
    w = settings.AI_TREND_WINDOW
    recent, prev = results[:w], results[w:2 * w]
    return (sum(recent), len(recent)), (sum(prev), len(prev))


def build_bundle(conn, user_id, ctx, today, diff, weak, lessons, sits):
    """Everything below is read from stored rows. Nothing here is estimated by a model."""
    b = Bundle()
    lang, rank, age = ctx["target_language_id"], ctx["max_rank"], ctx["age_group_id"]
    ev = diff["evidence"]
    if diff["reason_code"] != "not_enough_data":
        b.add("difficulty", f"Recent lesson answers: {ev['correct']} of {ev['attempts']} right at about {diff['label']} difficulty.", code=diff["reason_code"], level=diff["recommended"],
              working=ev["working_level"], accuracy=ev["accuracy"])
    for w in weak[:4]:
        if w["rule"] == "low_topic_accuracy":
            b.add("weakness", f"{w['topic']['name']}: {w['attempts'] - w['incorrect']} of the last {w['attempts']} answers were correct.", rule=w["rule"], topic=w["topic"]["slug"],
                  topic_name=w["topic"]["name"], severity=w["severity"], attempts=w["attempts"], incorrect=w["incorrect"])
        else:
            it = w["item"]
            phrase = it["pronunciation"] or it["text"]
            b.add("weakness", f"“{phrase}” was answered wrongly {w['incorrect']} of {w['attempts']} times.", rule=w["rule"], item_id=it["id"], item_text=phrase,
                  severity=w["severity"], attempts=w["attempts"], incorrect=w["incorrect"])
    conf = pers_repo.latest_confidence(conn, user_id, lang, "topic_id")
    topics = {t["id"]: t for t in pers_repo.topics_with_content(conn, lang, rank, age)}
    for tid, c in sorted(conf.items(), key=lambda p: (p[1]["score"], p[0])):
        if tid in topics and c["score"] <= rules.LOW_CONFIDENCE_AT_OR_BELOW:
            b.add("confidence", f"Self-rated confidence in {topics[tid]['name']}: {c['score']}%.", topic=topics[tid]["slug"], topic_name=topics[tid]["name"], score=c["score"])
    windows = pers_repo.recent_topic_window(conn, user_id, lang, rules.TOPIC_WINDOW)
    for tid, c in sorted(conf.items(), key=lambda p: (p[1]["score"], p[0])):
        w = windows.get(tid)
        if tid in topics and c["score"] <= rules.LOW_CONFIDENCE_AT_OR_BELOW and w and w["attempts"] >= settings.AI_TREND_MIN_ATTEMPTS:
            right = w["attempts"] - w["incorrect"]
            b.add("accuracy", f"Last {w['attempts']} {topics[tid]['name']} answers: {right} correct.", source="topic", topic=topics[tid]["slug"], topic_name=topics[tid]["name"],
                  correct=right, attempts=w["attempts"], accuracy=right / w["attempts"], prev_accuracy=None)
    for source in ("listening", "lesson", "situation"):
        results = repo.recent_results(conn, user_id, lang, source, 2 * settings.AI_TREND_WINDOW)
        (c1, n1), (c0, n0) = _pct_windows(results)
        if n1 >= settings.AI_TREND_MIN_ATTEMPTS:
            b.add("accuracy", f"Last {n1} {SOURCE_LABELS[source]} answers: {c1} correct.", source=source, correct=c1, attempts=n1, accuracy=c1 / n1,
                  prev_correct=c0, prev_attempts=n0, prev_accuracy=(c0 / n0) if n0 >= settings.AI_TREND_MIN_ATTEMPTS else None)
    for rp in repo.recent_roleplays(conn, user_id, lang, 3):
        b.add("roleplay", f"Roleplay “{rp['title']}”: {rp['steps_correct']} of {rp['steps_total']} steps correct.", situation_id=rp["situation_id"], title=rp["title"],
              correct=rp["steps_correct"], total=rp["steps_total"])
    counts, _ = speaking_repo.progress_counts(conn, user_id, lang)
    if counts.get("completed", 0):
        b.add("speaking", f"{counts['completed']} speaking practice{'s' if counts['completed'] != 1 else ''} completed.", completed=counts["completed"])
    lprog = progress.summaries(conn, user_id, [l["id"] for l in lessons])
    done = sum(1 for p in lprog.values() if p["completed_at"])
    if lessons:
        b.add("progress", f"{done} of {len(lessons)} lessons completed.", scope="lessons", done=done, total=len(lessons))
    sprog = situations.summaries(conn, user_id, [s["id"] for s in sits])
    sdone = sum(1 for p in sprog.values() if p["completed_at"])
    if sits:
        b.add("progress", f"{sdone} of {len(sits)} situations completed.", scope="situations", done=sdone, total=len(sits))
    last = repo.last_attempt_day(conn, user_id)
    if last:
        from datetime import date
        gap = (date.fromisoformat(today) - date.fromisoformat(last)).days
        if gap >= 3:
            b.add("activity", f"The last answer was {gap} days ago.", days=gap)
    return b


def _cid(kind, ttype, tid):
    return f"{kind}:{ttype}:{tid}"


def _boost(severity):
    return {"high": 8, "medium": 4}.get(severity, 0)


def candidates(conn, user_id, ctx, bundle, phase6, today, mode, lessons, sits):
    """-> (candidates in rule order, micro_specs). A micro spec asks for a drill on one canonical item; the caller generates, validates and stores it."""
    lang, rank, age = ctx["target_language_id"], ctx["max_rank"], ctx["age_group_id"]
    out, seen = [], set()

    def add(kind, ttype, tid, title, reason, evidence, boost=0):
        cid = _cid(kind, ttype, tid)
        if cid in seen or not evidence:
            return
        seen.add(cid)
        out.append({"id": cid, "kind": kind, "target_type": ttype, "target_id": tid, "title": title, "reason": reason, "evidence_ids": list(evidence), "boost": boost})

    weak_topic = {e.data["topic"]: e for e in bundle.where("weakness", rule="low_topic_accuracy")}
    weak_items = bundle.where("weakness", rule="repeated_item_errors")
    conf = {e.data["topic"]: e for e in bundle.items if e.kind == "confidence"}
    prog = {e.data["scope"]: e for e in bundle.items if e.kind == "progress" and "scope" in e.data}
    lesson_ids = {l["id"] for l in lessons}

    # --- the Phase 6 recommendations, kept in their order, each tied to stored evidence ---
    for rec in phase6["recommendations"]:
        t, topic, kind = rec["target"], rec["topic"], rec["kind"]
        ids, boost = [], 0
        if kind == "review_topic" and topic and topic["slug"] in weak_topic:
            ids, boost = [weak_topic[topic["slug"]].id], _boost(weak_topic[topic["slug"]].data["severity"])
        elif kind == "review_item":
            for e in weak_items:
                if t["type"] == "lesson" and t["id"] in repo_lessons(conn, e.data["item_id"], lang, rank, age):
                    ids, boost = [e.id], _boost(e.data["severity"])
                    break
        elif kind == "low_confidence" and topic and topic["slug"] in conf:
            ids, boost = [conf[topic["slug"]].id], max(0, (rules.LOW_CONFIDENCE_AT_OR_BELOW - conf[topic["slug"]].data["score"]) // 5)
        elif kind in ("continue_lesson", "next_lesson") and "lessons" in prog:
            ids = [prog["lessons"].id]
        elif kind in ("continue_situation", "next_situation") and "situations" in prog:
            ids = [prog["situations"].id]
        elif kind == "confidence_checkin":
            ids = [bundle.add("activity", rec["reason"])]
        if not ids:
            ids = [bundle.add("progress", rec["reason"])]
        add(kind, t["type"], t["id"], t["title"], rec["reason"], ids, boost)

    first_lesson = next((c for c in out if c["target_type"] == "lesson"), None)
    # --- easier / harder practice, from the Phase 6 difficulty reading ---
    d = bundle.where("difficulty")
    if d and first_lesson:
        e = d[0]
        if e.data["code"] == "step_down":
            add("practice_easier", "lesson", first_lesson["target_id"], first_lesson["title"],
                f"{e.text} A set of easier questions may help you build up.", [e.id], 6)
        elif e.data["code"] == "step_up" and e.data["level"] > e.data["working"]:
            add("practice_harder", "lesson", first_lesson["target_id"], first_lesson["title"],
                f"{e.text} You may be ready for something harder.", [e.id], 0)
    # --- listening practice when recent listening accuracy is low ---
    for e in bundle.where("accuracy", source="listening"):
        if e.data["accuracy"] < rules.TOPIC_WEAK_BELOW:
            stats = listening_repo.activity_stats(conn, user_id, [a["id"] for a in listening_repo.list_available(conn, lang, rank, age)])
            nxt = next((a for a in listening_repo.list_available(conn, lang, rank, age) if not (stats.get(a["id"]) or {}).get("correct")), None)
            if nxt:
                add("listening_practice", "listening_activity", nxt["id"], f"Listening: {nxt['title']}",
                    f"{e.text} More listening practice can help.", [e.id], 0)
    # --- speaking practice (never when voice is switched off for this learner, whatever the reason) ---
    total_attempts = sum(x.data["attempts"] for x in bundle.items if x.kind == "accuracy" and x.data["source"] != "topic")
    done = bundle.where("speaking")
    if parent_controls.voice_block_reason(conn, ctx, user_id) is None and total_attempts >= 10 and (not done or done[0].data["completed"] < 3):
        sid = bundle.add("speaking", "No speaking practice completed yet." if not done else done[0].text, completed=0 if not done else done[0].data["completed"])
        add("speaking_practice", "speaking", 0, "Voice Practice", "Speaking out loud builds fluency. You have been answering questions; try saying some phrases too.", [sid], 0)
    # --- roleplay: only where it follows evidence, and only after practice of the topic when the topic is weak ---
    completed_roleplays = {e.data["situation_id"] for e in bundle.where("roleplay")}
    n_role = 0
    for s in sits:
        slug = s["topic_slug"]
        if s["id"] in completed_roleplays or slug in weak_topic or n_role >= TOPIC_ROLEPLAY_MAX:
            continue
        lprog_topic = [l for l in lessons if slug in {t["slug"] for t in curriculum.topics_for_lessons(conn, [l["id"]]).get(l["id"], [])}]
        if lprog_topic and "lessons" in prog and prog["lessons"].data["done"] > 0 and any(p["completed_at"] for p in progress.summaries(conn, user_id, [l["id"] for l in lprog_topic]).values()):
            add("roleplay_practice", "roleplay", s["id"], f"Roleplay: {s['title']}",
                f"You have completed a {s['topic_name']} lesson. Try it in a roleplay.", [prog["lessons"].id], 0)
            n_role += 1
    # --- targeted vocabulary micro-lessons: item weaknesses, and recent mistakes inside a weak topic ---
    specs, spec_items = [], set()

    def spec(item_id, evidence, boost, topic_slug=None):
        if item_id in spec_items or len(specs) >= settings.AI_MAX_NEW_MICRO_LESSONS_PER_DAY:
            return
        spec_items.add(item_id)
        specs.append({"item_id": item_id, "evidence_ids": evidence, "boost": boost, "topic_slug": topic_slug})

    for e in weak_items:
        spec(e.data["item_id"], [e.id], _boost(e.data["severity"]))
    for item_id in repo_recent_mistakes(conn, user_id, lang):
        t = repo.item_topic(conn, item_id, lang, rank, age)
        if t and t["slug"] in weak_topic:
            spec(item_id, [weak_topic[t["slug"]].id], _boost(weak_topic[t["slug"]].data["severity"]), t["slug"])
    return out, specs


def repo_lessons(conn, item_id, lang, rank, age):
    return set(pers_repo.lessons_containing_item(conn, item_id, lang, rank, age))


def repo_recent_mistakes(conn, user_id, lang, limit=4):
    from ..repositories import tutor as tutor_repo
    return tutor_repo.recent_mistake_items(conn, user_id, lang, limit)


def prepare(conn, user_id, ctx, today, mode):
    """Everything the adaptive layer needs, from one consistent read. Returns a dict (no provider has been called yet)."""
    phase6 = recommendations.build(conn, user_id, ctx)                      # also refreshes the derived weaknesses, exactly as Phase 6 does
    lang, rank, age = ctx["target_language_id"], ctx["max_rank"], ctx["age_group_id"]
    lessons = curriculum.list_available_lessons(conn, lang, rank, age)
    sits = situations.list_available(conn, lang, rank, age)
    weak = weaknesses.current(conn, user_id, ctx)
    diff = difficulty.for_learner(conn, user_id, ctx)
    bundle = build_bundle(conn, user_id, ctx, today, diff, weak, lessons, sits)
    cands, specs = candidates(conn, user_id, ctx, bundle, phase6, today, mode, lessons, sits)
    return {"phase6": phase6, "bundle": bundle, "candidates": cands, "micro_specs": specs, "difficulty": diff, "lessons": lessons, "situations": sits}
