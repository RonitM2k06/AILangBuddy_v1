"""Adaptive difficulty recommendation: explainable and deterministic.

Looks at the learner's most recent graded lesson exercises (difficulty scale 1 easy .. 3 hard):
  * fewer than DIFFICULTY_MIN_ATTEMPTS answers  -> start at the easiest level;
  * accuracy >= STEP_UP_ACCURACY                -> one level above the level they have been working at;
  * accuracy <  STEP_DOWN_BELOW                 -> one level below it;
  * otherwise                                   -> stay at that level.
"Level they have been working at" is the mean difficulty of those answers, rounded. The recommendation only
suggests a level; it never changes stored content."""
from ..db import connect
from ..repositories import personalization as repo
from . import rules
from .context import learner_context

_label = rules.DIFFICULTY_LABELS.get


def recommend(attempts):
    """attempts: newest-first [{is_correct, difficulty}]. Pure function, unit-tested directly."""
    window = attempts[: rules.DIFFICULTY_WINDOW]
    n = len(window)
    scale = {"min": rules.DIFFICULTY_MIN, "max": rules.DIFFICULTY_MAX}
    if n < rules.DIFFICULTY_MIN_ATTEMPTS:
        level = rules.DIFFICULTY_MIN
        return {"recommended": level, "label": _label(level), "reason_code": "not_enough_data",
                "reason": f"Only {n} recent answers so far (need {rules.DIFFICULTY_MIN_ATTEMPTS}); starting at {_label(level)}.",
                "evidence": {"attempts": n, "correct": sum(a["is_correct"] for a in window), "accuracy": None, "working_level": None, "scale": scale}}
    correct = sum(a["is_correct"] for a in window)
    accuracy = correct / n
    working = min(rules.DIFFICULTY_MAX, max(rules.DIFFICULTY_MIN, int(sum(a["difficulty"] for a in window) / n + 0.5)))
    if accuracy >= rules.STEP_UP_ACCURACY:
        level, code = min(rules.DIFFICULTY_MAX, working + 1), "step_up"
        said = f"You got {correct} of {n} right at about {_label(working)} difficulty"
        reason = f"{said}, so try {_label(level)}." if level > working else f"{said}, and {_label(working)} is the hardest level."
    elif accuracy < rules.STEP_DOWN_BELOW:
        level, code = max(rules.DIFFICULTY_MIN, working - 1), "step_down"
        said = f"You got {correct} of {n} right at about {_label(working)} difficulty"
        reason = f"{said}, so try {_label(level)}." if level < working else f"{said}; {_label(working)} is already the easiest level."
    else:
        level, code = working, "stay"
        reason = f"You got {correct} of {n} right at about {_label(working)} difficulty, so stay at {_label(working)}."
    return {"recommended": level, "label": _label(level), "reason_code": code, "reason": reason,
            "evidence": {"attempts": n, "correct": correct, "accuracy": round(accuracy, 2), "working_level": working, "scale": scale}}


def for_learner(conn, user_id, ctx):
    return recommend(repo.recent_lesson_attempts(conn, user_id, ctx["target_language_id"], rules.DIFFICULTY_WINDOW))


def get_recommendation(db_path, user_id):
    with connect(db_path) as conn:
        return for_learner(conn, user_id, learner_context(conn, user_id))
