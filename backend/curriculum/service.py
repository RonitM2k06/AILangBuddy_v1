"""Lessons, exercise grading and progress for the authenticated learner. No HTTP and no SQL in here."""
from datetime import datetime, timezone

from .. import settings
from ..db import connect
from ..learner import service as learner_service
from ..repositories import catalog, curriculum, learner, progress
from ..textnorm import answer_key, normalize  # normalize re-exported: tests and callers use service.normalize

MAX_TEXT_ANSWER = 500


class NeedsProfile(Exception):
    """The learner has not chosen a target language and level yet."""


class NotFound(Exception):
    """Unknown, unpublished, or outside the learner's language/level (deliberately indistinguishable)."""


class AttemptError(ValueError):
    def __init__(self, field, message):
        super().__init__(message)
        self.field = field
        self.message = message


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _status(summary):
    if summary["completed_at"]:
        return "completed"
    return "in_progress" if summary["started_at"] else "not_started"


def _context(conn, user_id):
    ctx = curriculum.get_learner_context(conn, user_id)
    if ctx is None:
        raise NeedsProfile()
    ctx["fallback_id"] = learner.get_language_id(conn, settings.FALLBACK_CONTENT_LANGUAGE)
    return learner_service.with_age_group(conn, ctx)


def _progress_view(summary):
    return {"status": _status(summary), "exercises_total": summary["exercises_total"],
            "exercises_correct": summary["exercises_correct"], "started_at": summary["started_at"], "completed_at": summary["completed_at"]}


def list_lessons(db_path, user_id):
    with connect(db_path) as conn:
        ctx = _context(conn, user_id)
        lessons = curriculum.list_available_lessons(conn, ctx["target_language_id"], ctx["max_rank"], ctx["age_group_id"])
        ids = [l["id"] for l in lessons]
        topics = curriculum.topics_for_lessons(conn, ids)
        summaries = progress.summaries(conn, user_id, ids)
    return [{"id": l["id"], "slug": l["slug"], "title": l["title"], "description": l["description"], "cefr_level": l["cefr_code"],
             "topics": topics.get(l["id"], []), "progress": _progress_view(summaries[l["id"]])} for l in lessons]


def get_lesson(db_path, user_id, lesson_id):
    with connect(db_path) as conn:
        ctx = _context(conn, user_id)
        lesson = curriculum.get_available_lesson(conn, lesson_id, ctx["target_language_id"], ctx["max_rank"], ctx["age_group_id"])
        if lesson is None:
            raise NotFound()
        native, fallback = ctx["native_language_id"], ctx["fallback_id"]
        vocab = curriculum.vocabulary_for_lesson(conn, lesson_id, native, fallback)
        examples = curriculum.examples_for_items(conn, [v["id"] for v in vocab], native, fallback)
        for v in vocab:
            v["examples"] = examples.get(v["id"], [])
        return {
            "id": lesson["id"], "slug": lesson["slug"], "title": lesson["title"], "description": lesson["description"],
            "situation": lesson["situation"], "tip": lesson["tip"], "cefr_level": lesson["cefr_code"],
            "topics": curriculum.topics_for_lessons(conn, [lesson_id]).get(lesson_id, []),
            "vocabulary": vocab,
            "grammar": curriculum.grammar_for_lesson(conn, lesson_id, native, fallback),
            "exercises": curriculum.exercises_for_lesson(conn, lesson_id),
            "progress": _progress_view(progress.summaries(conn, user_id, [lesson_id])[lesson_id]),
        }


def submit_attempt(db_path, user_id, exercise_id, *, answer_id=None, text=None):
    with connect(db_path) as conn:
        ctx = _context(conn, user_id)
        exercise = curriculum.get_exercise(conn, exercise_id)
        # The exercise must sit in a lesson this learner may see; otherwise it looks like it doesn't exist.
        if exercise is None or curriculum.get_available_lesson(conn, exercise["lesson_id"], ctx["target_language_id"], ctx["max_rank"], ctx["age_group_id"]) is None:
            raise NotFound()
        answers = curriculum.answers_for_exercise(conn, exercise_id)
        if exercise["kind"] == "multiple_choice":
            if answer_id is None or text is not None:
                raise AttemptError("answer_id", "Choose one of the options")
            chosen = next((a for a in answers if a["id"] == answer_id), None)
            if chosen is None:
                raise AttemptError("answer_id", "That option does not belong to this exercise")
            correct, stored_text = bool(chosen["is_correct"]), None
        else:
            if answer_id is not None or text is None:
                raise AttemptError("text", "Type your answer")
            text = text.strip()
            if not text or len(text) > MAX_TEXT_ANSWER:
                raise AttemptError("text", f"Answer must be 1-{MAX_TEXT_ANSWER} characters")
            code = catalog.language_code(conn, ctx["target_language_id"])        # Marathi folds its documented spelling variants; Hindi is exact
            accepted = {answer_key(a["answer_text"], code) for a in answers if a["is_correct"]}
            correct, stored_text = answer_key(text, code) in accepted, text
        stamp = now()
        progress.ensure_started(conn, user_id, exercise["lesson_id"], stamp)
        progress.record_attempt(conn, user_id, exercise_id, answer_id, stored_text, correct, stamp)
        if correct:
            progress.mark_completed_if_done(conn, user_id, exercise["lesson_id"], stamp)
        summary = progress.summaries(conn, user_id, [exercise["lesson_id"]])[exercise["lesson_id"]]
        return {"correct": correct, "explanation": exercise["explanation"],
                "correct_answers": [a["answer_text"] for a in answers if a["is_correct"]],
                "lesson_progress": {"lesson_id": exercise["lesson_id"], **_progress_view(summary)}}


def lesson_progress(db_path, user_id):
    """Progress for the lessons this learner has started, most recently started first."""
    with connect(db_path) as conn:
        ctx = _context(conn, user_id)
        lessons = {l["id"]: l for l in curriculum.list_available_lessons(conn, ctx["target_language_id"], ctx["max_rank"], ctx["age_group_id"])}
        summaries = progress.summaries(conn, user_id, list(lessons))
    started = [(i, s) for i, s in summaries.items() if s["started_at"]]
    started.sort(key=lambda p: (p[1]["started_at"], p[0]), reverse=True)
    return [{"lesson_id": i, "title": lessons[i]["title"], **_progress_view(s)} for i, s in started]
