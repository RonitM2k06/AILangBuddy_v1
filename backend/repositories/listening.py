"""Listening activities, options and the learner's attempts. Takes an open connection; every attempt/progress
function is scoped by user_id."""
from . import age

_COLUMNS = """a.id, a.slug, a.title, a.mode, a.prompt, a.difficulty, a.cefr_code, a.item_id,
              t.slug AS topic_slug, t.name AS topic_name, t.icon AS topic_icon"""


def _marks(ids):
    return ",".join("?" * len(ids))


def list_available(conn, language_id, max_rank, age_group_id):
    """Published activities in the target language at or below the learner's level, easiest level first."""
    return [dict(r) for r in conn.execute(
        f"""SELECT {_COLUMNS} FROM listening_activities a JOIN topics t ON t.id = a.topic_id JOIN cefr_levels c ON c.code = a.cefr_code
            WHERE a.language_id = ? AND a.status = 'published' AND c.rank <= ? AND {age.listening()}
            ORDER BY c.rank, a.sort_order""",
        (language_id, max_rank, age_group_id)).fetchall()]


def get_available(conn, activity_id, language_id, max_rank, age_group_id):
    row = conn.execute(
        f"""SELECT {_COLUMNS} FROM listening_activities a JOIN topics t ON t.id = a.topic_id JOIN cefr_levels c ON c.code = a.cefr_code
            WHERE a.id = ? AND a.language_id = ? AND a.status = 'published' AND c.rank <= ? AND {age.listening()}""",
        (activity_id, language_id, max_rank, age_group_id)).fetchone()
    return dict(row) if row else None


def options_for(conn, activity_id):
    """Option ids and the items they stand for, in display order. The caller must not mark which one is correct."""
    return [dict(r) for r in conn.execute(
        "SELECT id, item_id FROM listening_options WHERE activity_id = ? ORDER BY sort_order", (activity_id,)).fetchall()]


def option_item(conn, option_id, activity_id):
    """The item an option stands for, only if the option belongs to this activity (server-side, for grading)."""
    row = conn.execute("SELECT item_id FROM listening_options WHERE id = ? AND activity_id = ?", (option_id, activity_id)).fetchone()
    return row["item_id"] if row else None


def correct_option_id(conn, activity_id, activity_item_id):
    """The option whose item is the activity's item (the correct one)."""
    row = conn.execute("SELECT id FROM listening_options WHERE activity_id = ? AND item_id = ?", (activity_id, activity_item_id)).fetchone()
    return row["id"] if row else None


# ---------- attempts ----------
def insert_session(conn, user_id, language_id, started_at, ended_at, duration_ms):
    cur = conn.execute(
        """INSERT INTO audio_sessions(user_id, language_id, kind, status, started_at, ended_at, duration_ms)
           VALUES (?, ?, 'listening', 'completed', ?, ?, ?)""",
        (user_id, language_id, started_at, ended_at, duration_ms))
    return cur.lastrowid


def insert_attempt(conn, user_id, session_id, activity_id, option_id, is_correct, plays, attempted_at):
    cur = conn.execute(
        """INSERT INTO listening_attempts(user_id, session_id, activity_id, option_id, is_correct, plays, attempted_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (user_id, session_id, activity_id, option_id, 1 if is_correct else 0, plays, attempted_at))
    return cur.lastrowid


def list_attempts(conn, user_id, language_id, limit):
    return [dict(r) for r in conn.execute(
        """SELECT la.id, la.option_id, la.is_correct, la.plays, la.attempted_at, s.duration_ms,
                  a.id AS activity_id, a.title, a.mode
           FROM listening_attempts la JOIN listening_activities a ON a.id = la.activity_id JOIN audio_sessions s ON s.id = la.session_id
           WHERE la.user_id = ? AND a.language_id = ? ORDER BY la.attempted_at DESC, la.id DESC LIMIT ?""",
        (user_id, language_id, limit)).fetchall()]


def activity_stats(conn, user_id, activity_ids):
    """{activity_id: {attempts, correct, last_attempt_at}} for this learner (only activities they have attempted)."""
    if not activity_ids:
        return {}
    rows = conn.execute(
        f"""SELECT activity_id, COUNT(*) AS attempts, SUM(is_correct) AS correct, MAX(attempted_at) AS last_at
            FROM listening_attempts WHERE user_id = ? AND activity_id IN ({_marks(activity_ids)}) GROUP BY activity_id""",
        [user_id, *activity_ids]).fetchall()
    return {r["activity_id"]: {"attempts": r["attempts"], "correct": r["correct"], "last_attempt_at": r["last_at"]} for r in rows}
