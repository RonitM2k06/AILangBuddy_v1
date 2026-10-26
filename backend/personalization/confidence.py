"""Self-reported confidence: recording, current values, history. It is kept apart from performance (accuracy
computed from attempts), which is returned next to it but never mixed into it."""
from ..db import connect
from ..repositories import curriculum, personalization as repo, situations
from . import clock, rules
from .context import InvalidInput, learner_context


def _record_view(row):
    if row["topic_slug"]:
        dim = {"type": "topic", "slug": row["topic_slug"], "name": row["topic_name"], "icon": row["topic_icon"]}
    else:
        dim = {"type": "skill", "slug": row["skill_code"], "name": row["skill_name"]}
    return {"id": row["id"], "dimension": dim, "score": row["score"], "source": row["source"],
            "lesson_id": row["lesson_id"], "situation_id": row["situation_id"], "recorded_at": row["recorded_at"]}


def record(db_path, user_id, *, topic=None, skill=None, score, source="self_report", lesson_id=None, situation_id=None):
    with connect(db_path) as conn:
        ctx = learner_context(conn, user_id)
        if (topic is None) == (skill is None):
            raise InvalidInput("topic", "Provide exactly one of topic or skill")
        topic_id = skill_id = None
        if topic is not None:
            found = repo.get_topic(conn, topic)
            if found is None or found["id"] not in {t["id"] for t in repo.topics_with_content(conn, ctx["target_language_id"], ctx["max_rank"], ctx["age_group_id"])}:
                raise InvalidInput("topic", "Unknown topic, or none available for your language and level")
            topic_id = found["id"]
        else:
            found = repo.get_skill(conn, skill)
            if found is None:
                raise InvalidInput("skill", "Unknown skill")
            skill_id = found["id"]
        # the context (what the rating followed) must agree with the source and be something this learner may see
        if source == "self_report" and (lesson_id is not None or situation_id is not None):
            raise InvalidInput("source", "A plain self-report has no lesson or situation")
        if source == "lesson":
            if lesson_id is None or situation_id is not None:
                raise InvalidInput("lesson_id", "Provide lesson_id for source 'lesson'")
            if curriculum.get_available_lesson(conn, lesson_id, ctx["target_language_id"], ctx["max_rank"], ctx["age_group_id"]) is None:
                raise InvalidInput("lesson_id", "Unknown lesson")
        if source == "situation":
            if situation_id is None or lesson_id is not None:
                raise InvalidInput("situation_id", "Provide situation_id for source 'situation'")
            if situations.get_available(conn, situation_id, ctx["target_language_id"], ctx["max_rank"], ctx["age_group_id"]) is None:
                raise InvalidInput("situation_id", "Unknown situation")
        new_id = repo.insert_confidence(conn, user_id, ctx["target_language_id"], topic_id, skill_id, score, source,
                                        lesson_id, situation_id, clock.now())
        return _record_view(repo.get_confidence(conn, user_id, new_id))


def _performance(window):
    """Recent accuracy for a topic from attempts (None when the learner has not answered anything there)."""
    if not window:
        return None
    return {"attempts": window["attempts"], "correct": window["attempts"] - window["incorrect"],
            "accuracy": round((window["attempts"] - window["incorrect"]) / window["attempts"], 2)}


def overview(db_path, user_id):
    with connect(db_path) as conn:
        ctx = learner_context(conn, user_id)
        lang = ctx["target_language_id"]
        topics = repo.topics_with_content(conn, lang, ctx["max_rank"], ctx["age_group_id"])
        latest_topics = repo.latest_confidence(conn, user_id, lang, "topic_id")
        windows = repo.recent_topic_window(conn, user_id, lang, rules.TOPIC_WINDOW)
        latest_skills = repo.latest_confidence(conn, user_id, lang, "skill_id")
        skills = repo.list_skills(conn)
    scored = [latest_topics[t["id"]]["score"] for t in topics if t["id"] in latest_topics]
    return {
        # unweighted mean of the learner's latest topic self-reports; None until they have reported at least one
        "overall": round(sum(scored) / len(scored)) if scored else None,
        "topics": [{"topic": {"slug": t["slug"], "name": t["name"], "icon": t["icon"]},
                    "confidence": latest_topics.get(t["id"]), "performance": _performance(windows.get(t["id"]))} for t in topics],
        "skills": [{"skill": {"code": s["code"], "name": s["name"]}, "confidence": latest_skills.get(s["id"])} for s in skills],
    }


def history(db_path, user_id, *, topic=None, skill=None, limit=50):
    with connect(db_path) as conn:
        ctx = learner_context(conn, user_id)
        if topic is not None and skill is not None:
            raise InvalidInput("topic", "Filter by topic or skill, not both")
        topic_id = skill_id = None
        if topic is not None:
            found = repo.get_topic(conn, topic)
            if found is None:
                raise InvalidInput("topic", "Unknown topic")
            topic_id = found["id"]
        if skill is not None:
            found = repo.get_skill(conn, skill)
            if found is None:
                raise InvalidInput("skill", "Unknown skill")
            skill_id = found["id"]
        rows = repo.confidence_history(conn, user_id, ctx["target_language_id"], topic_id, skill_id, limit)
    return [_record_view(r) for r in rows]
