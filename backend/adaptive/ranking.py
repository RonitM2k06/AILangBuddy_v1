"""The deterministic ranking used by the built-in provider (and as the fallback when any other provider's ranking is unusable).

Each candidate already passed the eligibility rules (it is available to this learner, at their level and age, and backed by stored
evidence). Ranking only ORDERS them: a base score per kind (what is usually most useful first) plus a small boost the engine computed from
the evidence (severity, how recent). Ties keep the engine's order. The note says why, using only the candidate's own evidence texts."""

KIND_SCORE = {"review_topic": 90, "remediation": 88, "review_item": 85, "targeted_vocabulary": 84, "practice_easier": 80, "low_confidence": 70,
              "listening_practice": 66, "continue_lesson": 64, "continue_situation": 62, "roleplay_practice": 60, "speaking_practice": 55,
              "practice_harder": 50, "confidence_checkin": 45, "next_lesson": 40, "next_situation": 38}


def score(candidate):
    return KIND_SCORE.get(candidate["kind"], 30) + int(candidate.get("boost", 0))


def order(candidates):
    """[(id, note)] best first; stable for equal scores."""
    indexed = sorted(enumerate(candidates), key=lambda p: (-score(p[1]), p[0]))
    out = []
    for place, (_, c) in enumerate(indexed, start=1):
        evidence = list(c.get("evidence") or ())
        note = ("Because: " + "; ".join(e.rstrip(".") for e in evidence[:2]) + ".") if evidence else "Suggested by your learning plan."
        out.append((c["id"], note[:300]))
    return out
