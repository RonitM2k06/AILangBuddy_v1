"""Admin analytics: aggregate, privacy-safe metrics derived from the evidence the learner-facing features already write.

Definitions that hold for every metric here (docs/ARCHITECTURE.md §21 repeats them):
  * learners: the learner role, no admin role, not the demo account. Parents, admins and the demo user never count.
  * time: UTC. A window is whole UTC calendar days, `from` and `to` both included, at most 365 days; 7d/30d/90d mean "the last N days ending today".
  * active on a day: at least one row of learning evidence that day (exercise / situation-step / listening attempts, speaking and pronunciation attempts, roleplay
    turns, micro-lesson attempts, XP events). A login is not learning activity and is never used.
  * a rate with nothing to divide reports no rate (null, status 'no_data'), never 0, and always carries its numerator and denominator when it is shown;
  * small cells: any figure that involves fewer than SMALL_CELL (5) learners is suppressed (value null, status 'suppressed'), together with the numerator and
    denominator behind it. A count of exactly zero involves nobody and is shown. Breakdowns fold their small buckets into an 'other' bucket (and, if even
    that is too small, the smallest visible bucket joins it) so a hidden bucket cannot be recovered by subtracting from a total.
Nothing in this module returns a learner identifier or any learner-written content."""
from datetime import date, datetime, timedelta, timezone

from .. import settings
from ..db import connect
from ..repositories import admin_analytics as repo
from .errors import InvalidInput

SMALL = settings.SMALL_CELL
REVIEW_MIN_ATTEMPTS, REVIEW_LOW, REVIEW_HIGH = 30, 0.20, 0.98


def utcnow():
    """Patched by tests that need a fixed clock."""
    return datetime.now(timezone.utc)


# ---------- windows ----------
def resolve_window(window=None, from_=None, to=None, default="30d"):
    """-> {'from': date, 'to': date, 'start': 'YYYY-MM-DD 00:00:00', 'end': (to+1 day) 00:00:00, 'days': n}. 422 for anything unusable."""
    today = utcnow().date()
    if window and (from_ or to):
        raise InvalidInput("window", "use either window or from/to, not both")
    if window:
        if window not in settings.ANALYTICS_WINDOWS:
            raise InvalidInput("window", "window must be 7d, 30d or 90d")
        last, first = today, today - timedelta(days=settings.ANALYTICS_WINDOWS[window] - 1)
    elif from_ or to:
        try:
            last = date.fromisoformat(to) if to else today
            first = date.fromisoformat(from_) if from_ else last - timedelta(days=settings.ANALYTICS_WINDOWS["30d"] - 1)
        except ValueError:
            raise InvalidInput("from", "dates are YYYY-MM-DD")
    else:
        last, first = today, today - timedelta(days=settings.ANALYTICS_WINDOWS[default] - 1)
    if first > last:
        raise InvalidInput("from", "from must not be after to")
    days = (last - first).days + 1
    if days > settings.ANALYTICS_MAX_WINDOW_DAYS:
        raise InvalidInput("to", f"a window is at most {settings.ANALYTICS_MAX_WINDOW_DAYS} days")
    return {"from": first, "to": last, "start": f"{first.isoformat()} 00:00:00", "end": f"{(last + timedelta(days=1)).isoformat()} 00:00:00", "days": days}


def _meta(w):
    return {"generated_at": utcnow().strftime("%Y-%m-%d %H:%M:%S"), "timezone": "UTC", "window": {"from": w["from"].isoformat(), "to": w["to"].isoformat(), "days": w["days"]}}


# ---------- suppression ----------
def counted(value, learners):
    """A count that involves `learners` learners. Zero learners means a zero count (shown); 1-4 learners means suppressed."""
    if 0 < learners < SMALL:
        return {"value": None, "status": "suppressed"}
    return {"value": value, "status": "ok"}


def people(n):
    """A count of learners themselves."""
    return counted(n, n)


def rate(numerator, denominator, learners, numerator_learners=None):
    """numerator / denominator over `learners` learners. No denominator -> no_data. Too few learners behind the denominator, or behind a numerator that is itself a
    count of learners (0 < n < 5), -> suppressed, and the numerator and denominator are withheld with the rate."""
    if denominator == 0:
        return {"numerator": 0, "denominator": 0, "rate": None, "status": "no_data"}
    if 0 < learners < SMALL or (numerator_learners is not None and 0 < numerator_learners < SMALL):
        return {"numerator": None, "denominator": None, "rate": None, "status": "suppressed"}
    return {"numerator": numerator, "denominator": denominator, "rate": round(numerator / denominator, 4), "status": "ok"}


def fold_buckets(items, measure):
    """items: [{'key', 'label', 'count', 'learners'}], 'learners' being the figure small-cell suppression looks at. Buckets with 1-4 learners are folded into 'other';
    measure(keys) -> (count, learners) for a SET of keys (so 'other' counts a learner once even if they sit in several folded buckets). If 'other' is still too small
    the smallest visible bucket joins it, until it is big enough or nothing is left (then 'other' is suppressed). Zero-learner buckets are not listed."""
    visible = sorted((i for i in items if i["learners"] >= SMALL), key=lambda i: (i["learners"], i["key"]))
    folded = [i for i in items if 0 < i["learners"] < SMALL]
    other = None
    if folded:
        while True:
            count, learners = measure([i["key"] for i in folded])
            if learners >= SMALL or not visible:
                other = {"key": "other", "label": "Other", "count": count, "learners": learners}
                break
            folded.append(visible.pop(0))
    out = [{"key": i["key"], "label": i["label"], "count": i["count"], "learners": i["learners"], "status": "ok"} for i in sorted(visible, key=lambda i: items.index(i))]
    if other:
        out.append({**other, "status": "ok"} if other["learners"] >= SMALL else {"key": "other", "label": "Other", "count": None, "learners": None, "status": "suppressed"})
    return out


def _additive(items):
    """measure() for buckets that partition the learners (each learner is in exactly one bucket)."""
    by_key = {i["key"]: i for i in items}
    return lambda keys: (sum(by_key[k]["count"] for k in keys), sum(by_key[k]["learners"] for k in keys))


def distribution(rows):
    """rows: [(key, label, learners)] where each learner is in exactly one bucket."""
    items = [{"key": k, "label": l, "count": n, "learners": n} for k, l, n in rows if n]
    total = sum(i["count"] for i in items)
    return {"total": people(total), "buckets": fold_buckets(items, _additive(items))}


# ---------- activity ----------
def _day(d):
    return d.isoformat()


def _active_by_day(conn, w, extra_before=29):
    first = w["from"] - timedelta(days=extra_before)
    pairs = repo.active_user_days(conn, settings.DEMO_HANDLE, f"{first.isoformat()} 00:00:00", w["end"])
    by_day = {}
    for user, day in pairs:
        by_day.setdefault(day, set()).add(user)
    return by_day


def _trailing(by_day, last, days):
    users = set()
    for i in range(days):
        users |= by_day.get(_day(last - timedelta(days=i)), set())
    return len(users)


def activity_series(db_path, window=None, from_=None, to=None, grain="day"):
    w = resolve_window(window, from_, to)
    with connect(db_path) as conn:
        by_day = _active_by_day(conn, w)
        evidence = repo.kinds_of_activity(conn, settings.DEMO_HANDLE, w["start"], w["end"])
    points = []
    if grain == "day":
        for i in range(w["days"]):
            d = w["from"] + timedelta(days=i)
            points.append({"date": _day(d), "dau": people(len(by_day.get(_day(d), set()))), "wau": people(_trailing(by_day, d, 7)), "mau": people(_trailing(by_day, d, 30))})
        series = points
    else:
        buckets = []
        for i in range(0, w["days"], 7):
            first = w["from"] + timedelta(days=i)
            last = min(first + timedelta(days=6), w["to"])
            users = set()
            for j in range((last - first).days + 1):
                users |= by_day.get(_day(first + timedelta(days=j)), set())
            buckets.append({"date": _day(first), "days": (last - first).days + 1, "active_learners": people(len(users))})
        series = buckets
    return {**_meta(w), "grain": grain, "points": series, "evidence_kinds": sorted(evidence)}


def _headline_activity(conn, w):
    by_day = _active_by_day(conn, {**w, "from": w["to"]}, extra_before=29)
    return {"as_of": _day(w["to"]), "dau": people(len(by_day.get(_day(w["to"]), set()))), "wau": people(_trailing(by_day, w["to"], 7)), "mau": people(_trailing(by_day, w["to"], 30))}


# ---------- learning ----------
def _learning(conn, w):
    d = settings.DEMO_HANDLE
    ls, lc, ll, llc = repo.progress_cohort(conn, d, "lesson_progress", "lesson_id", w["start"], w["end"])
    ss, sc, sl, slc = repo.progress_cohort(conn, d, "situation_progress", "situation_id", w["start"], w["end"])
    ea, ec, el = repo.attempt_accuracy(conn, d, "lesson", w["start"], w["end"])
    la, lcorrect, lel = repo.attempt_accuracy(conn, d, "listening", w["start"], w["end"])
    return {"lesson_completion": rate(lc, ls, ll, llc), "exercise_accuracy": rate(ec, ea, el), "situation_completion": rate(sc, ss, sl, slc), "listening_accuracy": rate(lcorrect, la, lel)}


def learning(db_path, window=None, from_=None, to=None):
    w = resolve_window(window, from_, to)
    with connect(db_path) as conn:
        return {**_meta(w), **_learning(conn, w)}


# ---------- speaking ----------
def _speaking(conn, w):
    d = settings.DEMO_HANDLE
    active = repo.active_learners(conn, d, w["start"], w["end"])
    _, speakers = repo.speaking_learners(conn, d, w["start"], w["end"])
    p_attempts, p_learners = repo.pronunciation_usage(conn, d, w["start"], w["end"])
    rp = repo.roleplay(conn, d, w["start"], w["end"])
    return {
        "speaking_participation": rate(speakers, active, active, speakers),
        "pronunciation_usage": {"attempts": counted(p_attempts, p_learners), "learners": people(p_learners)},
        "roleplay": {"started": counted(*rp["started"]), "completed": counted(*rp["completed"]),
                     "success": rate(rp["success"][0], rp["completed"][0], rp["completed"][1], rp["success"][1])},
    }


def speaking(db_path, window=None, from_=None, to=None):
    w = resolve_window(window, from_, to)
    with connect(db_path) as conn:
        return {**_meta(w), **_speaking(conn, w)}


# ---------- confidence and weaknesses ----------
def confidence_weakness(db_path, window=None, from_=None, to=None):
    w = resolve_window(window, from_, to)
    d = settings.DEMO_HANDLE
    with connect(db_path) as conn:
        topics = []
        for slug, name, learners, conf, acc in repo.confidence_vs_accuracy(conn, d, w["start"], w["end"]):
            if 0 < learners < SMALL:
                topics.append({"topic": {"slug": slug, "name": name}, "learners": None, "mean_confidence": None, "mean_accuracy": None, "gap": None, "status": "suppressed"})
            else:
                topics.append({"topic": {"slug": slug, "name": name}, "learners": learners, "mean_confidence": round(conf, 1), "mean_accuracy": round(acc, 1), "gap": round(conf - acc, 1), "status": "ok"})
        by_rule = []
        for rule, n, learners in repo.weaknesses_by_rule(conn, d):
            by_rule.append({"rule": rule, **({"weaknesses": None, "learners": None, "status": "suppressed"} if 0 < learners < SMALL else {"weaknesses": n, "learners": learners, "status": "ok"})})
        rows = repo.weaknesses_by_topic(conn, d)
        items = [{"key": slug, "label": name, "count": n, "learners": learners} for slug, name, n, learners in rows]
        by_topic = fold_buckets(items, lambda keys: repo.weaknesses_for_topics(conn, d, keys))
    return {**_meta(w), "confidence_vs_performance": topics, "weaknesses": {"as_of": "now", "by_rule": by_rule, "by_topic": by_topic}}


# ---------- engagement ----------
def _engagement(conn, w):
    d = settings.DEMO_HANDLE
    events, xp, xp_learners = repo.xp_activity(conn, d, w["start"], w["end"])
    days, streak_learners = repo.streak_activity(conn, d, w["from"].isoformat(), w["to"].isoformat())
    unlocks, unlock_learners = repo.achievement_totals(conn, d, w["start"], w["end"])
    items = [{"key": code, "label": title, "count": n, "learners": learners} for code, title, n, learners in repo.achievements_unlocked(conn, d, w["start"], w["end"])]
    assigned, claimed, challenge_learners = repo.challenge_activity(conn, d, w["from"].isoformat(), w["to"].isoformat())
    return {
        "xp": {"events": counted(events, xp_learners), "xp_awarded": counted(xp, xp_learners), "learners_earning": people(xp_learners)},
        "streak": {"streak_days": counted(days, streak_learners), "learners": people(streak_learners)},
        "achievements": {"unlocks": counted(unlocks, unlock_learners), "learners": people(unlock_learners),
                         "by_achievement": fold_buckets(items, lambda codes: repo.achievements_for(conn, d, w["start"], w["end"], codes))},
        "challenges": {"started": counted(assigned, challenge_learners), "claim_rate": rate(claimed, assigned, challenge_learners, None)},
    }


def engagement(db_path, window=None, from_=None, to=None):
    w = resolve_window(window, from_, to)
    with connect(db_path) as conn:
        return {**_meta(w), **_engagement(conn, w)}


# ---------- adaptive ----------
def _adaptive(conn, w):
    d = settings.DEMO_HANDLE
    shown, applied, learners, applied_learners = repo.recommendation_usage(conn, d, w["start"], w["end"])
    ml = repo.micro_lesson_usage(conn, d, w["start"], w["end"])
    attempts, correct, attempt_learners = ml["attempts"]
    return {
        "recommendations": {"shown": counted(shown, learners), "learners": people(learners), "applied_rate": rate(applied, shown, learners, applied_learners)},
        "micro_lessons": {"generated": counted(*ml["generated"]), "attempted": counted(*ml["attempted"]), "attempts": counted(attempts, attempt_learners),
                          "attempt_accuracy": rate(correct, attempts, attempt_learners)},
    }


def adaptive(db_path, window=None, from_=None, to=None):
    w = resolve_window(window, from_, to)
    with connect(db_path) as conn:
        return {**_meta(w), **_adaptive(conn, w)}


# ---------- content performance ----------
def content_performance(db_path, kind, window=None, from_=None, to=None, limit=50, offset=0):
    w = resolve_window(window, from_, to)
    d = settings.DEMO_HANDLE
    with connect(db_path) as conn:
        rows = repo.content_performance(conn, d, kind, w["start"], w["end"])
    items = []
    for unit_id, slug, title, status, attempts, correct, learners, started, completed in rows:
        base = {"id": unit_id, "slug": slug, "title": title, "status": status}
        if 0 < learners < SMALL:
            items.append({**base, "cell": "suppressed", "attempts": None, "learners": None, "accuracy": None, "completion": None, "review_candidate": False})
            continue
        accuracy = round(correct / attempts, 4)                   # started == distinct starters here: a learner has one progress row per unit
        items.append({**base, "cell": "ok", "attempts": attempts, "learners": learners, "accuracy": accuracy, "completion": rate(completed, started, started, completed) if kind != "listening" else None,
                      "review_candidate": attempts >= REVIEW_MIN_ATTEMPTS and (accuracy < REVIEW_LOW or accuracy > REVIEW_HIGH)})
    return {**_meta(w), "kind": kind, "items": items[offset:offset + limit], "total": len(items), "limit": limit, "offset": offset}


# ---------- dashboard ----------
def dashboard(db_path, window="30d"):
    w = resolve_window(window=window)
    d = settings.DEMO_HANDLE
    today = w["to"].isoformat()
    with connect(db_path) as conn:
        out = {**_meta(w), "window_name": window,
               "learners": {"total": people(repo.total_learners(conn, d)), "new": people(repo.new_learners(conn, d, w["start"], w["end"])),
                            "active": people(repo.active_learners(conn, d, w["start"], w["end"]))},
               "activity": _headline_activity(conn, w),
               "distributions": {"language": distribution(repo.language_distribution(conn, d)), "cefr": distribution(repo.cefr_distribution(conn, d)),
                                 "age_group": distribution(repo.age_group_distribution(conn, d, today))},
               "learning": _learning(conn, w), "speaking": _speaking(conn, w), "engagement": _engagement(conn, w), "adaptive": _adaptive(conn, w)}
    return out
