"""Read-only learner overview queries. They return counts and coarse attributes (target language, CEFR level, age BAND, dates without times): never a name, an
email, a date of birth, a message, a transcript, a recording, a parent link or a raw user id outside this layer. Takes an open connection."""
from .admin_analytics import LEARNERS, per_user_activity

_AGE = "(CAST(strftime('%Y', :today) AS INTEGER) - CAST(strftime('%Y', p.date_of_birth) AS INTEGER) - (strftime('%m-%d', :today) < strftime('%m-%d', p.date_of_birth)))"
_LAST_ACTIVE = "(SELECT MAX(at) FROM (" + per_user_activity("u.id") + "))"

_BASE = f"""FROM users u
            LEFT JOIN learner_profiles p ON p.user_id = u.id
            LEFT JOIN languages lang ON lang.id = p.target_language_id
            LEFT JOIN age_groups g ON g.min_age <= {_AGE} AND (g.max_age IS NULL OR {_AGE} <= g.max_age)
            WHERE u.id IN {LEARNERS}"""


def _filters(language, cefr, age_group, active_since):
    clauses, extra = [], {}
    if language:
        clauses.append("lang.code = :language")
        extra["language"] = language
    if cefr:
        clauses.append("p.cefr_level = :cefr")
        extra["cefr"] = cefr
    if age_group:
        clauses.append("g.code = :age_group")
        extra["age_group"] = age_group
    if active_since:
        clauses.append(f"{_LAST_ACTIVE} >= :active_since")
        extra["active_since"] = active_since
    return ("".join(" AND " + c for c in clauses)), extra


def list_ids(conn, demo, today, language, cefr, age_group, active_since, limit, offset):
    """(total, [user ids]) of the learners matching the filters, newest first. The ids never leave the admin service (they become HMAC references there)."""
    where, extra = _filters(language, cefr, age_group, active_since)
    params = {"demo": demo, "today": today, **extra}
    total = conn.execute(f"SELECT COUNT(*) {_BASE}{where}", params).fetchone()[0]
    rows = conn.execute(f"SELECT u.id {_BASE}{where} ORDER BY u.created_at DESC, u.id DESC LIMIT :limit OFFSET :offset", {**params, "limit": limit, "offset": offset}).fetchall()
    return total, [r[0] for r in rows]


def all_ids(conn, demo):
    return [r[0] for r in conn.execute(f"SELECT id FROM users WHERE id IN {LEARNERS} ORDER BY id", {"demo": demo})]


def summary_rows(conn, demo, today, ids):
    """{id: {language, cefr, age_group, joined, last_active, lessons_completed, situations_completed, exercise_attempts}} for the given ids."""
    if not ids:
        return {}
    marks = ",".join(f":i{n}" for n in range(len(ids)))
    params = {"demo": demo, "today": today, **{f"i{n}": v for n, v in enumerate(ids)}}
    rows = conn.execute(
        f"""SELECT u.id, lang.code AS language, p.cefr_level AS cefr, g.code AS age_group, substr(u.created_at, 1, 10) AS joined, substr({_LAST_ACTIVE}, 1, 10) AS last_active,
                   (SELECT COUNT(*) FROM lesson_progress x WHERE x.user_id = u.id AND x.completed_at IS NOT NULL) AS lessons_completed,
                   (SELECT COUNT(*) FROM situation_progress x WHERE x.user_id = u.id AND x.completed_at IS NOT NULL) AS situations_completed,
                   (SELECT COUNT(*) FROM exercise_attempts x WHERE x.user_id = u.id) AS exercise_attempts
            {_BASE} AND u.id IN ({marks})""", params).fetchall()
    return {r["id"]: dict(r) for r in rows}


def cell_sizes(conn, demo, today):
    """{(language, cefr, age_group): learners}: how many learners share each combination of coarse attributes (a learner without a profile is (None, None, None))."""
    rows = conn.execute(f"SELECT lang.code, p.cefr_level, g.code, COUNT(*) {_BASE} GROUP BY lang.code, p.cefr_level, g.code", {"demo": demo, "today": today}).fetchall()
    return {(r[0], r[1], r[2]): r[3] for r in rows}


def detail_counts(conn, user_id, today_30_start):
    """Numbers only, for one learner."""
    q = lambda sql, **p: conn.execute(sql, {"u": user_id, **p}).fetchone()
    lessons = q("SELECT COUNT(*), COALESCE(SUM(completed_at IS NOT NULL), 0) FROM lesson_progress WHERE user_id = :u")
    situations = q("SELECT COUNT(*), COALESCE(SUM(completed_at IS NOT NULL), 0) FROM situation_progress WHERE user_id = :u")
    exercises = q("SELECT COUNT(*), COALESCE(SUM(is_correct), 0) FROM exercise_attempts WHERE user_id = :u")
    listening = q("SELECT COUNT(*), COALESCE(SUM(is_correct), 0) FROM listening_attempts WHERE user_id = :u")
    speaking = q("SELECT COUNT(*) FROM speaking_sessions WHERE user_id = :u AND stage NOT IN ('created', 'cancelled')")
    roleplay = q("SELECT COUNT(*), COALESCE(SUM(status = 'completed'), 0) FROM roleplay_sessions WHERE user_id = :u")
    xp = q("SELECT COALESCE(SUM(xp), 0) FROM xp_events WHERE user_id = :u")
    achievements = q("SELECT COUNT(*) FROM learner_achievements WHERE user_id = :u")
    days = q("SELECT COUNT(DISTINCT substr(at, 1, 10)) FROM (" + per_user_activity(":u") + ") WHERE at >= :start", start=today_30_start)
    return {"lessons_started": lessons[0], "lessons_completed": lessons[1], "situations_started": situations[0], "situations_completed": situations[1],
            "exercise_attempts": exercises[0], "exercise_correct": exercises[1], "listening_attempts": listening[0], "listening_correct": listening[1],
            "speaking_attempts": speaking[0], "roleplay_sessions_started": roleplay[0], "roleplay_sessions_completed": roleplay[1], "xp_total": xp[0],
            "achievements_unlocked": achievements[0], "active_days_30": days[0]}
