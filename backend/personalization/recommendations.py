"""Personalised recommendations, derived on demand from data the learner actually has: weaknesses, confidence ratings,
lessons/situations in progress, and (only as a starting point) the next unstarted content. Nothing is invented for a
learner who has no data, and nothing is stored: the persisted artifact is the daily plan built from these.

Order (each band only appears when its data exists), then the first MAX_RECOMMENDATIONS distinct targets are kept:
  1 review_topic          a topic with low recent accuracy (most severe first)
  2 review_item           a vocabulary item that keeps going wrong
  3 continue_lesson       a lesson started but not finished (most recent first)
  4 continue_situation    a situation started but not finished
  5 low_confidence        a topic the learner rated at or below LOW_CONFIDENCE_AT_OR_BELOW (lowest first)
  6 confidence_checkin    a topic practised several times but never rated
  7 next_lesson           the first lesson not started yet
  8 next_situation        the first situation not started yet"""
from ..db import connect
from ..repositories import curriculum, personalization as repo, progress, situations
from . import difficulty, rules, weaknesses
from .context import learner_context


def _topic(t):
    return {"slug": t["slug"], "name": t["name"], "icon": t["icon"]}


def build(conn, user_id, ctx):
    lang, rank, age = ctx["target_language_id"], ctx["max_rank"], ctx["age_group_id"]
    weaknesses.refresh(conn, user_id, lang)
    weak = weaknesses.current(conn, user_id, ctx)
    lessons = curriculum.list_available_lessons(conn, lang, rank, age)
    sits = situations.list_available(conn, lang, rank, age)
    lesson_topics = curriculum.topics_for_lessons(conn, [l["id"] for l in lessons])
    lprog = progress.summaries(conn, user_id, [l["id"] for l in lessons])
    sprog = situations.summaries(conn, user_id, [s["id"] for s in sits])
    topics = {t["slug"]: t for t in repo.topics_with_content(conn, lang, rank, age)}
    conf = repo.latest_confidence(conn, user_id, lang, "topic_id")
    windows = repo.recent_topic_window(conn, user_id, lang, rules.TOPIC_WINDOW)
    diff = difficulty.for_learner(conn, user_id, ctx)

    lessons_in = {}
    for l in lessons:
        for t in lesson_topics.get(l["id"], []):
            lessons_in.setdefault(t["slug"], []).append(l)
    sits_in = {}
    for s in sits:
        sits_in.setdefault(s["topic_slug"], []).append(s)

    def lesson_target(l):
        return {"type": "lesson", "id": l["id"], "title": l["title"]}

    def situation_target(s):
        return {"type": "situation", "id": s["id"], "title": s["title"]}

    def first_lesson_for(slug):
        return next(iter(lessons_in.get(slug, [])), None)

    bands = []  # (kind, reason, target, topic, evidence)
    # 1-2: weaknesses
    for w in (w for w in weak if w["rule"] == "low_topic_accuracy"):
        slug = w["topic"]["slug"]
        l, s = first_lesson_for(slug), next(iter(sits_in.get(slug, [])), None)
        target = lesson_target(l) if l else situation_target(s) if s else None
        if target:
            bands.append(("review_topic", f"{w['explanation']} Review {w['topic']['name']}.", target, w["topic"],
                          {"severity": w["severity"], "attempts": w["attempts"], "incorrect": w["incorrect"], "accuracy": w["accuracy"]}))
    for w in (w for w in weak if w["rule"] == "repeated_item_errors"):
        ids = repo.lessons_containing_item(conn, w["item"]["id"], lang, rank, age)
        l = next((x for x in lessons if x["id"] in ids), None)
        if l:
            bands.append(("review_item", f"{w['explanation']} It is in “{l['title']}”.", lesson_target(l),
                          next(iter(lesson_topics.get(l["id"], [])), None),
                          {"severity": w["severity"], "attempts": w["attempts"], "incorrect": w["incorrect"], "accuracy": w["accuracy"]}))
    # 3-4: unfinished work
    started = sorted((l for l in lessons if lprog[l["id"]]["started_at"] and not lprog[l["id"]]["completed_at"]),
                     key=lambda l: lprog[l["id"]]["started_at"], reverse=True)
    for l in started:
        p = lprog[l["id"]]
        bands.append(("continue_lesson", f"You have {p['exercises_correct']} of {p['exercises_total']} exercises right in “{l['title']}”. Finish it.",
                      lesson_target(l), next(iter(lesson_topics.get(l["id"], [])), None),
                      {"exercises_correct": p["exercises_correct"], "exercises_total": p["exercises_total"]}))
    started_s = sorted((s for s in sits if sprog[s["id"]]["started_at"] and not sprog[s["id"]]["completed_at"]),
                       key=lambda s: sprog[s["id"]]["started_at"], reverse=True)
    for s in started_s:
        p = sprog[s["id"]]
        bands.append(("continue_situation", f"You are on step {p['current_step_order']} of {p['steps_total']} in “{s['title']}”.",
                      situation_target(s), topics.get(s["topic_slug"]),
                      {"steps_completed": p["steps_completed"], "steps_total": p["steps_total"]}))
    # 5: low self-reported confidence
    low = sorted(((conf[t["id"]]["score"], t) for t in topics.values() if t["id"] in conf and conf[t["id"]]["score"] <= rules.LOW_CONFIDENCE_AT_OR_BELOW),
                 key=lambda p: (p[0], p[1]["id"]))
    for score, t in low:
        s, l = next(iter(sits_in.get(t["slug"], [])), None), first_lesson_for(t["slug"])
        target = situation_target(s) if s else lesson_target(l) if l else None
        if target:
            bands.append(("low_confidence", f"You rated your confidence in {t['name']} at {score}%. Practise it.", target, t, {"confidence": score}))
    # 6: ask for a rating where the learner has practised but never rated
    for t in topics.values():
        w = windows.get(t["id"])
        if w and w["attempts"] >= rules.CHECKIN_MIN_ATTEMPTS and t["id"] not in conf:
            bands.append(("confidence_checkin", f"You have practised {t['name']} {w['attempts']} times. How confident do you feel about it?",
                          {"type": "topic", "id": t["id"], "slug": t["slug"], "title": t["name"]}, t, {"attempts": w["attempts"]}))
    # 7-8: where to start next (curriculum order, only what is not started)
    nxt = next((l for l in lessons if not lprog[l["id"]]["started_at"]), None)
    if nxt:
        bands.append(("next_lesson", f"Next lesson: “{nxt['title']}”.", lesson_target(nxt), next(iter(lesson_topics.get(nxt["id"], [])), None), {}))
    nxt_s = next((s for s in sits if not sprog[s["id"]]["started_at"]), None)
    if nxt_s:
        bands.append(("next_situation", f"Next situation: “{nxt_s['title']}”.", situation_target(nxt_s), topics.get(nxt_s["topic_slug"]), {}))

    recs, seen = [], set()
    for kind, reason, target, topic, evidence in bands:
        key = (target["type"], target["id"])
        if key in seen:
            continue
        seen.add(key)
        rec = {"kind": kind, "priority": len(recs) + 1, "reason": reason, "target": target,
               "topic": _topic(topic) if topic else None, "evidence": evidence}
        if target["type"] == "lesson":
            rec["suggested_difficulty"] = diff["recommended"]  # see GET /api/difficulty for the reasoning
        recs.append(rec)
        if len(recs) == rules.MAX_RECOMMENDATIONS:
            break
    return {"recommendations": recs, "next_activity": recs[0] if recs else None, "difficulty": diff}


def get_recommendations(db_path, user_id):
    with connect(db_path) as conn:  # one transaction (building refreshes the derived weakness rows)
        return build(conn, user_id, learner_context(conn, user_id))
