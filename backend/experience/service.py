"""The learner's age-aware experience: which mode the app presents, and the teen home. Both are thin: the age group comes from
the profile (derived from the date of birth, Phase 3) and the teen home only composes the existing curriculum, recommendation,
weakness and daily-plan services, so adaptive difficulty and weaknesses are not duplicated. No HTTP and no SQL in here."""
from ..curriculum import service as curriculum
from ..db import connect
from ..learner import service as learner_service
from ..personalization import difficulty, plan, recommendations, weaknesses
from ..personalization.context import Forbidden, NeedsProfile, learner_context  # noqa: F401  (re-exported)

FEATURES = {
    "child": {"adventure": True, "lives": True, "voice_practice": False, "path": False},
    "teen": {"adventure": False, "lives": False, "voice_practice": True, "path": True},
    "adult": {"adventure": False, "lives": False, "voice_practice": True, "path": False},
}
TOP_WEAKNESSES = 3


def experience(db_path, user_id):
    profile = learner_service.get_profile(db_path, user_id)
    if profile is None:
        raise NeedsProfile()
    group = profile["age_group"]               # {code, label}; the date of birth is not part of this answer
    return {"mode": group["code"], "age_group": group, "features": FEATURES[group["code"]]}


def teen_home(db_path, user_id):
    with connect(db_path) as conn:
        if learner_context(conn, user_id)["age_group_code"] != "teen":
            raise Forbidden()
    recs = recommendations.get_recommendations(db_path, user_id)
    return {"path": curriculum.list_lessons(db_path, user_id),           # already filtered for this age group
            "next_activity": recs["next_activity"], "difficulty": recs["difficulty"],
            "weaknesses": weaknesses.list_weaknesses(db_path, user_id)[:TOP_WEAKNESSES],
            "daily_plan": plan.get_plan(db_path, user_id)}
