"""Situations, their steps and the learner's progress through them. Takes an open connection;
every progress function is scoped by user_id."""
from . import age

_COLUMNS = """s.id, s.slug, s.title, s.description, s.goal, s.setting, s.partner_name, s.partner_role, s.difficulty,
              s.cefr_code, t.slug AS topic_slug, t.name AS topic_name, t.icon AS topic_icon"""


def _marks(ids):
    return ",".join("?" * len(ids))


def list_available(conn, language_id, max_rank, age_group_id):
    """Published situations in the target language at or below the learner's level, easiest level first."""
    rows = conn.execute(
        f"""SELECT {_COLUMNS} FROM situations s
            JOIN topics t ON t.id = s.topic_id JOIN cefr_levels c ON c.code = s.cefr_code
            WHERE s.language_id = ? AND s.status = 'published' AND c.rank <= ? AND {age.situation()}
            ORDER BY c.rank, s.sort_order""",
        (language_id, max_rank, age_group_id),
    ).fetchall()
    return [dict(r) for r in rows]


def get_available(conn, situation_id, language_id, max_rank, age_group_id):
    row = conn.execute(
        f"""SELECT {_COLUMNS} FROM situations s
            JOIN topics t ON t.id = s.topic_id JOIN cefr_levels c ON c.code = s.cefr_code
            WHERE s.id = ? AND s.language_id = ? AND s.status = 'published' AND c.rank <= ? AND {age.situation()}""",
        (situation_id, language_id, max_rank, age_group_id),
    ).fetchone()
    return dict(row) if row else None


def steps_for_situation(conn, situation_id):
    return [dict(r) for r in conn.execute(
        "SELECT id, sort_order, kind, prompt, prompt_meaning, item_id FROM situation_steps WHERE situation_id = ? ORDER BY sort_order",
        (situation_id,)).fetchall()]


def step_answers_for_display(conn, step_ids):
    """{step_id: [(answer_id, text)]} for choose_response options and conversation suggestions only.
    Typed-answer steps (translate, fill_blank) are never listed: their answers are the secret."""
    if not step_ids:
        return {}
    out = {}
    for r in conn.execute(
        f"""SELECT a.step_id, a.id, a.answer_text FROM situation_step_answers a JOIN situation_steps s ON s.id = a.step_id
            WHERE a.step_id IN ({_marks(step_ids)}) AND s.kind IN ('choose_response', 'conversation')
            ORDER BY a.step_id, a.sort_order""", step_ids):
        out.setdefault(r["step_id"], []).append((r["id"], r["answer_text"]))
    return out


def items_by_ids(conn, item_ids, native_id, fallback_id):
    if not item_ids:
        return {}
    rows = conn.execute(
        f"""SELECT v.id, v.kind, v.text, v.pronunciation, COALESCE(t.meaning, f.meaning) AS meaning, COALESCE(t.natural, f.natural) AS natural
            FROM vocabulary_items v
            LEFT JOIN vocabulary_translations t ON t.item_id = v.id AND t.language_id = ?
            LEFT JOIN vocabulary_translations f ON f.item_id = v.id AND f.language_id = ?
            WHERE v.id IN ({_marks(item_ids)})""",
        [native_id, fallback_id, *item_ids],
    ).fetchall()
    return {r["id"]: dict(r) for r in rows}


def get_step(conn, step_id, situation_id):
    row = conn.execute(
        "SELECT id, sort_order, kind, explanation FROM situation_steps WHERE id = ? AND situation_id = ?", (step_id, situation_id)).fetchone()
    return dict(row) if row else None


def answers_for_step(conn, step_id):
    """Server-side only: includes is_correct."""
    return [dict(r) for r in conn.execute(
        "SELECT id, answer_text, is_correct FROM situation_step_answers WHERE step_id = ? ORDER BY sort_order", (step_id,)).fetchall()]


# ---------- progress ----------
def ensure_started(conn, user_id, situation_id, now):
    conn.execute("INSERT OR IGNORE INTO situation_progress(user_id, situation_id, started_at) VALUES (?, ?, ?)", (user_id, situation_id, now))


def record_attempt(conn, user_id, step_id, answer_id, submitted_text, is_correct, now):
    conn.execute(
        """INSERT INTO situation_step_attempts(user_id, step_id, answer_id, submitted_text, is_correct, attempted_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (user_id, step_id, answer_id, submitted_text, 1 if is_correct else 0, now),
    )


def mark_completed_if_done(conn, user_id, situation_id, now):
    """Completes the situation once every step has a correct attempt by this user."""
    conn.execute(
        """UPDATE situation_progress SET completed_at = ?
           WHERE user_id = ? AND situation_id = ? AND completed_at IS NULL
             AND (SELECT COUNT(*) FROM situation_steps WHERE situation_id = ?) > 0
             AND (SELECT COUNT(*) FROM situation_steps WHERE situation_id = ?) =
                 (SELECT COUNT(*) FROM situation_steps s WHERE s.situation_id = ? AND EXISTS
                    (SELECT 1 FROM situation_step_attempts a WHERE a.user_id = ? AND a.step_id = s.id AND a.is_correct = 1))""",
        (now, user_id, situation_id, situation_id, situation_id, situation_id, user_id),
    )


def summaries(conn, user_id, situation_ids):
    """{situation_id: {steps_total, steps_completed, attempts, current_step_id, current_step_order, started_at, completed_at}}.
    The current step is the first step without a correct attempt (None once every step is passed)."""
    if not situation_ids:
        return {}
    marks = _marks(situation_ids)
    out = {i: {"steps_total": 0, "steps_completed": 0, "attempts": 0, "current_step_id": None, "current_step_order": None,
               "started_at": None, "completed_at": None} for i in situation_ids}
    for r in conn.execute(
        f"""SELECT s.situation_id, COUNT(*) AS total,
                   SUM(EXISTS (SELECT 1 FROM situation_step_attempts a WHERE a.user_id = ? AND a.step_id = s.id AND a.is_correct = 1)) AS passed
            FROM situation_steps s WHERE s.situation_id IN ({marks}) GROUP BY s.situation_id""",
        [user_id, *situation_ids],
    ):
        out[r["situation_id"]].update(steps_total=r["total"], steps_completed=r["passed"])
    for r in conn.execute(
        f"""SELECT s.situation_id, s.id, s.sort_order FROM situation_steps s
            WHERE s.situation_id IN ({marks}) AND NOT EXISTS
                (SELECT 1 FROM situation_step_attempts a WHERE a.user_id = ? AND a.step_id = s.id AND a.is_correct = 1)
            ORDER BY s.situation_id, s.sort_order""",
        [*situation_ids, user_id],
    ):
        if out[r["situation_id"]]["current_step_id"] is None:
            out[r["situation_id"]].update(current_step_id=r["id"], current_step_order=r["sort_order"])
    for r in conn.execute(
        f"""SELECT s.situation_id, COUNT(*) AS n FROM situation_step_attempts a JOIN situation_steps s ON s.id = a.step_id
            WHERE a.user_id = ? AND s.situation_id IN ({marks}) GROUP BY s.situation_id""",
        [user_id, *situation_ids],
    ):
        out[r["situation_id"]]["attempts"] = r["n"]
    for r in conn.execute(
        f"SELECT situation_id, started_at, completed_at FROM situation_progress WHERE user_id = ? AND situation_id IN ({marks})",
        [user_id, *situation_ids],
    ):
        out[r["situation_id"]].update(started_at=r["started_at"], completed_at=r["completed_at"])
    return out
