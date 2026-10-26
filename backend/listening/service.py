"""Listening activities for the authenticated learner: browsing, playback metadata, server-side grading, attempts, progress.
No HTTP and no SQL in here."""
from datetime import datetime, timedelta

from ..audio.service import default_service
from ..db import connect
from ..personalization import clock
from ..personalization.context import InvalidInput, NeedsProfile, NotFound, learner_context  # noqa: F401  (re-exported)
from ..repositories import listening as repo, situations

AUDIO = default_service          # the audio service in use; tests (and a future TTS setup) can replace it
MAX_PLAYS = 99
MAX_RESPONSE_MS = 3_600_000
_TIME = "%Y-%m-%d %H:%M:%S"


def _status(stats):
    if not stats:
        return "not_started"
    return "completed" if stats["correct"] else "attempted"


def _progress(stats):
    s = stats or {"attempts": 0, "correct": 0, "last_attempt_at": None}
    return {"status": _status(stats), "attempts": s["attempts"], "correct": s["correct"], "last_attempt_at": s["last_attempt_at"]}


def _summary(row):
    return {"id": row["id"], "slug": row["slug"], "title": row["title"], "mode": row["mode"], "prompt": row["prompt"],
            "difficulty": row["difficulty"], "cefr_level": row["cefr_code"],
            "topic": {"slug": row["topic_slug"], "name": row["topic_name"], "icon": row["topic_icon"]}}


def list_activities(db_path, user_id):
    with connect(db_path) as conn:
        ctx = learner_context(conn, user_id)
        rows = repo.list_available(conn, ctx["target_language_id"], ctx["max_rank"], ctx["age_group_id"])
        stats = repo.activity_stats(conn, user_id, [r["id"] for r in rows])
    return [{**_summary(r), "progress": _progress(stats.get(r["id"]))} for r in rows]


def _option_views(mode, item_ids_by_option, items):
    """What the learner reads for each option. Never says which one is right."""
    out = []
    for option_id, item_id in item_ids_by_option:
        it = items[item_id]
        if mode == "choose_meaning":
            out.append({"id": option_id, "text": it["natural"] or it["meaning"]})
        else:
            out.append({"id": option_id, "text": it["text"], "pronunciation": it["pronunciation"]})
    return out


def get_activity(db_path, user_id, activity_id):
    with connect(db_path) as conn:
        ctx = learner_context(conn, user_id)
        a = repo.get_available(conn, activity_id, ctx["target_language_id"], ctx["max_rank"], ctx["age_group_id"])
        if a is None:
            raise NotFound()
        options = repo.options_for(conn, activity_id)
        items = situations.items_by_ids(conn, [o["item_id"] for o in options], ctx["native_language_id"], ctx["fallback_id"])
        source = AUDIO.resolve(conn, a["item_id"])
        stats = repo.activity_stats(conn, user_id, [activity_id]).get(activity_id)
    # The audio source is how the client plays the item. With browser TTS it necessarily carries the text to speak
    # (the UI does not display it); a stored audio file carries only its URL.
    return {**_summary(a), "audio": source.as_dict() if source else None,
            "options": _option_views(a["mode"], [(o["id"], o["item_id"]) for o in options], items), "progress": _progress(stats)}


def submit_answer(db_path, user_id, activity_id, *, option_id, plays=0, response_ms=None):
    if not 0 <= plays <= MAX_PLAYS:
        raise InvalidInput("plays", f"plays must be between 0 and {MAX_PLAYS}")
    if response_ms is not None and not 0 <= response_ms <= MAX_RESPONSE_MS:
        raise InvalidInput("response_ms", f"response_ms must be between 0 and {MAX_RESPONSE_MS}")
    with connect(db_path) as conn:  # one transaction: the session and its attempt are written together or not at all
        return submit_in(conn, learner_context(conn, user_id), user_id, activity_id, option_id, plays, response_ms)


def submit_in(conn, ctx, user_id, activity_id, option_id, plays, response_ms):
    """Grades and records one answer inside the caller's transaction (inputs already range-checked)."""
    a = repo.get_available(conn, activity_id, ctx["target_language_id"], ctx["max_rank"], ctx["age_group_id"])
    if a is None:
        raise NotFound()
    chosen = repo.option_item(conn, option_id, activity_id)
    if chosen is None:
        raise InvalidInput("option_id", "That option does not belong to this activity")
    correct = chosen == a["item_id"]                     # graded here, from the database, never from the client
    ended = clock.now()
    started = (datetime.strptime(ended, _TIME) - timedelta(milliseconds=response_ms or 0)).strftime(_TIME)
    session_id = repo.insert_session(conn, user_id, ctx["target_language_id"], started, ended, response_ms)
    attempt_id = repo.insert_attempt(conn, user_id, session_id, activity_id, option_id, correct, plays, ended)
    heard = situations.items_by_ids(conn, [a["item_id"]], ctx["native_language_id"], ctx["fallback_id"])[a["item_id"]]
    return {"correct": correct, "correct_option_id": repo.correct_option_id(conn, activity_id, a["item_id"]),
            "heard": {"text": heard["text"], "pronunciation": heard["pronunciation"], "meaning": heard["meaning"], "natural": heard["natural"]},
            "attempt": {"id": attempt_id, "plays": plays, "duration_ms": response_ms, "attempted_at": ended},
            "progress": _progress(repo.activity_stats(conn, user_id, [activity_id]).get(activity_id))}


def list_attempts(db_path, user_id, limit=50):
    with connect(db_path) as conn:
        ctx = learner_context(conn, user_id)
        rows = repo.list_attempts(conn, user_id, ctx["target_language_id"], limit)
    return [{"id": r["id"], "activity": {"id": r["activity_id"], "title": r["title"], "mode": r["mode"]}, "option_id": r["option_id"],
             "correct": bool(r["is_correct"]), "plays": r["plays"], "duration_ms": r["duration_ms"], "attempted_at": r["attempted_at"]} for r in rows]


def progress(db_path, user_id):
    with connect(db_path) as conn:
        ctx = learner_context(conn, user_id)
        ids = [r["id"] for r in repo.list_available(conn, ctx["target_language_id"], ctx["max_rank"], ctx["age_group_id"])]
        stats = repo.activity_stats(conn, user_id, ids)
    attempts = sum(s["attempts"] for s in stats.values())
    correct = sum(s["correct"] for s in stats.values())
    last = max((s["last_attempt_at"] for s in stats.values()), default=None)
    return {"activities_total": len(ids), "activities_attempted": len(stats),
            "activities_completed": sum(1 for s in stats.values() if s["correct"]),
            "attempts": attempts, "correct": correct, "accuracy": round(correct / attempts, 2) if attempts else None,
            "last_attempt_at": last}
