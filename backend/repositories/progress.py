"""Learner progress persistence. Every function is scoped by user_id; callers pass the session's user."""


def ensure_started(conn, user_id, lesson_id, now):
    conn.execute("INSERT OR IGNORE INTO lesson_progress(user_id, lesson_id, started_at) VALUES (?, ?, ?)", (user_id, lesson_id, now))


def record_attempt(conn, user_id, exercise_id, answer_id, submitted_text, is_correct, now):
    conn.execute(
        """INSERT INTO exercise_attempts(user_id, exercise_id, answer_id, submitted_text, is_correct, attempted_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (user_id, exercise_id, answer_id, submitted_text, 1 if is_correct else 0, now),
    )


def mark_completed_if_done(conn, user_id, lesson_id, now):
    """Completes the lesson once every one of its exercises has a correct attempt by this user."""
    conn.execute(
        """UPDATE lesson_progress SET completed_at = ?
           WHERE user_id = ? AND lesson_id = ? AND completed_at IS NULL
             AND (SELECT COUNT(*) FROM exercises WHERE lesson_id = ?) > 0
             AND (SELECT COUNT(*) FROM exercises WHERE lesson_id = ?) =
                 (SELECT COUNT(*) FROM exercises e WHERE e.lesson_id = ? AND EXISTS
                    (SELECT 1 FROM exercise_attempts a WHERE a.user_id = ? AND a.exercise_id = e.id AND a.is_correct = 1))""",
        (now, user_id, lesson_id, lesson_id, lesson_id, lesson_id, user_id),
    )


def summaries(conn, user_id, lesson_ids):
    """{lesson_id: {total, correct, started_at, completed_at}} for this user (zeros / None when untouched)."""
    if not lesson_ids:
        return {}
    marks = ",".join("?" * len(lesson_ids))
    out = {i: {"exercises_total": 0, "exercises_correct": 0, "started_at": None, "completed_at": None} for i in lesson_ids}
    for r in conn.execute(
        f"""SELECT e.lesson_id, COUNT(*) AS total,
                   SUM(EXISTS (SELECT 1 FROM exercise_attempts a WHERE a.user_id = ? AND a.exercise_id = e.id AND a.is_correct = 1)) AS correct
            FROM exercises e WHERE e.lesson_id IN ({marks}) GROUP BY e.lesson_id""",
        [user_id, *lesson_ids],
    ):
        out[r["lesson_id"]].update(exercises_total=r["total"], exercises_correct=r["correct"])
    for r in conn.execute(
        f"SELECT lesson_id, started_at, completed_at FROM lesson_progress WHERE user_id = ? AND lesson_id IN ({marks})",
        [user_id, *lesson_ids],
    ):
        out[r["lesson_id"]].update(started_at=r["started_at"], completed_at=r["completed_at"])
    return out
