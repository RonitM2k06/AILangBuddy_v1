"""Admin analytics: read-only aggregate queries over the evidence that already exists. Nothing is stored, nothing is rolled up, and no query returns a row
about one learner: every function returns counts, sums or per-content / per-topic figures. Takes an open connection.

Who counts as a learner: has the learner role, has no admin role, and is not the demo account. Every query restricts itself to that set.
Time: timestamps are UTC 'YYYY-MM-DD HH:MM:SS'; a window is [start, end) as such strings, a day is the UTC calendar date of the timestamp."""

LEARNERS = """(SELECT u.id FROM users u WHERE u.handle <> :demo
               AND EXISTS (SELECT 1 FROM user_roles ur JOIN roles r ON r.id = ur.role_id WHERE ur.user_id = u.id AND r.name = 'learner')
               AND NOT EXISTS (SELECT 1 FROM user_roles ur JOIN roles r ON r.id = ur.role_id WHERE ur.user_id = u.id AND r.name = 'admin'))"""

# One entry per kind of learning evidence. A learner is ACTIVE on a day if any of these has a row on that day. A login (sessions) is not evidence.
# Each carries its own window predicate so the time-window indexes of migration 0025 can be used.
# (timestamp column, extra condition). A speaking session counts once something was recorded: 'created' and 'cancelled' sessions are not attempts.
SOURCES = {
    "exercise_attempts": ("attempted_at", None),
    "situation_step_attempts": ("attempted_at", None),
    "listening_attempts": ("attempted_at", None),
    "speaking_sessions": ("created_at", "stage NOT IN ('created', 'cancelled')"),
    "pronunciation_assessments": ("created_at", None),
    "roleplay_turns": ("created_at", None),
    "ai_micro_lesson_attempts": ("attempted_at", None),
    "xp_events": ("earned_at", None),
}


def _windowed(table, column, extra):
    return f"SELECT user_id, {column} AS at FROM {table} WHERE {column} >= :start AND {column} < :end" + (f" AND {extra}" if extra else "")


ACTIVITY = {table: _windowed(table, column, extra) for table, (column, extra) in SOURCES.items()}


def per_user_activity(user_expr):
    """The same evidence for ONE learner (an SQL expression naming them), as a UNION ALL of timestamps: used for 'last active' and 'active days'."""
    return " UNION ALL ".join(f"SELECT {column} AS at FROM {table} WHERE user_id = {user_expr}" + (f" AND {extra}" if extra else "") for table, (column, extra) in SOURCES.items())


ACTIVITY_UNION = " UNION ALL ".join(ACTIVITY.values())


def _p(demo, start=None, end=None, **extra):
    return {"demo": demo, "start": start, "end": end, **extra}


# ---------- learners ----------
def total_learners(conn, demo):
    return conn.execute(f"SELECT COUNT(*) FROM users WHERE id IN {LEARNERS}", _p(demo)).fetchone()[0]


def new_learners(conn, demo, start, end):
    return conn.execute(f"SELECT COUNT(*) FROM users WHERE id IN {LEARNERS} AND created_at >= :start AND created_at < :end", _p(demo, start, end)).fetchone()[0]


def active_learners(conn, demo, start, end):
    return conn.execute(f"SELECT COUNT(DISTINCT user_id) FROM ({ACTIVITY_UNION}) WHERE user_id IN {LEARNERS}", _p(demo, start, end)).fetchone()[0]


def active_user_days(conn, demo, start, end):
    """[(user_id, 'YYYY-MM-DD')]: who was active on which UTC day. Used only to count distinct learners per day / week / month; never returned."""
    return [(r[0], r[1]) for r in conn.execute(
        f"SELECT DISTINCT user_id, substr(at, 1, 10) FROM ({ACTIVITY_UNION}) WHERE user_id IN {LEARNERS}", _p(demo, start, end))]


def kinds_of_activity(conn, demo, start, end):
    """{kind: learners with at least one row of that kind in the window}: which evidence the activity count rests on."""
    return {name: conn.execute(f"SELECT COUNT(DISTINCT user_id) FROM ({sql}) WHERE user_id IN {LEARNERS}", _p(demo, start, end)).fetchone()[0] for name, sql in ACTIVITY.items()}


def language_distribution(conn, demo):
    """[(code, name, learners)] by TARGET language; learners without a profile are the code 'none'."""
    rows = [(r[0], r[1], r[2]) for r in conn.execute(
        f"""SELECT l.code, l.name, COUNT(*) FROM learner_profiles p JOIN languages l ON l.id = p.target_language_id
            WHERE p.user_id IN {LEARNERS} GROUP BY l.code, l.name ORDER BY l.code""", _p(demo))]
    none = conn.execute(f"SELECT COUNT(*) FROM users u WHERE u.id IN {LEARNERS} AND NOT EXISTS (SELECT 1 FROM learner_profiles p WHERE p.user_id = u.id)", _p(demo)).fetchone()[0]
    return rows + ([("none", "No profile yet", none)] if none else [])


def cefr_distribution(conn, demo):
    return [(r[0], r[1], r[2]) for r in conn.execute(
        f"""SELECT c.code, c.label, COUNT(*) FROM learner_profiles p JOIN cefr_levels c ON c.code = p.cefr_level
            WHERE p.user_id IN {LEARNERS} GROUP BY c.code, c.label ORDER BY c.rank""", _p(demo))]


def age_group_distribution(conn, demo, today):
    """[(code, label, learners)]: the age BAND each learner falls in today (derived from the date of birth, which never leaves this query)."""
    age = "(CAST(strftime('%Y', :today) AS INTEGER) - CAST(strftime('%Y', p.date_of_birth) AS INTEGER) - (strftime('%m-%d', :today) < strftime('%m-%d', p.date_of_birth)))"
    return [(r[0], r[1], r[2]) for r in conn.execute(
        f"""SELECT g.code, g.label, COUNT(*) FROM learner_profiles p
            JOIN age_groups g ON g.min_age <= {age} AND (g.max_age IS NULL OR {age} <= g.max_age)
            WHERE p.user_id IN {LEARNERS} GROUP BY g.code, g.label ORDER BY g.min_age""", _p(demo, today=today))]


# ---------- learning ----------
def progress_cohort(conn, demo, table, fk, start, end):
    """(started, completed, learners, completed_learners): rows of lesson_progress / situation_progress that BEGAN in the window, how many of those are completed
    (by now), the distinct learners who started, and the distinct learners who completed."""
    row = conn.execute(
        f"""SELECT COUNT(*), COALESCE(SUM(completed_at IS NOT NULL), 0), COUNT(DISTINCT user_id), COUNT(DISTINCT CASE WHEN completed_at IS NOT NULL THEN user_id END) FROM {table}
            WHERE started_at >= :start AND started_at < :end AND user_id IN {LEARNERS}""", _p(demo, start, end)).fetchone()
    return row[0], row[1], row[2], row[3]


def attempt_accuracy(conn, demo, source, start, end):
    """(attempts, correct, learners) from the unified learner_attempts view (the same evidence the learner-facing features read)."""
    row = conn.execute(
        f"""SELECT COUNT(*), COALESCE(SUM(is_correct), 0), COUNT(DISTINCT user_id) FROM learner_attempts
            WHERE source = :source AND attempted_at >= :start AND attempted_at < :end AND user_id IN {LEARNERS}""", _p(demo, start, end, source=source)).fetchone()
    return row[0], row[1], row[2]


# ---------- speaking, pronunciation, roleplay ----------
def speaking_learners(conn, demo, start, end):
    row = conn.execute(f"SELECT COUNT(*), COUNT(DISTINCT user_id) FROM ({ACTIVITY['speaking_sessions']}) WHERE user_id IN {LEARNERS}", _p(demo, start, end)).fetchone()
    return row[0], row[1]


def pronunciation_usage(conn, demo, start, end):
    """(attempts, learners): assessments of any outcome. Usage only: no score is read."""
    row = conn.execute(f"SELECT COUNT(*), COUNT(DISTINCT user_id) FROM ({ACTIVITY['pronunciation_assessments']}) WHERE user_id IN {LEARNERS}", _p(demo, start, end)).fetchone()
    return row[0], row[1]


def roleplay(conn, demo, start, end):
    """{'started': (sessions, learners), 'completed': (sessions, learners), 'success': (sessions with no missed step, learners)}."""
    started = conn.execute(f"SELECT COUNT(*), COUNT(DISTINCT user_id) FROM roleplay_sessions WHERE created_at >= :start AND created_at < :end AND user_id IN {LEARNERS}", _p(demo, start, end)).fetchone()
    done = conn.execute(f"""SELECT COUNT(*), COUNT(DISTINCT user_id), COALESCE(SUM(steps_missed = 0), 0), COUNT(DISTINCT CASE WHEN steps_missed = 0 THEN user_id END)
                            FROM roleplay_sessions WHERE status = 'completed' AND completed_at >= :start AND completed_at < :end AND user_id IN {LEARNERS}""", _p(demo, start, end)).fetchone()
    return {"started": (started[0], started[1]), "completed": (done[0], done[1]), "success": (done[2], done[3])}


# ---------- confidence and weaknesses ----------
def confidence_vs_accuracy(conn, demo, start, end):
    """[(topic_slug, topic_name, learners, mean_confidence, mean_accuracy)]: per topic, for the learners who BOTH rated their confidence (latest self-report
    before the window ends) AND answered at least once on that topic in the window. Each learner counts once: mean_accuracy is the mean of
    per-learner accuracy (0-100), not attempts pooled, so a heavy practiser does not outweigh a light one."""
    return [tuple(r) for r in conn.execute(
        f"""WITH conf AS (
                SELECT c.user_id, c.topic_id, c.score FROM confidence_scores c
                WHERE c.source = 'self_report' AND c.topic_id IS NOT NULL AND c.recorded_at < :end AND c.user_id IN {LEARNERS}
                  AND c.id = (SELECT c2.id FROM confidence_scores c2 WHERE c2.user_id = c.user_id AND c2.topic_id = c.topic_id AND c2.source = 'self_report' AND c2.recorded_at < :end
                              ORDER BY c2.recorded_at DESC, c2.id DESC LIMIT 1)),
            acc AS (
                SELECT user_id, topic_id, 100.0 * SUM(is_correct) / COUNT(*) AS accuracy FROM learner_attempt_topics
                WHERE attempted_at >= :start AND attempted_at < :end GROUP BY user_id, topic_id)
            SELECT t.slug, t.name, COUNT(*), AVG(conf.score), AVG(acc.accuracy)
            FROM conf JOIN acc ON acc.user_id = conf.user_id AND acc.topic_id = conf.topic_id JOIN topics t ON t.id = conf.topic_id
            GROUP BY t.id ORDER BY t.slug""", _p(demo, start, end))]


def weaknesses_by_rule(conn, demo):
    """[(rule, active weaknesses, learners)] as of now."""
    return [tuple(r) for r in conn.execute(
        f"SELECT rule, COUNT(*), COUNT(DISTINCT user_id) FROM weaknesses WHERE status = 'active' AND user_id IN {LEARNERS} GROUP BY rule ORDER BY rule", _p(demo))]


def weaknesses_by_topic(conn, demo):
    """[(topic_slug, topic_name, active topic weaknesses, learners)] as of now."""
    return [tuple(r) for r in conn.execute(
        f"""SELECT t.slug, t.name, COUNT(*), COUNT(DISTINCT w.user_id) FROM weaknesses w JOIN topics t ON t.id = w.topic_id
            WHERE w.status = 'active' AND w.rule = 'low_topic_accuracy' AND w.user_id IN {LEARNERS} GROUP BY t.id ORDER BY t.slug""", _p(demo))]


# ---------- adaptive ----------
def recommendation_usage(conn, demo, start, end):
    """(shown, applied, learners, applied_learners): recommendations created in the window, those the learner applied (status 'applied'), the distinct learners shown any,
    and the distinct learners who applied any."""
    row = conn.execute(
        f"""SELECT COUNT(*), COALESCE(SUM(status = 'applied'), 0), COUNT(DISTINCT user_id), COUNT(DISTINCT CASE WHEN status = 'applied' THEN user_id END) FROM ai_recommendations
            WHERE created_at >= :start AND created_at < :end AND user_id IN {LEARNERS}""", _p(demo, start, end)).fetchone()
    return row[0], row[1], row[2], row[3]


def micro_lesson_usage(conn, demo, start, end):
    """{'generated': (lessons, learners), 'attempted': (lessons created in the window with at least one attempt, learners), 'attempts': (attempts, correct, learners)}."""
    generated = conn.execute(f"SELECT COUNT(*), COUNT(DISTINCT user_id) FROM ai_micro_lessons WHERE created_at >= :start AND created_at < :end AND user_id IN {LEARNERS}", _p(demo, start, end)).fetchone()
    attempted = conn.execute(
        f"""SELECT COUNT(*), COUNT(DISTINCT m.user_id) FROM ai_micro_lessons m WHERE m.created_at >= :start AND m.created_at < :end AND m.user_id IN {LEARNERS}
            AND EXISTS (SELECT 1 FROM ai_micro_lesson_attempts a WHERE a.micro_lesson_id = m.id)""", _p(demo, start, end)).fetchone()
    attempts = conn.execute(
        f"""SELECT COUNT(*), COALESCE(SUM(is_correct), 0), COUNT(DISTINCT user_id) FROM ai_micro_lesson_attempts
            WHERE attempted_at >= :start AND attempted_at < :end AND user_id IN {LEARNERS}""", _p(demo, start, end)).fetchone()
    return {"generated": (generated[0], generated[1]), "attempted": (attempted[0], attempted[1]), "attempts": (attempts[0], attempts[1], attempts[2])}


# ---------- engagement ----------
def xp_activity(conn, demo, start, end):
    """(events, xp awarded, learners who earned xp > 0)."""
    row = conn.execute(
        f"""SELECT COUNT(*), COALESCE(SUM(xp), 0), COUNT(DISTINCT CASE WHEN xp > 0 THEN user_id END) FROM xp_events
            WHERE earned_at >= :start AND earned_at < :end AND user_id IN {LEARNERS}""", _p(demo, start, end)).fetchone()
    return row[0], row[1], row[2]


def streak_activity(conn, demo, start_day, end_day):
    """(streak days, learners) for the UTC dates start_day..end_day inclusive."""
    row = conn.execute(f"SELECT COUNT(*), COUNT(DISTINCT user_id) FROM streak_days WHERE day >= :start AND day <= :end AND user_id IN {LEARNERS}", _p(demo, start_day, end_day)).fetchone()
    return row[0], row[1]


def achievements_unlocked(conn, demo, start, end):
    """[(code, title, unlocks, learners)] for unlocks in the window."""
    return [tuple(r) for r in conn.execute(
        f"""SELECT a.code, a.title, COUNT(*), COUNT(DISTINCT la.user_id) FROM learner_achievements la JOIN achievements a ON a.id = la.achievement_id
            WHERE la.unlocked_at >= :start AND la.unlocked_at < :end AND la.user_id IN {LEARNERS} GROUP BY a.id ORDER BY a.sort_order""", _p(demo, start, end))]


def _named_set(prefix, values):
    """(':p0, :p1', {'p0': v0, 'p1': v1}): an IN-list made of named parameters, so it can sit beside the named :demo / :start / :end."""
    names = {f"{prefix}{i}": v for i, v in enumerate(values)}
    return ", ".join(f":{k}" for k in names), names


def achievements_for(conn, demo, start, end, codes):
    """(unlocks, distinct learners) over a SET of achievements: the measure used when small buckets are folded together."""
    marks, names = _named_set("c", codes)
    row = conn.execute(
        f"""SELECT COUNT(*), COUNT(DISTINCT la.user_id) FROM learner_achievements la JOIN achievements a ON a.id = la.achievement_id
            WHERE la.unlocked_at >= :start AND la.unlocked_at < :end AND a.code IN ({marks}) AND la.user_id IN {LEARNERS}""", _p(demo, start, end, **names)).fetchone()
    return row[0], row[1]


def weaknesses_for_topics(conn, demo, slugs):
    """(active topic weaknesses, distinct learners) over a SET of topics: the measure used when small buckets are folded together."""
    marks, names = _named_set("t", slugs)
    row = conn.execute(
        f"""SELECT COUNT(*), COUNT(DISTINCT w.user_id) FROM weaknesses w JOIN topics t ON t.id = w.topic_id
            WHERE w.status = 'active' AND w.rule = 'low_topic_accuracy' AND t.slug IN ({marks}) AND w.user_id IN {LEARNERS}""", _p(demo, **names)).fetchone()
    return row[0], row[1]


def achievement_totals(conn, demo, start, end):
    row = conn.execute(f"SELECT COUNT(*), COUNT(DISTINCT user_id) FROM learner_achievements WHERE unlocked_at >= :start AND unlocked_at < :end AND user_id IN {LEARNERS}", _p(demo, start, end)).fetchone()
    return row[0], row[1]


def challenge_activity(conn, demo, start_day, end_day):
    """(challenges that began in the window, of those claimed, learners): period_start is a date."""
    row = conn.execute(
        f"""SELECT COUNT(*), COALESCE(SUM(claimed_at IS NOT NULL), 0), COUNT(DISTINCT user_id) FROM learner_challenges
            WHERE period_start >= :start AND period_start <= :end AND user_id IN {LEARNERS}""", _p(demo, start_day, end_day)).fetchone()
    return row[0], row[1], row[2]


# ---------- content performance ----------
UNIT = {
    "lesson": ("lessons", "lesson", "lesson_progress", "lesson_id"),
    "situation": ("situations", "situation", "situation_progress", "situation_id"),
    "listening": ("listening_activities", "listening", None, None),
}


def content_performance(conn, demo, kind, start, end):
    """[(id, slug, title, status, attempts, correct, learners, started, completed)] for the units of `kind` that learners answered in the window
    (any status: an archived unit that was used is still reported). Per unit, never per learner."""
    table, source, progress, fk = UNIT[kind]
    rows = conn.execute(
        f"""SELECT u.id, u.slug, u.title, u.status, COUNT(*) AS attempts, SUM(a.is_correct) AS correct, COUNT(DISTINCT a.user_id) AS learners
            FROM learner_attempts a JOIN {table} u ON u.id = a.unit_id
            WHERE a.source = :source AND a.attempted_at >= :start AND a.attempted_at < :end AND a.user_id IN {LEARNERS} GROUP BY u.id ORDER BY u.id""",
        _p(demo, start, end, source=source)).fetchall()
    out = []
    for r in rows:
        started = completed = 0
        if progress:
            p = conn.execute(f"SELECT COUNT(*), COALESCE(SUM(completed_at IS NOT NULL), 0) FROM {progress} WHERE {fk} = :unit AND started_at >= :start AND started_at < :end AND user_id IN {LEARNERS}",
                             _p(demo, start, end, unit=r["id"])).fetchone()
            started, completed = p[0], p[1]
        out.append((r["id"], r["slug"], r["title"], r["status"], r["attempts"], r["correct"], r["learners"], started, completed))
    return out
