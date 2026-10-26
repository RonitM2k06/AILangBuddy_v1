"""XP, levels, streaks, freezes, achievements and challenges for the authenticated learner. No HTTP and no SQL in here.

The one entry point that changes anything is `sync`. It looks at what the learner has ALREADY done in the existing tables and
credits it (once each, by a UNIQUE ledger row), then derives days, streak, challenge instances and achievements. It is
idempotent, so calling it again (a page reload, a friend opening the leaderboard) changes nothing; there is no way to ask it to
award a particular amount or to unlock anything by name. Everything it writes is in the caller's transaction."""
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo, available_timezones

from ..db import connect
from ..personalization import clock
from ..personalization.context import InvalidInput, NeedsProfile, NotFound  # noqa: F401  (re-exported)
from ..repositories import gamification as repo
from . import rules, streaks

_TIME = "%Y-%m-%d %H:%M:%S"
RECENT_EVENTS = 10
KIND_LABELS = {"exercise": "Exercise answered", "lesson": "Lesson completed", "situation": "Situation completed", "listening": "Listening activity",
               "speaking": "Speaking practice", "daily_task": "Daily task", "challenge": "Challenge reward"}
METRIC_LABELS = {"lessons_completed": "lessons completed", "situations_completed": "situations completed", "listening_correct": "listening activities right",
                 "speaking_completed": "speaking practices", "longest_streak": "day streak", "challenges_claimed": "challenges claimed", "total_xp": "XP"}


class Conflict(Exception):
    pass


def _zone(name):
    try:
        return ZoneInfo(name)
    except Exception:
        return ZoneInfo("UTC")


def _utc(text):
    return datetime.strptime(text[:19], _TIME).replace(tzinfo=timezone.utc)


def local_day(utc_text, zone):
    return _utc(utc_text).astimezone(zone).date()


def _iso(d):
    return d.isoformat()


# ---------- sync ----------
def _credit(conn, user_id, zone, now):
    new = repo.uncredited_sources(conn, user_id)
    new.sort(key=lambda s: (s["earned_at"], rules.KIND_ORDER[s["kind"]], s["source_id"]))
    for s in new:
        day = _iso(local_day(s["earned_at"], zone))
        room = max(0, rules.DAILY_XP_CAP - repo.activity_xp_on(conn, user_id, day))
        repo.insert_event(conn, user_id, s["kind"], s["source_id"], min(rules.XP_RULES[s["kind"]], room), s["earned_at"], day, now)


def _streak(conn, user_id, today, now):
    repo.record_days(conn, user_id)
    result = streaks.compute([date.fromisoformat(d) for d in repo.list_days(conn, user_id)],
                             [date.fromisoformat(d) for d in repo.freeze_days(conn, user_id, "used")],
                             [date.fromisoformat(d) for d in repo.freeze_days(conn, user_id, "earned")], today)
    for d in result.new_earned:
        repo.add_freeze(conn, user_id, "earned", _iso(d), now)
    for d in result.new_used:
        repo.add_freeze(conn, user_id, "used", _iso(d), now)
    return result


def _period(period, today):
    if period == "daily":
        return today, today
    monday = today - timedelta(days=today.weekday())
    return monday, monday + timedelta(days=6)


def _progress(conn, user_id, c, current_streak):
    s, e = c["period_start"], c["period_end"]
    if c["metric"] == "exercises":
        value = repo.count_between(conn, user_id, "exercise", s, e)
    elif c["metric"] == "listening":
        value = repo.count_between(conn, user_id, "listening", s, e)
    elif c["metric"] == "lessons":
        value = repo.count_between(conn, user_id, "lesson", s, e)
    elif c["metric"] == "xp":
        value = repo.xp_between(conn, user_id, s, e)
    else:
        value = current_streak
    return min(value, c["target"])


def _metric(conn, user_id, metric, longest):
    return {"lessons_completed": lambda: repo.count_kind(conn, user_id, "lesson"), "situations_completed": lambda: repo.count_kind(conn, user_id, "situation"),
            "listening_correct": lambda: repo.count_kind(conn, user_id, "listening"), "speaking_completed": lambda: repo.count_kind(conn, user_id, "speaking"),
            "longest_streak": lambda: longest, "challenges_claimed": lambda: repo.count_claimed(conn, user_id),
            "total_xp": lambda: repo.total_xp(conn, user_id)}[metric]()


def _unlock(conn, user_id, longest, now):
    for a in repo.list_achievements(conn, user_id):
        if a["unlocked_at"] is None and _metric(conn, user_id, a["metric"], longest) >= a["threshold"]:
            repo.unlock(conn, user_id, a["id"], now)


def sync(conn, user_id):
    """Brings the learner's gamification up to date inside the caller's transaction. Returns (zone, today, streak result)."""
    now = clock.now()
    repo.create_settings(conn, user_id, now)
    zone = _zone(repo.get_settings(conn, user_id)["timezone"])
    today = local_day(now, zone)
    _credit(conn, user_id, zone, now)
    result = _streak(conn, user_id, today, now)
    for c in repo.active_challenges(conn):
        start, end = _period(c["period"], today)
        repo.ensure_instance(conn, user_id, c["id"], _iso(start), _iso(end))
    _unlock(conn, user_id, result.longest, now)
    return zone, today, result


# ---------- views ----------
def _level_view(total):
    level = rules.level_for(total)
    start = rules.level_start(level)
    nxt = rules.level_start(level + 1) if level < rules.MAX_LEVEL else None
    return {"total": total, "level": level, "rank": rules.rank_for(level), "level_start": start, "next_level_at": nxt,
            "into_level": total - start, "to_next": None if nxt is None else nxt - total}


def level_summary(conn, user_id):
    """Level and rank from the ledger as it stands (used for friends and the leaderboard, after a sync)."""
    return _level_view(repo.total_xp(conn, user_id))


def _balance(conn, user_id):
    return len(repo.freeze_days(conn, user_id, "earned")) - len(repo.freeze_days(conn, user_id, "used"))


def summary(db_path, user_id):
    with connect(db_path) as conn:
        zone, today, st = sync(conn, user_id)
        total = repo.total_xp(conn, user_id)
        return {"xp": _level_view(total),
                "today": {"date": _iso(today), "xp": repo.activity_xp_on(conn, user_id, _iso(today)), "cap": rules.DAILY_XP_CAP},
                "streak": {"current": st.current, "longest": st.longest, "active_today": st.active_today, "at_risk": st.at_risk,
                           "freezes": _balance(conn, user_id), "max_freezes": rules.MAX_FREEZES, "freeze_every": rules.FREEZE_EVERY,
                           "freeze_log": repo.freeze_log(conn, user_id, 10)},
                "timezone": repo.get_settings(conn, user_id)["timezone"],
                "recent": [{"what": KIND_LABELS[e["kind"]], "xp": e["xp"], "day": e["day"]} for e in repo.recent_events(conn, user_id, RECENT_EVENTS)]}


def achievements(db_path, user_id):
    with connect(db_path) as conn:
        _, _, st = sync(conn, user_id)
        out = []
        for a in repo.list_achievements(conn, user_id):
            value = _metric(conn, user_id, a["metric"], st.longest)
            out.append({"code": a["code"], "title": a["title"], "description": a["description"], "unlocked": a["unlocked_at"] is not None,
                        "unlocked_at": a["unlocked_at"], "progress": min(value, a["threshold"]), "target": a["threshold"], "unit": METRIC_LABELS[a["metric"]]})
        return out


def _challenge_view(conn, user_id, c, today, current_streak):
    progress = _progress(conn, user_id, c, current_streak)
    if c["claimed_at"]:
        status = "claimed"
    elif c["period_end"] < _iso(today):
        status = "expired"
    elif progress >= c["target"]:
        status = "claimable"
    else:
        status = "active"
    return {"id": c["id"], "title": c["title"], "period": c["period"], "progress": progress, "target": c["target"], "reward_xp": c["reward_xp"],
            "status": status, "period_start": c["period_start"], "period_end": c["period_end"], "claimed_at": c["claimed_at"]}


def challenges(db_path, user_id):
    with connect(db_path) as conn:
        _, today, st = sync(conn, user_id)
        return [_challenge_view(conn, user_id, c, today, st.current) for c in repo.current_instances(conn, user_id, _iso(today))]


def claim(db_path, user_id, instance_id):
    """Pays a finished challenge once. The reward comes from the challenge definition; progress is recomputed here, never trusted."""
    with connect(db_path) as conn:              # one transaction: the claim mark and the XP row are written together or not at all
        _, today, st = sync(conn, user_id)
        c = repo.get_instance(conn, user_id, instance_id)      # someone else's challenge is simply "not found"
        if c is None:
            raise NotFound()
        view = _challenge_view(conn, user_id, c, today, st.current)
        if view["status"] == "claimed":
            raise Conflict("This challenge has already been claimed.")
        if view["status"] == "expired":
            raise Conflict("This challenge has ended.")
        if view["status"] != "claimable":
            raise Conflict("This challenge is not finished yet.")
        now = clock.now()
        if not repo.mark_claimed(conn, user_id, instance_id, now):
            raise Conflict("This challenge has already been claimed.")
        if not repo.insert_event(conn, user_id, "challenge", instance_id, c["reward_xp"], now, _iso(today), now):
            raise Conflict("This challenge has already been claimed.")
        _unlock(conn, user_id, st.longest, now)
        fresh = repo.get_instance(conn, user_id, instance_id)
        return {"challenge": _challenge_view(conn, user_id, fresh, today, st.current), "xp": _level_view(repo.total_xp(conn, user_id))}


def set_timezone(db_path, user_id, name):
    if not isinstance(name, str) or name not in available_timezones():
        raise InvalidInput("timezone", "Unknown timezone")
    with connect(db_path) as conn:
        sync(conn, user_id)                     # what was done so far keeps the day it happened on under the old timezone
        repo.set_timezone(conn, user_id, name)
    return {"timezone": name}
