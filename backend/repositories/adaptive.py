"""Adaptive AI persistence: recommendations, insights, micro-lessons (and their options and attempts), the evidence behind them, the audit
events and roleplay grades. Takes an open connection; every function is scoped by user_id, so another learner's rows are simply not found."""

_OWNER = {"recommendation": "recommendation_id", "insight": "insight_id", "micro_lesson": "micro_lesson_id"}


# ---------- evidence ----------
def insert_evidence(conn, user_id, owner, owner_id, items):
    column = _OWNER[owner]
    for i, (kind, text) in enumerate(items[:8], start=1):
        conn.execute(f"INSERT INTO ai_evidence(user_id, {column}, ord, kind, text) VALUES (?, ?, ?, ?, ?)", (user_id, owner_id, i, kind, text[:300]))


def evidence_for(conn, user_id, owner, owner_id):
    column = _OWNER[owner]
    return [dict(r) for r in conn.execute(f"SELECT kind, text FROM ai_evidence WHERE user_id = ? AND {column} = ? ORDER BY ord", (user_id, owner_id)).fetchall()]


# ---------- recommendations ----------
_REC = "SELECT id, plan_date, kind, target_type, target_id, title, reason, note, rank, source, mode, status, created_at, applied_at FROM ai_recommendations"


def find_recommendation(conn, user_id, plan_date, kind, target_type, target_id):
    row = conn.execute(f"{_REC} WHERE user_id = ? AND plan_date = ? AND kind = ? AND target_type = ? AND target_id = ?",
                       (user_id, plan_date, kind, target_type, target_id)).fetchone()
    return dict(row) if row else None


def insert_recommendation(conn, user_id, language_id, plan_date, c, rank, source, mode, now):
    cur = conn.execute(
        """INSERT INTO ai_recommendations(user_id, language_id, plan_date, kind, target_type, target_id, title, reason, note, rank, source, mode, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (user_id, language_id, plan_date, c["kind"], c["target_type"], c["target_id"], c["title"][:120], c["reason"][:300], c.get("note"), rank, source, mode, now))
    return cur.lastrowid


def update_active_ranking(conn, user_id, rec_id, rank, note, source, reason, title):
    """Re-ranks a recommendation that is still active (applied ones keep what the learner acted on)."""
    conn.execute("UPDATE ai_recommendations SET rank = ?, note = ?, source = ?, reason = ?, title = ? WHERE id = ? AND user_id = ? AND status = 'active'",
                 (rank, note, source, reason[:300], title[:120], rec_id, user_id))


def list_recommendations(conn, user_id, plan_date, statuses=("active", "applied")):
    marks = ",".join("?" * len(statuses))
    return [dict(r) for r in conn.execute(f"{_REC} WHERE user_id = ? AND plan_date = ? AND status IN ({marks}) ORDER BY rank, id", (user_id, plan_date, *statuses)).fetchall()]


def top_active_recommendation(conn, user_id, plan_date):
    """The learner's best stored suggestion for today, if there is one (the tutor may quote it; it is evidence-backed and stored)."""
    row = conn.execute(f"{_REC} WHERE user_id = ? AND plan_date = ? AND status = 'active' ORDER BY rank, id LIMIT 1", (user_id, plan_date)).fetchone()
    return dict(row) if row else None


def get_recommendation(conn, user_id, rec_id):
    row = conn.execute(f"{_REC} WHERE user_id = ? AND id = ?", (user_id, rec_id)).fetchone()
    return dict(row) if row else None


def mark_applied(conn, user_id, rec_id, now):
    """Guarded: only an active recommendation of this learner. Returns True if this call applied it."""
    return conn.execute("UPDATE ai_recommendations SET status = 'applied', applied_at = ? WHERE id = ? AND user_id = ? AND status = 'active'", (now, rec_id, user_id)).rowcount == 1


def expire_recommendations(conn, user_id, plan_date, keep_ids):
    """Active recommendations from earlier days, and today's that are no longer candidates, stop being offered."""
    marks = ",".join("?" * len(keep_ids)) or "NULL"
    conn.execute(f"UPDATE ai_recommendations SET status = 'expired' WHERE user_id = ? AND status = 'active' AND (plan_date < ? OR (plan_date = ? AND id NOT IN ({marks})))",
                 (user_id, plan_date, plan_date, *keep_ids))


# ---------- insights ----------
def insert_insight(conn, user_id, language_id, day, kind, subject, text, source, now):
    cur = conn.execute("INSERT OR IGNORE INTO ai_learning_insights(user_id, language_id, day, kind, subject, text, source, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                       (user_id, language_id, day, kind, subject[:60], text[:300], source, now))
    return cur.lastrowid if cur.rowcount == 1 else None


def list_insights(conn, user_id, day):
    return [dict(r) for r in conn.execute("SELECT id, kind, subject, text, source, day, created_at FROM ai_learning_insights WHERE user_id = ? AND day = ? ORDER BY id", (user_id, day)).fetchall()]


# ---------- micro-lessons ----------
def count_micro_created_on(conn, user_id, day):
    return conn.execute("SELECT COUNT(*) FROM ai_micro_lessons WHERE user_id = ? AND day = ?", (user_id, day)).fetchone()[0]


def find_micro(conn, user_id, day, item_id, kind):
    row = conn.execute("SELECT id FROM ai_micro_lessons WHERE user_id = ? AND day = ? AND item_id = ? AND kind = ?", (user_id, day, item_id, kind)).fetchone()
    return row["id"] if row else None


def insert_micro(conn, user_id, language_id, item_id, kind, topic_id, difficulty, mode, question, generator, note, day, now, expires):
    return conn.execute(
        """INSERT INTO ai_micro_lessons(user_id, language_id, item_id, kind, topic_id, difficulty, mode, question, generator, validation_note, day, created_at, expires_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (user_id, language_id, item_id, kind, topic_id, difficulty, mode, question, generator, note, day, now, expires)).lastrowid


def insert_options(conn, user_id, micro_id, options):
    for i, (text, correct) in enumerate(options, start=1):
        conn.execute("INSERT INTO ai_micro_lesson_options(micro_lesson_id, user_id, ord, text, is_correct) VALUES (?, ?, ?, ?, ?)", (micro_id, user_id, i, text, correct))


_MICRO = """SELECT m.id, m.item_id, m.kind, m.difficulty, m.mode, m.question, m.generator, m.status, m.created_at, m.expires_at, m.language_id, t.slug AS topic_slug, t.name AS topic_name
            FROM ai_micro_lessons m LEFT JOIN topics t ON t.id = m.topic_id"""


def expire_micro(conn, user_id, now):
    conn.execute("UPDATE ai_micro_lessons SET status = 'expired' WHERE user_id = ? AND status = 'validated' AND expires_at <= ?", (user_id, now))


def list_presentable_micro(conn, user_id, language_id, mode, now):
    """Only validated, unexpired lessons of this learner, in their current language and for their current age group."""
    return [dict(r) for r in conn.execute(f"{_MICRO} WHERE m.user_id = ? AND m.language_id = ? AND m.mode = ? AND m.status = 'validated' AND m.expires_at > ? ORDER BY m.id",
                                          (user_id, language_id, mode, now)).fetchall()]


def get_micro(conn, user_id, micro_id):
    row = conn.execute(f"{_MICRO} WHERE m.user_id = ? AND m.id = ?", (user_id, micro_id)).fetchone()
    return dict(row) if row else None


def options_for(conn, user_id, micro_id):
    """Server side: includes is_correct."""
    return [dict(r) for r in conn.execute("SELECT ord, text, is_correct FROM ai_micro_lesson_options WHERE micro_lesson_id = ? AND user_id = ? ORDER BY ord", (micro_id, user_id)).fetchall()]


def insert_attempt(conn, user_id, micro_id, option_ord, text, correct, now):
    conn.execute("INSERT INTO ai_micro_lesson_attempts(user_id, micro_lesson_id, option_ord, submitted_text, is_correct, attempted_at) VALUES (?, ?, ?, ?, ?, ?)",
                 (user_id, micro_id, option_ord, text, 1 if correct else 0, now))


def attempt_stats(conn, user_id, micro_ids):
    if not micro_ids:
        return {}
    marks = ",".join("?" * len(micro_ids))
    return {r["micro_lesson_id"]: {"attempts": r["n"], "correct": r["c"] or 0} for r in conn.execute(
        f"SELECT micro_lesson_id, COUNT(*) AS n, SUM(is_correct) AS c FROM ai_micro_lesson_attempts WHERE user_id = ? AND micro_lesson_id IN ({marks}) GROUP BY micro_lesson_id",
        (user_id, *micro_ids)).fetchall()}


# ---------- audit ----------
def insert_event(conn, user_id, event_type, ref_id, detail, now):
    conn.execute("INSERT INTO adaptive_learning_events(user_id, event_type, ref_id, detail, created_at) VALUES (?, ?, ?, ?, ?)", (user_id, event_type, ref_id, detail[:200], now))


def events(conn, user_id):
    return [dict(r) for r in conn.execute("SELECT event_type, ref_id, detail FROM adaptive_learning_events WHERE user_id = ? ORDER BY id", (user_id,)).fetchall()]


# ---------- roleplay grades ----------
def insert_turn_grade(conn, user_id, turn_id, g, provider):
    conn.execute(
        """INSERT INTO roleplay_turn_grades(turn_id, user_id, method, semantic_match, confidence, explanation, missing_objective, grammar_feedback, provider)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (turn_id, user_id, g["method"], 1 if g["semantic_match"] else 0, g["confidence"], g["explanation"], g["missing_objective"], g["grammar_feedback"], provider))


def grades_for_session(conn, user_id, session_id):
    return {r["turn_no"]: dict(r) for r in conn.execute(
        """SELECT t.turn_no, g.method, g.semantic_match, g.confidence, g.explanation, g.missing_objective, g.grammar_feedback, g.provider
           FROM roleplay_turn_grades g JOIN roleplay_turns t ON t.id = g.turn_id WHERE t.session_id = ? AND g.user_id = ?""", (session_id, user_id)).fetchall()}


# ---------- read-only evidence from the existing tables ----------
def recent_results(conn, user_id, language_id, source, limit):
    """Newest-first is_correct list of the learner's attempts from one source ('lesson' | 'situation' | 'listening') in the unified attempts view."""
    return [r[0] for r in conn.execute(
        "SELECT is_correct FROM learner_attempts WHERE user_id = ? AND language_id = ? AND source = ? ORDER BY attempted_at DESC, attempt_id DESC LIMIT ?",
        (user_id, language_id, source, limit)).fetchall()]


def last_attempt_day(conn, user_id):
    row = conn.execute("SELECT MAX(substr(attempted_at, 1, 10)) FROM learner_attempts WHERE user_id = ?", (user_id,)).fetchone()
    return row[0]


def recent_roleplays(conn, user_id, language_id, limit):
    return [dict(r) for r in conn.execute(
        """SELECT rp.id, rp.steps_correct, rp.steps_total, sit.title, sit.id AS situation_id FROM roleplay_sessions rp JOIN situations sit ON sit.id = rp.situation_id
           WHERE rp.user_id = ? AND rp.language_id = ? AND rp.status = 'completed' ORDER BY rp.completed_at DESC, rp.id DESC LIMIT ?""", (user_id, language_id, limit)).fetchall()]


def item_topic(conn, item_id, language_id, max_rank, age_group_id):
    """The topic of the first available lesson that teaches an item (for labelling a micro-lesson)."""
    from . import age
    row = conn.execute(
        f"""SELECT t.id, t.slug, t.name FROM lessons l JOIN cefr_levels c ON c.code = l.cefr_code JOIN lesson_topics lt ON lt.lesson_id = l.id JOIN topics t ON t.id = lt.topic_id
            WHERE l.language_id = ? AND l.status = 'published' AND c.rank <= ? AND {age.lesson()}
              AND (EXISTS (SELECT 1 FROM lesson_vocabulary lv WHERE lv.lesson_id = l.id AND lv.item_id = ?) OR EXISTS (SELECT 1 FROM exercises e WHERE e.lesson_id = l.id AND e.item_id = ?))
            ORDER BY c.rank, l.sort_order LIMIT 1""", (language_id, max_rank, age_group_id, item_id, item_id)).fetchone()
    return dict(row) if row else None
