"""The parent portal: linking a parent to a child, the parent's read-only view of the child, and parental controls.
No HTTP and no SQL in here.

Safety rules, in one place:
  * A link is created only by redeeming a one-time code made by the learner's own session. There is no lookup of learners.
  * Every read or change of a child starts from the PARENT's own link (parent id + link id). A link id that is unknown or
    belongs to someone else is NotFound, indistinguishable from one that does not exist.
  * The portal composes the existing services (lessons, listening, speaking, pronunciation, confidence, weaknesses, plan); it
    keeps no copy of progress, and it never returns transcripts, recordings, e-mail, date of birth or another user's data.
  * Controls only restrict (see parent/controls.py)."""
import hashlib
import secrets
import sqlite3
from datetime import datetime, timedelta

from .. import settings
from ..curriculum import service as curriculum
from ..db import connect
from ..learner import service as learner_service
from ..listening import service as listening
from ..personalization import clock, confidence, plan, weaknesses
from ..personalization.context import InvalidInput, NeedsProfile, NotFound, learner_context  # noqa: F401  (re-exported)
from ..repositories import parent as repo
from ..situations import service as situations
from ..speaking import assessment, service as speaking
from . import controls

ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"     # no 0/O/1/I: a code is read aloud or copied by hand
_TIME = "%Y-%m-%d %H:%M:%S"
ACTIVITY_LIMIT = 20
CONFIDENCE_HISTORY = 30
_failures: dict = {}                              # parent id -> times of recent wrong codes (per process, like the login throttle)


class InvalidCode(Exception):
    """The code is unknown, expired, used, or not usable by this parent. One answer for all of them."""


class Conflict(Exception):
    pass


class TooManyAttempts(Exception):
    def __init__(self, retry_after):
        super().__init__("too many wrong codes")
        self.retry_after = retry_after


def reset_throttle():
    _failures.clear()


def _hash(code):
    return hashlib.sha256(code.encode()).hexdigest()


def _normalize(code):
    return "".join(ch for ch in code.upper() if ch.isalnum())


# ---------- linking ----------
def issue_code(db_path, learner_id):
    """A fresh one-time code for this learner (any earlier unused code stops working). Returned once; only its hash is stored."""
    code = "".join(secrets.choice(ALPHABET) for _ in range(settings.PARENT_CODE_LENGTH))
    now = datetime.strptime(clock.now(), _TIME)
    with connect(db_path) as conn:
        repo.delete_unused_codes(conn, learner_id)
        repo.insert_code(conn, learner_id, _hash(code), now.strftime(_TIME), (now + timedelta(seconds=settings.PARENT_CODE_TTL_SECONDS)).strftime(_TIME))
    return {"code": code, "expires_in_seconds": settings.PARENT_CODE_TTL_SECONDS}


def _check_throttle(parent_id, now):
    window = timedelta(seconds=settings.PARENT_CODE_WINDOW_SECONDS)
    recent = [t for t in _failures.get(parent_id, []) if now - t < window]
    _failures[parent_id] = recent
    if len(recent) >= settings.PARENT_CODE_MAX_FAILURES:
        raise TooManyAttempts(int((recent[0] + window - now).total_seconds()) + 1)


def link_with_code(db_path, parent_id, code):
    now_text = clock.now()
    now = datetime.strptime(now_text, _TIME)
    _check_throttle(parent_id, now)
    try:
        with connect(db_path) as conn:      # one transaction: consuming the code and creating the link, or neither
            found = repo.find_live_code(conn, _hash(_normalize(code)), now_text)
            if found is None or found["learner_id"] == parent_id:
                raise InvalidCode()
            if repo.link_exists(conn, parent_id, found["learner_id"]):
                raise Conflict("This child is already linked to your account.")
            if repo.count_children(conn, parent_id) >= settings.MAX_CHILDREN_PER_PARENT:
                raise Conflict("You have reached the number of children one account can follow.")
            if repo.count_parents(conn, found["learner_id"]) >= settings.MAX_PARENTS_PER_CHILD:
                raise Conflict("This child already has the most parents that can be linked.")
            if not repo.consume_code(conn, found["id"], parent_id, now_text):
                raise InvalidCode()
            link_id = repo.insert_link(conn, parent_id, found["learner_id"], now_text)
            return _child(db_path, repo.get_link(conn, parent_id, link_id))
    except InvalidCode:
        _failures.setdefault(parent_id, []).append(now)
        raise
    except sqlite3.IntegrityError:          # e.g. a parent who is not (or is no longer) a parent: the database refuses the link
        raise InvalidCode()


def unlink(db_path, parent_id, link_id):
    with connect(db_path) as conn:
        if not repo.delete_link(conn, parent_id, link_id):
            raise NotFound()


# ---------- views ----------
def _owned(conn, parent_id, link_id):
    link = repo.get_link(conn, parent_id, link_id)
    if link is None:
        raise NotFound()
    return link


def _profile(db_path, learner_id):
    p = learner_service.get_profile(db_path, learner_id)
    if p is None:
        return {"has_profile": False, "age_group": None, "target_language": None, "cefr_level": None}
    return {"has_profile": True, "age_group": p["age_group"], "target_language": p["target_language"], "cefr_level": p["cefr_level"]}


def _child(db_path, link):
    return {"id": link["link_id"], "display_name": link["display_name"], "linked_at": link["linked_at"], **_profile(db_path, link["learner_id"])}


def _optional(fn, *args, **kwargs):
    """The existing services need a learner profile; a child without one simply has nothing to show yet."""
    try:
        return fn(*args, **kwargs)
    except NeedsProfile:
        return None


def list_children(db_path, parent_id):
    with connect(db_path) as conn:
        links = repo.list_links(conn, parent_id)
    return [_child(db_path, l) for l in links]


def _link_and_child(db_path, parent_id, link_id):
    with connect(db_path) as conn:
        return _owned(conn, parent_id, link_id)


def progress(db_path, parent_id, link_id):
    link = _link_and_child(db_path, parent_id, link_id)
    uid = link["learner_id"]
    return {"child": _child(db_path, link),
            "lessons": _optional(curriculum.lesson_progress, db_path, uid),
            "situations": _optional(situations.situation_progress, db_path, uid),
            "listening": _optional(listening.progress, db_path, uid),
            "speaking": _optional(speaking.progress, db_path, uid),          # counts only: no transcripts, no recordings
            "pronunciation": _optional(assessment.progress, db_path, uid),   # per-method; test scores are labelled as such
            "daily_plan": _optional(plan.get_plan, db_path, uid)}


def weaknesses_view(db_path, parent_id, link_id):
    link = _link_and_child(db_path, parent_id, link_id)
    found = _optional(weaknesses.list_weaknesses, db_path, link["learner_id"])
    out = []
    for w in found or []:
        view = {"rule": w["rule"], "severity": w["severity"], "attempts": w["attempts"], "incorrect": w["incorrect"], "accuracy": w["accuracy"],
                "last_evidence_at": w["last_evidence_at"]}
        correct = w["attempts"] - w["incorrect"]
        if "topic" in w:
            view["topic"] = w["topic"]
            view["summary"] = f"{correct} of the last {w['attempts']} {w['topic']['name']} questions were answered correctly."
        else:
            it = w["item"]
            view["phrase"] = {"text": it["text"], "pronunciation": it["pronunciation"], "meaning": it["meaning"]}
            view["summary"] = f"This phrase was answered wrongly {w['incorrect']} times out of {w['attempts']}."
        out.append(view)
    return {"child": _child(db_path, link), "weaknesses": out if found is not None else None}


def confidence_view(db_path, parent_id, link_id):
    link = _link_and_child(db_path, parent_id, link_id)
    uid = link["learner_id"]
    return {"child": _child(db_path, link), "overview": _optional(confidence.overview, db_path, uid),
            "history": _optional(confidence.history, db_path, uid, limit=CONFIDENCE_HISTORY)}


def activity_view(db_path, parent_id, link_id):
    link = _link_and_child(db_path, parent_id, link_id)
    with connect(db_path) as conn:
        try:
            ctx = learner_context(conn, link["learner_id"])
        except NeedsProfile:
            return {"child": _child(db_path, link), "recent": None, "by_source": None}
        recent = repo.recent_activity(conn, link["learner_id"], ctx["target_language_id"], ACTIVITY_LIMIT)
        by_source = repo.activity_by_source(conn, link["learner_id"], ctx["target_language_id"])
    return {"child": _child(db_path, link),
            "recent": [{"source": r["source"], "correct": bool(r["is_correct"]), "difficulty": r["difficulty"], "at": r["attempted_at"]} for r in recent],
            "by_source": by_source}


def overview(db_path, parent_id, link_id):
    link = _link_and_child(db_path, parent_id, link_id)
    prog = progress(db_path, parent_id, link_id)
    weak = weaknesses_view(db_path, parent_id, link_id)["weaknesses"]
    conf = confidence_view(db_path, parent_id, link_id)
    act = activity_view(db_path, parent_id, link_id)
    lessons = prog["lessons"] or []
    return {"child": prog["child"],
            "lessons": {"started": len(lessons), "completed": sum(1 for l in lessons if l["status"] == "completed")},
            "listening": prog["listening"], "speaking": prog["speaking"], "pronunciation": prog["pronunciation"],
            "daily_plan": prog["daily_plan"],
            "confidence_overall": conf["overview"]["overall"] if conf["overview"] else None,
            "weaknesses_count": len(weak) if weak is not None else None,
            "recent_activity": act["recent"][:5] if act["recent"] is not None else None,
            "controls": get_controls(db_path, parent_id, link["link_id"])}


# ---------- controls ----------
def _controls_view(conn, link):
    control = repo.get_control(conn, link["link_id"]) or {"voice_disabled": 0, "updated_at": None}
    try:
        ctx = learner_context(conn, link["learner_id"])
        reason = controls.voice_block_reason(conn, ctx, link["learner_id"])
    except NeedsProfile:
        reason = "parent_control" if repo.voice_disabled_for_learner(conn, link["learner_id"]) else None
    return {"voice_disabled": bool(control["voice_disabled"]), "updated_at": control["updated_at"],
            "voice_available_to_child": reason is None, "voice_unavailable_reason": reason}


def get_controls(db_path, parent_id, link_id):
    with connect(db_path) as conn:
        return _controls_view(conn, _owned(conn, parent_id, link_id))


def set_controls(db_path, parent_id, link_id, *, voice_disabled):
    if not isinstance(voice_disabled, bool):
        raise InvalidInput("voice_disabled", "voice_disabled must be true or false")
    with connect(db_path) as conn:
        link = _owned(conn, parent_id, link_id)
        repo.set_control(conn, link["link_id"], voice_disabled, clock.now())
        return _controls_view(conn, link)
