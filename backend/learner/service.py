"""Learner profile rules: validation, server-side age-group derivation, persistence. No HTTP in here."""
from datetime import date, datetime, timezone

from ..db import connect
from ..repositories import learner
from ..repositories import parent as parent_repo

MAX_AGE_YEARS = 120


class AgeGroupLocked(Exception):
    """The date of birth would move a parent-linked learner into another age group."""


class ProfileError(ValueError):
    """A semantic validation failure tied to one request field."""

    def __init__(self, field, message):
        super().__init__(message)
        self.field = field
        self.message = message


def today():
    return datetime.now(timezone.utc).date()


def age_on(dob, on):
    return on.year - dob.year - ((on.month, on.day) < (dob.month, dob.day))


def with_age_group(conn, ctx):
    """Adds age_group_id / age_group_code to a learner context (which carries date_of_birth). Derived on every call from the
    date of birth, never stored; date_of_birth itself is dropped so it travels no further."""
    dob = date.fromisoformat(ctx.pop("date_of_birth"))
    group = learner.age_group_id_for_age(conn, age_on(dob, today()))
    ctx["age_group_id"], ctx["age_group_code"] = group["id"], group["code"]
    return ctx


def _parse_dob(text, now):
    try:
        dob = date.fromisoformat(text)
    except ValueError:
        raise ProfileError("date_of_birth", "Not a valid date (use YYYY-MM-DD)")
    if dob > now:
        raise ProfileError("date_of_birth", "Date of birth cannot be in the future")
    if age_on(dob, now) > MAX_AGE_YEARS:
        raise ProfileError("date_of_birth", "Date of birth is not plausible")
    return dob


def _view(conn, profile, now):
    age = age_on(date.fromisoformat(profile["date_of_birth"]), now)
    return {**profile, "age": age, "age_group": learner.age_group_for_age(conn, age)}  # derived, never stored


def get_profile(db_path, user_id):
    now = today()
    with connect(db_path) as conn:
        profile = learner.get_profile(conn, user_id)
        return _view(conn, profile, now) if profile else None


def _check_age_group_lock(conn, user_id, new_dob, now):
    """A learner followed by a parent cannot move themselves into another age group by editing their date of birth: the age group decides
    which features they get (social, voice, the external model), so the change has to wait until no parent is linked. Edits that keep the
    age group, and a first profile, are unaffected."""
    current = learner.get_profile(conn, user_id)
    if current is None or not parent_repo.count_parents(conn, user_id):
        return
    old_group = learner.age_group_for_age(conn, age_on(date.fromisoformat(current["date_of_birth"]), now))
    new_group = learner.age_group_for_age(conn, age_on(new_dob, now))
    if (old_group and old_group["code"]) != (new_group and new_group["code"]):
        raise AgeGroupLocked()


def save_profile(db_path, user_id, *, native_language, target_language, cefr_level, date_of_birth):
    now = today()
    dob = _parse_dob(date_of_birth, now)
    if native_language == target_language:
        raise ProfileError("target_language", "Target language must differ from native language")
    with connect(db_path) as conn:
        native_id = learner.get_language_id(conn, native_language)
        if native_id is None:
            raise ProfileError("native_language", "Unknown language")
        target_id = learner.get_language_id(conn, target_language)
        if target_id is None:
            raise ProfileError("target_language", "Unknown language")
        if not learner.is_supported_combination(conn, target_id, cefr_level):
            raise ProfileError("cefr_level", f"{cefr_level} is not available for {target_language}")
        _check_age_group_lock(conn, user_id, dob, now)
        learner.upsert_profile(conn, user_id, native_id, target_id, cefr_level, dob.isoformat(),
                               datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"))
        return _view(conn, learner.get_profile(conn, user_id), now)
