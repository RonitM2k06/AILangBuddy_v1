"""Roleplay sessions, turns and feedback. Takes an open connection; every function is scoped by user_id."""


def get_active_for_situation(conn, user_id, situation_id):
    row = conn.execute("SELECT id FROM roleplay_sessions WHERE user_id = ? AND situation_id = ? AND status = 'active'", (user_id, situation_id)).fetchone()
    return row["id"] if row else None


def create_session(conn, user_id, situation_id, language_id, cefr, mode, steps_total, now):
    return conn.execute(
        """INSERT INTO roleplay_sessions(user_id, situation_id, language_id, cefr_code, mode, steps_total, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (user_id, situation_id, language_id, cefr, mode, steps_total, now)).lastrowid


_SESSION = "SELECT id, situation_id, language_id, cefr_code, mode, status, steps_total, steps_correct, steps_missed, created_at, completed_at FROM roleplay_sessions"


def get_session(conn, user_id, session_id):
    row = conn.execute(f"{_SESSION} WHERE user_id = ? AND id = ?", (user_id, session_id)).fetchone()
    return dict(row) if row else None


def list_sessions(conn, user_id, limit):
    return [dict(r) for r in conn.execute(
        f"""SELECT s.id, s.status, s.steps_total, s.created_at, s.completed_at, sit.title FROM roleplay_sessions s JOIN situations sit ON sit.id = s.situation_id
            WHERE s.user_id = ? ORDER BY s.id DESC LIMIT ?""", (user_id, limit)).fetchall()]


def turns(conn, user_id, session_id):
    return [dict(r) for r in conn.execute(
        """SELECT turn_no, step_id, attempt_no, learner_text, input_mode, verdict, resolved, hint, character_reply, provider, created_at
           FROM roleplay_turns WHERE user_id = ? AND session_id = ? ORDER BY turn_no""", (user_id, session_id)).fetchall()]


def find_turn_by_client_id(conn, user_id, session_id, client_id):
    row = conn.execute(
        """SELECT turn_no, step_id, attempt_no, learner_text, input_mode, verdict, resolved, hint, character_reply, provider, created_at
           FROM roleplay_turns WHERE user_id = ? AND session_id = ? AND client_id = ?""", (user_id, session_id, client_id)).fetchone()
    return dict(row) if row else None


def insert_turn(conn, session_id, user_id, situation_id, step_id, turn_no, attempt_no, text, mode, speaking_session_id, verdict, resolved, hint, reply, provider, client_id, now):
    return conn.execute(
        """INSERT INTO roleplay_turns(session_id, user_id, situation_id, step_id, turn_no, attempt_no, learner_text, input_mode, speaking_session_id,
                                      verdict, resolved, hint, character_reply, provider, client_id, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (session_id, user_id, situation_id, step_id, turn_no, attempt_no, text, mode, speaking_session_id, verdict, resolved, hint, reply, provider, client_id, now)).lastrowid


def complete_session(conn, user_id, session_id, correct, missed, now):
    """Guarded: only an active session of this learner. Returns True if this call completed it."""
    return conn.execute("UPDATE roleplay_sessions SET status = 'completed', steps_correct = ?, steps_missed = ?, completed_at = ? WHERE id = ? AND user_id = ? AND status = 'active'",
                        (correct, missed, now, session_id, user_id)).rowcount == 1


def insert_feedback(conn, session_id, user_id, f, now):
    conn.execute(
        """INSERT INTO roleplay_feedback(session_id, user_id, steps_total, steps_correct, steps_missed, first_try_correct, voice_turns, correctness_text,
                                         vocabulary_feedback, grammar_feedback, hint, encouragement, next_step, pronunciation_note, provider, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (session_id, user_id, f["steps_total"], f["steps_correct"], f["steps_missed"], f["first_try_correct"], f["voice_turns"], f["correctness_text"],
         f["vocabulary_feedback"], f["grammar_feedback"], f["hint"], f["encouragement"], f["next_step"], f["pronunciation_note"], f["provider"], now))


def get_feedback(conn, user_id, session_id):
    row = conn.execute(
        """SELECT steps_total, steps_correct, steps_missed, first_try_correct, voice_turns, correctness_text, vocabulary_feedback, grammar_feedback, hint,
                  encouragement, next_step, pronunciation_note, provider, created_at FROM roleplay_feedback WHERE user_id = ? AND session_id = ?""", (user_id, session_id)).fetchone()
    return dict(row) if row else None
