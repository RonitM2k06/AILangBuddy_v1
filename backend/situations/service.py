"""Situational learning for the authenticated learner: browsing, ordered step progression, grading, progress.
No HTTP and no SQL in here."""
from datetime import datetime, timezone

from .. import settings
from ..curriculum.service import AttemptError, NeedsProfile, NotFound  # same meaning as in lessons
from ..db import connect
from ..learner import service as learner_service
from ..repositories import catalog, curriculum, learner, situations
from ..textnorm import answer_key

MAX_TEXT_ANSWER = 500
TYPED_KINDS = ("translate", "fill_blank", "conversation")


class OutOfOrder(Exception):
    """A later step was submitted before the current one was passed."""


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _context(conn, user_id):
    ctx = curriculum.get_learner_context(conn, user_id)
    if ctx is None:
        raise NeedsProfile()
    ctx["fallback_id"] = learner.get_language_id(conn, settings.FALLBACK_CONTENT_LANGUAGE)
    return learner_service.with_age_group(conn, ctx)


def _progress_view(s):
    status = "completed" if s["completed_at"] else ("in_progress" if s["started_at"] else "not_started")
    return {"status": status, "steps_total": s["steps_total"], "steps_completed": s["steps_completed"], "attempts": s["attempts"],
            "current_step_id": None if s["completed_at"] else s["current_step_id"],
            "current_step_order": None if s["completed_at"] else s["current_step_order"],
            "started_at": s["started_at"], "completed_at": s["completed_at"]}


def _summary_view(row):
    return {"id": row["id"], "slug": row["slug"], "title": row["title"], "description": row["description"], "goal": row["goal"],
            "setting": row["setting"], "partner_name": row["partner_name"], "partner_role": row["partner_role"],
            "difficulty": row["difficulty"], "cefr_level": row["cefr_code"],
            "topic": {"slug": row["topic_slug"], "name": row["topic_name"], "icon": row["topic_icon"]}}


def list_situations(db_path, user_id):
    with connect(db_path) as conn:
        ctx = _context(conn, user_id)
        rows = situations.list_available(conn, ctx["target_language_id"], ctx["max_rank"], ctx["age_group_id"])
        summaries = situations.summaries(conn, user_id, [r["id"] for r in rows])
    return [{**_summary_view(r), "progress": _progress_view(summaries[r["id"]])} for r in rows]


def get_situation(db_path, user_id, situation_id):
    with connect(db_path) as conn:
        ctx = _context(conn, user_id)
        row = situations.get_available(conn, situation_id, ctx["target_language_id"], ctx["max_rank"], ctx["age_group_id"])
        if row is None:
            raise NotFound()
        steps = situations.steps_for_situation(conn, situation_id)
        shown = situations.step_answers_for_display(conn, [s["id"] for s in steps])
        # Only learn_phrase steps show their vocabulary item. On other kinds item_id is just a content link, and showing it
        # (e.g. on a translate step) would give the answer away.
        items = situations.items_by_ids(conn, [s["item_id"] for s in steps if s["item_id"] and s["kind"] == "learn_phrase"],
                                        ctx["native_language_id"], ctx["fallback_id"])
        view = []
        for s in steps:
            step = {"id": s["id"], "order": s["sort_order"], "kind": s["kind"], "prompt": s["prompt"], "prompt_meaning": s["prompt_meaning"]}
            if s["kind"] == "learn_phrase":
                step["item"] = items[s["item_id"]]
            if s["kind"] == "choose_response":
                step["options"] = [{"id": i, "text": t} for i, t in shown.get(s["id"], [])]
            elif s["kind"] == "conversation":
                step["suggestions"] = [t for _, t in shown.get(s["id"], [])]  # offered to the learner by design
            view.append(step)
        progress = _progress_view(situations.summaries(conn, user_id, [situation_id])[situation_id])
    return {**_summary_view(row), "steps": view, "progress": progress}


def submit_response(db_path, user_id, situation_id, step_id, *, answer_id=None, text=None):
    with connect(db_path) as conn:
        ctx = _context(conn, user_id)
        if situations.get_available(conn, situation_id, ctx["target_language_id"], ctx["max_rank"], ctx["age_group_id"]) is None:
            raise NotFound()
        step = situations.get_step(conn, step_id, situation_id)
        if step is None:
            raise NotFound()
        before = situations.summaries(conn, user_id, [situation_id])[situation_id]
        # Steps are taken in order: you may redo a passed step, but not skip ahead of the current one.
        if not before["completed_at"] and before["current_step_order"] is not None and step["sort_order"] > before["current_step_order"]:
            raise OutOfOrder()
        answers = situations.answers_for_step(conn, step_id)
        kind, stored_text = step["kind"], None
        if kind == "learn_phrase":
            if answer_id is not None or text is not None:
                raise AttemptError("text", "Nothing to answer here; just continue")
            correct = True
        elif kind == "choose_response":
            if answer_id is None or text is not None:
                raise AttemptError("answer_id", "Choose one of the options")
            chosen = next((a for a in answers if a["id"] == answer_id), None)
            if chosen is None:
                raise AttemptError("answer_id", "That option does not belong to this step")
            correct = bool(chosen["is_correct"])
        else:  # typed kinds: compared after normalisation against the accepted answers
            if answer_id is not None or text is None:
                raise AttemptError("text", "Type your answer")
            text = text.strip()
            if not text or len(text) > MAX_TEXT_ANSWER:
                raise AttemptError("text", f"Answer must be 1-{MAX_TEXT_ANSWER} characters")
            code = catalog.language_code(conn, ctx["target_language_id"])        # Marathi folds its documented spelling variants; Hindi is exact
            correct = answer_key(text, code) in {answer_key(a["answer_text"], code) for a in answers if a["is_correct"]}
            stored_text = text
        stamp = now()
        situations.ensure_started(conn, user_id, situation_id, stamp)
        situations.record_attempt(conn, user_id, step_id, answer_id, stored_text, correct, stamp)
        if correct:
            situations.mark_completed_if_done(conn, user_id, situation_id, stamp)
        progress = _progress_view(situations.summaries(conn, user_id, [situation_id])[situation_id])
        return {"correct": correct, "explanation": step["explanation"],
                "correct_answers": [] if correct or kind == "learn_phrase" else [a["answer_text"] for a in answers if a["is_correct"]],
                "progress": {"situation_id": situation_id, **progress}}


def situation_progress(db_path, user_id):
    """Situations this learner has started, most recently started first."""
    with connect(db_path) as conn:
        ctx = _context(conn, user_id)
        rows = {r["id"]: r for r in situations.list_available(conn, ctx["target_language_id"], ctx["max_rank"], ctx["age_group_id"])}
        summaries = situations.summaries(conn, user_id, list(rows))
    started = sorted(((i, s) for i, s in summaries.items() if s["started_at"]), key=lambda p: (p[1]["started_at"], p[0]), reverse=True)
    return [{"situation_id": i, "title": rows[i]["title"], **_progress_view(s)} for i, s in started]
