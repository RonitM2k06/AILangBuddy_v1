"""Helpers for Phase 12 API tests."""
from .aih import db  # noqa: F401
from .gam import uid  # noqa: F401
from .lis import activities, answer, correct_option, wrong_options


def weak(c, rounds=4, topic="greetings"):
    """Wrong listening answers, repeated, so the existing Phase 6 engine finds a topic weakness and item weaknesses."""
    for _ in range(rounds):
        for a in [x for x in activities(c) if x["topic"]["slug"] == topic]:
            answer(c, a["id"], wrong_options(a["id"])[0])


def listen(c, results, tick=None, step=60):
    """One listening answer per entry (True = correct), cycling through the activities, in order. tick(seconds) moves a frozen clock between answers."""
    acts = activities(c)
    for i, ok in enumerate(results):
        a = acts[i % len(acts)]
        answer(c, a["id"], correct_option(a["id"]) if ok else wrong_options(a["id"])[0])
        if tick:
            tick(step)


def recs(c):
    r = c.get("/api/ai/recommendations")
    assert r.status_code == 200, r.text
    return r.json()


def sig(body):
    return [(x["kind"], x["title"], x["reason"], x["ai_note"]) for x in body["recommendations"]]


def kinds(body):
    return [x["kind"] for x in body["recommendations"]]


def total_xp(c):
    return c.get("/api/gamification").json()["xp"]["total"]


def drills(c):
    r = c.get("/api/ai/micro-lessons")
    assert r.status_code == 200, r.text
    return r.json()["micro_lessons"]
