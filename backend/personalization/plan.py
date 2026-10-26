"""The learner's daily plan: a few tasks per (day, language), taken from the top recommendations.

Generation is deterministic and idempotent: if the day already has a plan it is returned unchanged (the plan does not
reshuffle as the learner's data changes during the day), and unique indexes make a repeated or concurrent generation
unable to create duplicate tasks. Tasks the learner already completed (lesson/situation finished, topic rated) on or
after the plan date are marked done when the plan is read."""
from ..db import connect
from ..repositories import personalization as repo
from . import clock, recommendations, rules
from .context import InvalidInput, NotFound, learner_context

WHY = {
    "review_topic": "Review a topic you're finding hard",
    "review_item": "Review a phrase you keep missing",
    "continue_lesson": "Finish a lesson you started",
    "continue_situation": "Finish a situation you started",
    "low_confidence": "Build confidence in a topic you rated low",
    "confidence_checkin": "Tell us how confident you feel",
    "next_lesson": "Your next lesson",
    "next_situation": "Your next situation",
}
_TASK_TYPE = {"lesson": "study_lesson", "situation": "practice_situation", "topic": "confidence_checkin"}


def _views(conn, tasks):
    lessons = repo.lesson_titles(conn, [t["lesson_id"] for t in tasks if t["lesson_id"]])
    sits = repo.situation_titles(conn, [t["situation_id"] for t in tasks if t["situation_id"]])
    topics = repo.topics_by_ids(conn, [t["topic_id"] for t in tasks if t["topic_id"]])
    out = []
    for t in tasks:
        if t["lesson_id"]:
            target = {"type": "lesson", "id": t["lesson_id"], "title": lessons[t["lesson_id"]]}
        elif t["situation_id"]:
            target = {"type": "situation", "id": t["situation_id"], "title": sits[t["situation_id"]]}
        else:
            topic = topics[t["topic_id"]]
            target = {"type": "topic", "id": topic["id"], "slug": topic["slug"], "title": topic["name"]}
        out.append({"id": t["id"], "priority": t["priority"], "task_type": t["task_type"], "source": t["source"], "why": WHY[t["source"]],
                    "status": t["status"], "target": target, "plan_date": t["plan_date"], "completed_at": t["completed_at"]})
    return out


def _plan_view(conn, user_id, lang, date):
    repo.auto_complete_tasks(conn, user_id, lang, date)
    tasks = _views(conn, repo.list_tasks(conn, user_id, lang, date))
    return {"date": date, "generated": bool(tasks), "tasks": tasks,
            "done": sum(t["status"] == "done" for t in tasks), "total": len(tasks)}


def get_plan(db_path, user_id):
    with connect(db_path) as conn:
        ctx = learner_context(conn, user_id)
        return _plan_view(conn, user_id, ctx["target_language_id"], clock.today())


def generate_plan(db_path, user_id):
    """Create today's plan if there is none yet (from the current recommendations), then return it. Safe to call repeatedly."""
    with connect(db_path) as conn:  # one transaction: all tasks of a plan are written together or not at all
        ctx = learner_context(conn, user_id)
        lang, date, now = ctx["target_language_id"], clock.today(), clock.now()
        if not repo.list_tasks(conn, user_id, lang, date):
            recs = recommendations.build(conn, user_id, ctx)["recommendations"][: rules.DAILY_TASK_LIMIT]
            for i, rec in enumerate(recs, start=1):
                t = rec["target"]
                repo.insert_task(conn, user_id, lang, date, i, _TASK_TYPE[t["type"]], rec["kind"],
                                 t["id"] if t["type"] == "lesson" else None, t["id"] if t["type"] == "situation" else None,
                                 t["id"] if t["type"] == "topic" else None, now)
        return _plan_view(conn, user_id, lang, date)


def set_task_status(db_path, user_id, task_id, status):
    with connect(db_path) as conn:
        learner_context(conn, user_id)
        task = repo.get_task(conn, user_id, task_id)  # scoped by user: someone else's task is simply "not found"
        if task is None:
            raise NotFound()
        repo.set_task_status(conn, user_id, task_id, status, clock.now() if status == "done" else None)
        fresh = repo.get_task(conn, user_id, task_id)
        return _views(conn, [fresh])[0]
