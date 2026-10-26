"""XP ledger, streak days and freezes, achievements and challenges. Takes an open connection; every learner-data function is
scoped by user_id."""


# ---------- settings ----------
def get_settings(conn, user_id):
    row = conn.execute("SELECT timezone, friend_code FROM learner_gamification WHERE user_id = ?", (user_id,)).fetchone()
    return dict(row) if row else None


def create_settings(conn, user_id, now):
    conn.execute("INSERT OR IGNORE INTO learner_gamification(user_id, created_at) VALUES (?, ?)", (user_id, now))


def set_timezone(conn, user_id, timezone):
    conn.execute("UPDATE learner_gamification SET timezone = ? WHERE user_id = ?", (timezone, user_id))


def set_friend_code(conn, user_id, code):
    conn.execute("UPDATE learner_gamification SET friend_code = ? WHERE user_id = ?", (code, user_id))


# ---------- the things a learner has already done (read-only, from the existing tables) ----------
def _not_credited(kind, alias_user, alias_source):
    return (f"NOT EXISTS (SELECT 1 FROM xp_events x WHERE x.user_id = {alias_user} AND x.kind = '{kind}' AND x.source_id = {alias_source})")


def uncredited_sources(conn, user_id):
    """Everything the learner did that has no XP event yet: [{kind, source_id, earned_at}]."""
    q = {
        "exercise": f"""SELECT 'exercise' AS kind, ea.exercise_id AS source_id, MIN(ea.attempted_at) AS earned_at FROM exercise_attempts ea
                        WHERE ea.user_id = ? AND ea.is_correct = 1 AND {_not_credited('exercise', 'ea.user_id', 'ea.exercise_id')} GROUP BY ea.exercise_id""",
        "lesson": f"""SELECT 'lesson' AS kind, p.lesson_id AS source_id, p.completed_at AS earned_at FROM lesson_progress p
                      WHERE p.user_id = ? AND p.completed_at IS NOT NULL AND {_not_credited('lesson', 'p.user_id', 'p.lesson_id')}""",
        "situation": f"""SELECT 'situation' AS kind, p.situation_id AS source_id, p.completed_at AS earned_at FROM situation_progress p
                         WHERE p.user_id = ? AND p.completed_at IS NOT NULL AND {_not_credited('situation', 'p.user_id', 'p.situation_id')}""",
        "listening": f"""SELECT 'listening' AS kind, la.activity_id AS source_id, MIN(la.attempted_at) AS earned_at FROM listening_attempts la
                         WHERE la.user_id = ? AND la.is_correct = 1 AND {_not_credited('listening', 'la.user_id', 'la.activity_id')} GROUP BY la.activity_id""",
        "speaking": f"""SELECT 'speaking' AS kind, ss.item_id AS source_id, MIN(ss.updated_at) AS earned_at FROM speaking_sessions ss
                        WHERE ss.user_id = ? AND ss.stage = 'completed' AND {_not_credited('speaking', 'ss.user_id', 'ss.item_id')} GROUP BY ss.item_id""",
        # a finished roleplay of a situation (Phase 11) is practice of that situation: it is credited as that situation, once, and only when
        # at least half of its steps were answered correctly, so failing on purpose to "finish" earns nothing. A step accepted only by an external
        # (model) grader does not count toward that half (Phase 12): a model never decides a reward.
        "roleplay": f"""SELECT 'situation' AS kind, rp.situation_id AS source_id, rp.completed_at AS earned_at FROM roleplay_sessions rp
                        WHERE rp.user_id = ? AND rp.status = 'completed'
                          AND (rp.steps_correct - (SELECT COUNT(*) FROM roleplay_turns t JOIN roleplay_turn_grades g ON g.turn_id = t.id
                                                   WHERE t.session_id = rp.id AND t.user_id = rp.user_id AND t.resolved = 'correct' AND g.method = 'semantic_llm')) * 2 >= rp.steps_total
                          AND {_not_credited('situation', 'rp.user_id', 'rp.situation_id')}""",
        # a daily task counts only if what it asked for is verifiably done: setting the status alone earns nothing
        "daily_task": f"""SELECT 'daily_task' AS kind, dt.id AS source_id, dt.completed_at AS earned_at FROM daily_tasks dt
                          WHERE dt.user_id = ? AND dt.status = 'done' AND dt.completed_at IS NOT NULL AND {_not_credited('daily_task', 'dt.user_id', 'dt.id')}
                            AND ((dt.task_type = 'study_lesson' AND EXISTS (SELECT 1 FROM lesson_progress p WHERE p.user_id = dt.user_id AND p.lesson_id = dt.lesson_id AND p.completed_at IS NOT NULL))
                              OR (dt.task_type = 'practice_situation' AND EXISTS (SELECT 1 FROM situation_progress p WHERE p.user_id = dt.user_id AND p.situation_id = dt.situation_id AND p.completed_at IS NOT NULL))
                              OR (dt.task_type = 'confidence_checkin' AND EXISTS (SELECT 1 FROM confidence_scores c WHERE c.user_id = dt.user_id AND c.topic_id = dt.topic_id AND c.recorded_at >= dt.plan_date)))""",
    }
    out = []
    for sql in q.values():
        out += [dict(r) for r in conn.execute(sql, (user_id,)).fetchall()]
    return out


# ---------- xp ledger ----------
def activity_xp_on(conn, user_id, day):
    return conn.execute("SELECT COALESCE(SUM(xp), 0) FROM xp_events WHERE user_id = ? AND day = ? AND kind <> 'challenge'", (user_id, day)).fetchone()[0]


def insert_event(conn, user_id, kind, source_id, xp, earned_at, day, now):
    """Credits one thing, once. Returns False when it was already credited (the UNIQUE row refuses a second reward)."""
    return conn.execute("INSERT OR IGNORE INTO xp_events(user_id, kind, source_id, xp, earned_at, day, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (user_id, kind, source_id, xp, earned_at, day, now)).rowcount == 1


def total_xp(conn, user_id):
    return conn.execute("SELECT COALESCE(SUM(xp), 0) FROM xp_events WHERE user_id = ?", (user_id,)).fetchone()[0]


def xp_between(conn, user_id, start, end):
    return conn.execute("SELECT COALESCE(SUM(xp), 0) FROM xp_events WHERE user_id = ? AND day BETWEEN ? AND ? AND kind <> 'challenge'", (user_id, start, end)).fetchone()[0]


def count_between(conn, user_id, kind, start, end):
    return conn.execute("SELECT COUNT(*) FROM xp_events WHERE user_id = ? AND kind = ? AND day BETWEEN ? AND ?", (user_id, kind, start, end)).fetchone()[0]


def count_kind(conn, user_id, kind):
    return conn.execute("SELECT COUNT(*) FROM xp_events WHERE user_id = ? AND kind = ?", (user_id, kind)).fetchone()[0]


def xp_since(conn, user_id, start_day):
    """XP (everything, challenge rewards included) on or after a day, for the leaderboard."""
    return conn.execute("SELECT COALESCE(SUM(xp), 0) FROM xp_events WHERE user_id = ? AND day >= ?", (user_id, start_day)).fetchone()[0]


def recent_events(conn, user_id, limit):
    return [dict(r) for r in conn.execute("SELECT kind, xp, day FROM xp_events WHERE user_id = ? ORDER BY earned_at DESC, id DESC LIMIT ?", (user_id, limit)).fetchall()]


# ---------- streak days and freezes ----------
def record_days(conn, user_id):
    conn.execute("INSERT OR IGNORE INTO streak_days(user_id, day) SELECT ?, day FROM xp_events WHERE user_id = ? AND kind <> 'challenge' GROUP BY day", (user_id, user_id))


def list_days(conn, user_id):
    return [r[0] for r in conn.execute("SELECT day FROM streak_days WHERE user_id = ? ORDER BY day", (user_id,)).fetchall()]


def freeze_days(conn, user_id, kind):
    return [r[0] for r in conn.execute("SELECT day FROM streak_freezes WHERE user_id = ? AND kind = ? ORDER BY day", (user_id, kind)).fetchall()]


def add_freeze(conn, user_id, kind, day, now):
    return conn.execute("INSERT OR IGNORE INTO streak_freezes(user_id, kind, day, created_at) VALUES (?, ?, ?, ?)", (user_id, kind, day, now)).rowcount == 1


def freeze_log(conn, user_id, limit):
    return [dict(r) for r in conn.execute("SELECT kind, day FROM streak_freezes WHERE user_id = ? ORDER BY day DESC, id DESC LIMIT ?", (user_id, limit)).fetchall()]


# ---------- achievements ----------
def list_achievements(conn, user_id):
    return [dict(r) for r in conn.execute(
        """SELECT a.id, a.code, a.title, a.description, a.metric, a.threshold, la.unlocked_at FROM achievements a
           LEFT JOIN learner_achievements la ON la.achievement_id = a.id AND la.user_id = ? ORDER BY a.sort_order""", (user_id,)).fetchall()]


def unlock(conn, user_id, achievement_id, now):
    return conn.execute("INSERT OR IGNORE INTO learner_achievements(user_id, achievement_id, unlocked_at) VALUES (?, ?, ?)", (user_id, achievement_id, now)).rowcount == 1


# ---------- challenges ----------
def active_challenges(conn):
    return [dict(r) for r in conn.execute("SELECT id, code, title, period, metric, target, reward_xp FROM challenges WHERE active = 1 ORDER BY sort_order").fetchall()]


def ensure_instance(conn, user_id, challenge_id, start, end):
    conn.execute("INSERT OR IGNORE INTO learner_challenges(user_id, challenge_id, period_start, period_end) VALUES (?, ?, ?, ?)", (user_id, challenge_id, start, end))


_INSTANCE = """SELECT lc.id, lc.period_start, lc.period_end, lc.claimed_at, c.code, c.title, c.period, c.metric, c.target, c.reward_xp
               FROM learner_challenges lc JOIN challenges c ON c.id = lc.challenge_id"""


def current_instances(conn, user_id, day):
    return [dict(r) for r in conn.execute(f"{_INSTANCE} WHERE lc.user_id = ? AND lc.period_start <= ? AND lc.period_end >= ? AND c.active = 1 ORDER BY c.sort_order", (user_id, day, day)).fetchall()]


def get_instance(conn, user_id, instance_id):
    row = conn.execute(f"{_INSTANCE} WHERE lc.user_id = ? AND lc.id = ?", (user_id, instance_id)).fetchone()
    return dict(row) if row else None


def mark_claimed(conn, user_id, instance_id, now):
    """Guarded: only an unclaimed instance of this learner. Returns True if this call claimed it."""
    return conn.execute("UPDATE learner_challenges SET claimed_at = ? WHERE id = ? AND user_id = ? AND claimed_at IS NULL", (now, instance_id, user_id)).rowcount == 1


def count_claimed(conn, user_id):
    return conn.execute("SELECT COUNT(*) FROM learner_challenges WHERE user_id = ? AND claimed_at IS NOT NULL", (user_id,)).fetchone()[0]
