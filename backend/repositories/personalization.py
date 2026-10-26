"""Confidence, weaknesses, attempt statistics and daily tasks. Takes an open connection; every learner-data
function is scoped by user_id (and the learner's target language)."""
from . import age


def _marks(ids):
    return ",".join("?" * len(ids))


# ---------- dimensions ----------
def get_topic(conn, slug):
    row = conn.execute("SELECT id, slug, name, icon FROM topics WHERE slug = ?", (slug,)).fetchone()
    return dict(row) if row else None


def get_skill(conn, code):
    row = conn.execute("SELECT id, code, name FROM skills WHERE code = ?", (code,)).fetchone()
    return dict(row) if row else None


def list_skills(conn):
    return [dict(r) for r in conn.execute("SELECT id, code, name FROM skills ORDER BY id").fetchall()]


def topics_with_content(conn, language_id, max_rank, age_group_id):
    """Topics that have at least one published lesson or situation available to the learner."""
    rows = conn.execute(
        f"""SELECT t.id, t.slug, t.name, t.icon FROM topics t
           WHERE EXISTS (SELECT 1 FROM lesson_topics lt JOIN lessons l ON l.id = lt.lesson_id JOIN cefr_levels c ON c.code = l.cefr_code
                         WHERE lt.topic_id = t.id AND l.language_id = ? AND l.status = 'published' AND c.rank <= ? AND {age.lesson()})
              OR EXISTS (SELECT 1 FROM situations s JOIN cefr_levels c ON c.code = s.cefr_code
                         WHERE s.topic_id = t.id AND s.language_id = ? AND s.status = 'published' AND c.rank <= ? AND {age.situation()})
           ORDER BY t.id""",
        (language_id, max_rank, age_group_id, language_id, max_rank, age_group_id),
    ).fetchall()
    return [dict(r) for r in rows]


# ---------- confidence ----------
def insert_confidence(conn, user_id, language_id, topic_id, skill_id, score, source, lesson_id, situation_id, recorded_at):
    cur = conn.execute(
        """INSERT INTO confidence_scores(user_id, language_id, topic_id, skill_id, score, source, lesson_id, situation_id, recorded_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (user_id, language_id, topic_id, skill_id, score, source, lesson_id, situation_id, recorded_at),
    )
    return cur.lastrowid


def get_confidence(conn, user_id, confidence_id):
    row = conn.execute(
        """SELECT c.id, c.score, c.source, c.lesson_id, c.situation_id, c.recorded_at, t.slug AS topic_slug, t.name AS topic_name,
                  t.icon AS topic_icon, s.code AS skill_code, s.name AS skill_name
           FROM confidence_scores c LEFT JOIN topics t ON t.id = c.topic_id LEFT JOIN skills s ON s.id = c.skill_id
           WHERE c.id = ? AND c.user_id = ?""",
        (confidence_id, user_id),
    ).fetchone()
    return dict(row) if row else None


def latest_confidence(conn, user_id, language_id, column):
    """{topic_id|skill_id: {score, source, recorded_at}}: the most recent self-report per dimension."""
    assert column in ("topic_id", "skill_id")
    rows = conn.execute(
        f"""SELECT c.{column} AS dim, c.score, c.source, c.recorded_at FROM confidence_scores c
            WHERE c.user_id = ? AND c.language_id = ? AND c.{column} IS NOT NULL
              AND c.id = (SELECT c2.id FROM confidence_scores c2 WHERE c2.user_id = c.user_id AND c2.language_id = c.language_id
                          AND c2.{column} = c.{column} ORDER BY c2.recorded_at DESC, c2.id DESC LIMIT 1)""",
        (user_id, language_id),
    ).fetchall()
    return {r["dim"]: {"score": r["score"], "source": r["source"], "recorded_at": r["recorded_at"]} for r in rows}


def confidence_history(conn, user_id, language_id, topic_id, skill_id, limit):
    where, args = "", []
    if topic_id is not None:
        where, args = " AND c.topic_id = ?", [topic_id]
    elif skill_id is not None:
        where, args = " AND c.skill_id = ?", [skill_id]
    rows = conn.execute(
        f"""SELECT c.id, c.score, c.source, c.lesson_id, c.situation_id, c.recorded_at, t.slug AS topic_slug, t.name AS topic_name,
                   t.icon AS topic_icon, s.code AS skill_code, s.name AS skill_name
            FROM confidence_scores c LEFT JOIN topics t ON t.id = c.topic_id LEFT JOIN skills s ON s.id = c.skill_id
            WHERE c.user_id = ? AND c.language_id = ?{where} ORDER BY c.recorded_at DESC, c.id DESC LIMIT ?""",
        [user_id, language_id, *args, limit],
    ).fetchall()
    return [dict(r) for r in rows]


# ---------- performance (from attempts) ----------
def recent_topic_window(conn, user_id, language_id, window):
    """{topic_id: {attempts, incorrect, last_at}} over each topic's most recent `window` graded attempts."""
    rows = conn.execute(
        """SELECT topic_id, COUNT(*) AS attempts, SUM(1 - is_correct) AS incorrect, MAX(attempted_at) AS last_at FROM (
               SELECT topic_id, is_correct, attempted_at,
                      ROW_NUMBER() OVER (PARTITION BY topic_id ORDER BY attempted_at DESC, source, attempt_id DESC) AS rn
               FROM learner_attempt_topics WHERE user_id = ? AND language_id = ?)
           WHERE rn <= ? GROUP BY topic_id""",
        (user_id, language_id, window),
    ).fetchall()
    return {r["topic_id"]: {"attempts": r["attempts"], "incorrect": r["incorrect"], "last_at": r["last_at"]} for r in rows}


def item_stats(conn, user_id, language_id):
    """Per vocabulary item: attempts, incorrect, time of the last attempt, and whether that last attempt was correct."""
    rows = conn.execute(
        """SELECT a.item_id, COUNT(*) AS attempts, SUM(1 - a.is_correct) AS incorrect, MAX(a.attempted_at) AS last_at,
                  (SELECT b.is_correct FROM learner_attempts b WHERE b.user_id = a.user_id AND b.language_id = a.language_id
                     AND b.item_id = a.item_id ORDER BY b.attempted_at DESC, b.source, b.attempt_id DESC LIMIT 1) AS last_correct
           FROM learner_attempts a WHERE a.user_id = ? AND a.language_id = ? AND a.item_id IS NOT NULL GROUP BY a.item_id""",
        (user_id, language_id),
    ).fetchall()
    return [dict(r) for r in rows]


def recent_lesson_attempts(conn, user_id, language_id, limit):
    """The learner's most recent graded lesson-exercise attempts with the exercise difficulty."""
    return [dict(r) for r in conn.execute(
        """SELECT is_correct, difficulty, attempted_at FROM learner_attempts
           WHERE user_id = ? AND language_id = ? AND source = 'lesson'
           ORDER BY attempted_at DESC, attempt_id DESC LIMIT ?""",
        (user_id, language_id, limit)).fetchall()]


# ---------- weaknesses ----------
def active_weaknesses(conn, user_id, language_id):
    rows = conn.execute(
        """SELECT w.id, w.rule, w.severity, w.attempts, w.incorrect, w.last_evidence_at, w.detected_at, w.item_id,
                  t.slug AS topic_slug, t.name AS topic_name, t.icon AS topic_icon, t.id AS topic_id
           FROM weaknesses w LEFT JOIN topics t ON t.id = w.topic_id
           WHERE w.user_id = ? AND w.language_id = ? AND w.status = 'active'
           ORDER BY CASE w.severity WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END, w.rule, w.id""",
        (user_id, language_id),
    ).fetchall()
    return [dict(r) for r in rows]


def upsert_weakness(conn, user_id, language_id, rule, topic_id, item_id, severity, attempts, incorrect, last_evidence_at, now):
    """Insert a weakness, or refresh (and reactivate) the existing one for the same subject."""
    target = "(user_id, language_id, topic_id) WHERE topic_id IS NOT NULL" if topic_id is not None else "(user_id, language_id, item_id) WHERE item_id IS NOT NULL"
    conn.execute(
        f"""INSERT INTO weaknesses(user_id, language_id, rule, topic_id, item_id, severity, attempts, incorrect, last_evidence_at, detected_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT{target} DO UPDATE SET severity = excluded.severity, attempts = excluded.attempts, incorrect = excluded.incorrect,
                last_evidence_at = excluded.last_evidence_at,
                detected_at = CASE WHEN weaknesses.status = 'resolved' THEN excluded.detected_at ELSE weaknesses.detected_at END,
                status = 'active', resolved_at = NULL""",
        (user_id, language_id, rule, topic_id, item_id, severity, attempts, incorrect, last_evidence_at, now),
    )


def resolve_weaknesses_except(conn, user_id, language_id, keep_topic_ids, keep_item_ids, now):
    """Mark active weaknesses that no longer hold as resolved. (An empty keep-list must not become `NOT IN (NULL)`,
    which is never true, so each condition is only added when there is something to keep.)"""
    topic_cond = f"topic_id NOT IN ({_marks(keep_topic_ids)})" if keep_topic_ids else "1"
    item_cond = f"item_id NOT IN ({_marks(keep_item_ids)})" if keep_item_ids else "1"
    conn.execute(
        f"""UPDATE weaknesses SET status = 'resolved', resolved_at = ?
            WHERE user_id = ? AND language_id = ? AND status = 'active'
              AND (topic_id IS NULL OR {topic_cond}) AND (item_id IS NULL OR {item_cond})""",
        [now, user_id, language_id, *keep_topic_ids, *keep_item_ids],
    )


# ---------- recommendation inputs ----------
def lessons_containing_item(conn, item_id, language_id, max_rank, age_group_id):
    """Available lessons that teach or test a vocabulary item, easiest first."""
    return [r[0] for r in conn.execute(
        f"""SELECT l.id FROM lessons l JOIN cefr_levels c ON c.code = l.cefr_code
           WHERE l.language_id = ? AND l.status = 'published' AND c.rank <= ? AND {age.lesson()}
             AND (EXISTS (SELECT 1 FROM lesson_vocabulary lv WHERE lv.lesson_id = l.id AND lv.item_id = ?)
               OR EXISTS (SELECT 1 FROM exercises e WHERE e.lesson_id = l.id AND e.item_id = ?))
           ORDER BY c.rank, l.sort_order""",
        (language_id, max_rank, age_group_id, item_id, item_id)).fetchall()]


def situation_topics(conn, situation_ids):
    if not situation_ids:
        return {}
    rows = conn.execute(f"SELECT id, topic_id FROM situations WHERE id IN ({_marks(situation_ids)})", situation_ids).fetchall()
    return {r["id"]: r["topic_id"] for r in rows}


# ---------- daily plan ----------
_TASK_COLUMNS = """d.id, d.plan_date, d.priority, d.task_type, d.source, d.lesson_id, d.situation_id, d.topic_id, d.status, d.created_at, d.completed_at"""


def list_tasks(conn, user_id, language_id, plan_date):
    return [dict(r) for r in conn.execute(
        f"SELECT {_TASK_COLUMNS} FROM daily_tasks d WHERE d.user_id = ? AND d.language_id = ? AND d.plan_date = ? ORDER BY d.priority",
        (user_id, language_id, plan_date)).fetchall()]


def insert_task(conn, user_id, language_id, plan_date, priority, task_type, source, lesson_id, situation_id, topic_id, created_at):
    """INSERT OR IGNORE: the unique indexes make a repeated generation a no-op instead of a duplicate."""
    cur = conn.execute(
        """INSERT OR IGNORE INTO daily_tasks(user_id, language_id, plan_date, priority, task_type, source, lesson_id, situation_id, topic_id, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (user_id, language_id, plan_date, priority, task_type, source, lesson_id, situation_id, topic_id, created_at))
    return cur.rowcount == 1


def get_task(conn, user_id, task_id):
    row = conn.execute(f"SELECT {_TASK_COLUMNS}, d.language_id FROM daily_tasks d WHERE d.id = ? AND d.user_id = ?", (task_id, user_id)).fetchone()
    return dict(row) if row else None


def set_task_status(conn, user_id, task_id, status, completed_at):
    conn.execute("UPDATE daily_tasks SET status = ?, completed_at = ? WHERE id = ? AND user_id = ?", (status, completed_at, task_id, user_id))


def auto_complete_tasks(conn, user_id, language_id, plan_date):
    """Mark pending tasks done when the learner already did what they ask for on or after the plan date."""
    conn.execute(
        """UPDATE daily_tasks SET status = 'done', completed_at = (SELECT p.completed_at FROM lesson_progress p
                                                                     WHERE p.user_id = daily_tasks.user_id AND p.lesson_id = daily_tasks.lesson_id)
           WHERE user_id = ? AND language_id = ? AND plan_date = ? AND status = 'pending' AND task_type = 'study_lesson'
             AND EXISTS (SELECT 1 FROM lesson_progress p WHERE p.user_id = daily_tasks.user_id AND p.lesson_id = daily_tasks.lesson_id
                         AND p.completed_at IS NOT NULL AND p.completed_at >= ?)""",
        (user_id, language_id, plan_date, plan_date))
    conn.execute(
        """UPDATE daily_tasks SET status = 'done', completed_at = (SELECT p.completed_at FROM situation_progress p
                                                                     WHERE p.user_id = daily_tasks.user_id AND p.situation_id = daily_tasks.situation_id)
           WHERE user_id = ? AND language_id = ? AND plan_date = ? AND status = 'pending' AND task_type = 'practice_situation'
             AND EXISTS (SELECT 1 FROM situation_progress p WHERE p.user_id = daily_tasks.user_id AND p.situation_id = daily_tasks.situation_id
                         AND p.completed_at IS NOT NULL AND p.completed_at >= ?)""",
        (user_id, language_id, plan_date, plan_date))
    conn.execute(
        """UPDATE daily_tasks SET status = 'done', completed_at = (SELECT MIN(c.recorded_at) FROM confidence_scores c
                                                                     WHERE c.user_id = daily_tasks.user_id AND c.topic_id = daily_tasks.topic_id AND c.recorded_at >= ?)
           WHERE user_id = ? AND language_id = ? AND plan_date = ? AND status = 'pending' AND task_type = 'confidence_checkin'
             AND EXISTS (SELECT 1 FROM confidence_scores c WHERE c.user_id = daily_tasks.user_id AND c.topic_id = daily_tasks.topic_id AND c.recorded_at >= ?)""",
        (plan_date, user_id, language_id, plan_date, plan_date))


# ---------- display helpers ----------
def lesson_titles(conn, ids):
    if not ids:
        return {}
    return {r["id"]: r["title"] for r in conn.execute(f"SELECT id, title FROM lessons WHERE id IN ({_marks(ids)})", ids)}


def situation_titles(conn, ids):
    if not ids:
        return {}
    return {r["id"]: r["title"] for r in conn.execute(f"SELECT id, title FROM situations WHERE id IN ({_marks(ids)})", ids)}


def topics_by_ids(conn, ids):
    if not ids:
        return {}
    return {r["id"]: dict(r) for r in conn.execute(f"SELECT id, slug, name, icon FROM topics WHERE id IN ({_marks(ids)})", ids)}
