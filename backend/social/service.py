"""Friends and the friends leaderboard. No HTTP and no SQL in here.

Safety rules, in one place:
  * Learners only, and NOT the child age group: every call starts with `_member`, which refuses a child (the server decides, the
    UI only follows). There is no chat or messaging.
  * No discovery: a request needs the other learner's friend code, which they gave out themselves (it can be replaced at any
    time). There is no search and no list of learners. Wrong codes are throttled.
  * Only learners of the SAME age group can be friends, checked when a request is made and again whenever friends are shown (age
    is derived from the date of birth, so a teen turning 18 stops being listed beside teens).
  * Other learners are shown by display name, level and XP only: never an e-mail, date of birth, handle or user id. Requests and
    friendships are named by their own ids, and an id that is not the caller's is a 404.
  * The leaderboard has no input: it ranks the caller and their friends by XP the server credited."""
import secrets
from datetime import date, datetime, timedelta

from .. import settings  # noqa: F401  (kept for symmetry with the other services)
from ..db import connect
from ..gamification import rules, service as gamification
from ..learner import service as learner_service
from ..personalization import clock
from ..personalization.context import Forbidden, InvalidInput, NeedsProfile, NotFound, learner_context  # noqa: F401  (re-exported)
from ..repositories import gamification as game_repo, learner as learner_repo, social as repo

ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
_TIME = "%Y-%m-%d %H:%M:%S"
_failures: dict = {}


class InvalidCode(Exception):
    """The code is unknown or cannot be used by this learner. One answer for every reason."""


class Conflict(Exception):
    pass


class TooManyAttempts(Exception):
    def __init__(self, retry_after):
        super().__init__("too many wrong codes")
        self.retry_after = retry_after


def reset_throttle():
    _failures.clear()


def _group_of(conn, user_id):
    dob = repo.profile_dob(conn, user_id)
    if dob is None or not repo.has_learner_role(conn, user_id):
        return None
    found = learner_repo.age_group_id_for_age(conn, learner_service.age_on(date.fromisoformat(dob), learner_service.today()))
    return found["code"] if found else None


def _member(conn, user_id):
    """The caller's age group, or Forbidden for the child group."""
    group = learner_context(conn, user_id)["age_group_code"]
    if group not in rules.SOCIAL_AGE_GROUPS:
        raise Forbidden()
    return group


def _my_code(conn, user_id):
    game_repo.create_settings(conn, user_id, clock.now())
    code = game_repo.get_settings(conn, user_id)["friend_code"]
    if code is None:
        code = _fresh_code(conn, user_id)
    return code


def _fresh_code(conn, user_id):
    for _ in range(10):
        code = "".join(secrets.choice(ALPHABET) for _ in range(rules.FRIEND_CODE_LENGTH))
        if repo.user_for_code(conn, code) is None:
            game_repo.set_friend_code(conn, user_id, code)
            return code
    raise RuntimeError("could not make a friend code")


def rotate_code(db_path, user_id):
    with connect(db_path) as conn:
        _member(conn, user_id)
        game_repo.create_settings(conn, user_id, clock.now())
        return {"code": _fresh_code(conn, user_id)}


def _person(conn, other_id):
    gamification.sync(conn, other_id)
    lvl = gamification.level_summary(conn, other_id)
    return {"display_name": repo.display_name(conn, other_id), "level": lvl["level"], "rank": lvl["rank"], "xp": lvl["total"]}


def _same_group(conn, group, other_id):
    return _group_of(conn, other_id) == group


# ---------- requests ----------
def _check_throttle(user_id, now):
    window = timedelta(seconds=rules.CODE_WINDOW_SECONDS)
    recent = [t for t in _failures.get(user_id, []) if now - t < window]
    _failures[user_id] = recent
    if len(recent) >= rules.CODE_MAX_FAILURES:
        raise TooManyAttempts(int((recent[0] + window - now).total_seconds()) + 1)


def send_request(db_path, user_id, code):
    now_text = clock.now()
    now = datetime.strptime(now_text, _TIME)
    _check_throttle(user_id, now)
    code = "".join(ch for ch in code.upper() if ch.isalnum())
    try:
        with connect(db_path) as conn:
            group = _member(conn, user_id)
            target = repo.user_for_code(conn, code)
            if target is None or target == user_id or not _same_group(conn, group, target):
                raise InvalidCode()
            if repo.friendship_between(conn, user_id, target) is not None:
                raise Conflict("You are already friends.")
            if repo.pending_between(conn, user_id, target):
                raise Conflict("There is already a request waiting between you.")
            since = (now - timedelta(days=rules.REJECT_COOLDOWN_DAYS)).strftime(_TIME)
            if repo.recently_rejected(conn, user_id, target, since):
                raise Conflict("That request was not accepted. You can try again later.")
            if repo.count_pending_outgoing(conn, user_id) >= rules.MAX_PENDING_OUTGOING:
                raise Conflict("You have too many requests waiting.")
            if repo.count_friends(conn, user_id) >= rules.MAX_FRIENDS or repo.count_friends(conn, target) >= rules.MAX_FRIENDS:
                raise Conflict("Friend list is full.")
            request_id = repo.insert_request(conn, user_id, target, now_text)
            return {"id": request_id, "display_name": repo.display_name(conn, target), "created_at": now_text}
    except InvalidCode:
        _failures.setdefault(user_id, []).append(now)
        raise


def _answer(db_path, user_id, request_id, status):
    now = clock.now()
    with connect(db_path) as conn:
        group = _member(conn, user_id)
        req = repo.get_incoming(conn, user_id, request_id)
        if req is None or not _same_group(conn, group, req["requester_id"]):
            raise NotFound()
        if req["status"] != "pending":
            raise Conflict("This request has already been answered.")
        if status == "accepted" and (repo.count_friends(conn, user_id) >= rules.MAX_FRIENDS or repo.count_friends(conn, req["requester_id"]) >= rules.MAX_FRIENDS):
            raise Conflict("Friend list is full.")
        if not repo.respond(conn, request_id, user_id, status, now):
            raise Conflict("This request has already been answered.")
        if status == "accepted":
            repo.insert_friendship(conn, user_id, req["requester_id"], now)
        return {"status": status}


def accept(db_path, user_id, request_id):
    return _answer(db_path, user_id, request_id, "accepted")


def reject(db_path, user_id, request_id):
    return _answer(db_path, user_id, request_id, "rejected")


def remove_friend(db_path, user_id, friendship_id):
    with connect(db_path) as conn:
        _member(conn, user_id)
        if not repo.delete_friendship(conn, user_id, friendship_id):
            raise NotFound()


# ---------- views ----------
def _visible_friends(conn, user_id, group):
    return [f for f in repo.list_friendships(conn, user_id) if _same_group(conn, group, f["friend_id"])]


def friends(db_path, user_id):
    with connect(db_path) as conn:
        group = _member(conn, user_id)
        code = _my_code(conn, user_id)
        mine = [{"id": f["id"], "since": f["since"], **_person(conn, f["friend_id"])} for f in _visible_friends(conn, user_id, group)]
        inc = [{"id": r["id"], "display_name": repo.display_name(conn, r["other_id"]), "created_at": r["created_at"]}
               for r in repo.incoming(conn, user_id) if _same_group(conn, group, r["other_id"])]
        out = [{"id": r["id"], "display_name": repo.display_name(conn, r["other_id"]), "created_at": r["created_at"]} for r in repo.outgoing(conn, user_id)]
        return {"my_friend_code": code, "friends": mine, "incoming": inc, "outgoing": out, "max_friends": rules.MAX_FRIENDS}


def leaderboard(db_path, user_id, period):
    if period not in ("week", "all"):
        raise InvalidInput("period", "period must be week or all")
    with connect(db_path) as conn:
        group = _member(conn, user_id)
        zone, today, _ = gamification.sync(conn, user_id)
        start = (today - timedelta(days=today.weekday())).isoformat() if period == "week" else "0000-00-00"
        rows = []
        for who, uid in [(True, user_id)] + [(False, f["friend_id"]) for f in _visible_friends(conn, user_id, group)]:
            if not who:
                gamification.sync(conn, uid)
            lvl = gamification.level_summary(conn, uid)
            rows.append({"display_name": repo.display_name(conn, uid), "xp": game_repo.xp_since(conn, uid, start), "level": lvl["level"], "rank_name": lvl["rank"],
                         "is_me": who, "_id": uid})
    rows.sort(key=lambda r: (-r["xp"], r["display_name"].lower(), r["_id"]))
    rank, previous = 0, None
    for position, r in enumerate(rows, start=1):
        if r["xp"] != previous:
            rank, previous = position, r["xp"]
        r["rank"] = rank
        del r["_id"]
    return {"period": period, "entries": rows}
