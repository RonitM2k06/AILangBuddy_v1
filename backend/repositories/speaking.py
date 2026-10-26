"""Speaking sessions, STT runs and transcripts. Takes an open connection; every learner-data function is scoped by user_id,
and every state change is a guarded UPDATE whose WHERE clause names the stages it may start from (so a wrong or racing
transition changes nothing and reports rowcount 0)."""
from . import age

# A phrase can be a speaking prompt if the learner can already reach it through a published lesson or situation at or
# below their level: the phrases of lessons, and the phrases studied in situations (e.g. the Emergency set).
_PROMPT_FILTER = f"""v.language_id = :lang AND v.kind = 'phrase' AND (
    EXISTS (SELECT 1 FROM lesson_vocabulary lv JOIN lessons l ON l.id = lv.lesson_id JOIN cefr_levels c ON c.code = l.cefr_code
            WHERE lv.item_id = v.id AND l.language_id = v.language_id AND l.status = 'published' AND c.rank <= :rank AND {age.lesson(param=':age')})
 OR EXISTS (SELECT 1 FROM situation_steps st JOIN situations s ON s.id = st.situation_id JOIN cefr_levels c ON c.code = s.cefr_code
            WHERE st.item_id = v.id AND st.kind = 'learn_phrase' AND s.language_id = v.language_id AND s.status = 'published' AND c.rank <= :rank AND {age.situation(param=':age')}))"""


def available_prompts(conn, language_id, max_rank, age_group_id):
    return [r["id"] for r in conn.execute(
        f"SELECT v.id FROM vocabulary_items v WHERE {_PROMPT_FILTER} ORDER BY v.id", {"lang": language_id, "rank": max_rank, "age": age_group_id}).fetchall()]


def is_available_prompt(conn, item_id, language_id, max_rank, age_group_id):
    return conn.execute(f"SELECT 1 FROM vocabulary_items v WHERE v.id = :id AND {_PROMPT_FILTER}",
                        {"id": item_id, "lang": language_id, "rank": max_rank, "age": age_group_id}).fetchone() is not None


def practised_items(conn, user_id, language_id):
    return {r["item_id"] for r in conn.execute(
        "SELECT DISTINCT item_id FROM speaking_sessions WHERE user_id = ? AND language_id = ? AND stage = 'completed'", (user_id, language_id))}


# ---------- sessions ----------
def create_audio_session(conn, user_id, language_id, now):
    cur = conn.execute("INSERT INTO audio_sessions(user_id, language_id, kind, status, started_at) VALUES (?, ?, 'speaking', 'started', ?)",
                       (user_id, language_id, now))
    return cur.lastrowid


def create_speaking_session(conn, session_id, user_id, language_id, item_id, locale, now):
    conn.execute(
        """INSERT INTO speaking_sessions(session_id, user_id, language_id, item_id, locale, stage, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, 'created', ?, ?)""", (session_id, user_id, language_id, item_id, locale, now, now))


_SESSION = """SELECT ss.session_id AS id, ss.stage, ss.item_id, ss.language_id, ss.locale, ss.audio_ref, ss.audio_mime, ss.audio_bytes,
                     ss.recording_ms, ss.recorded_at, ss.audio_deleted_at, ss.created_at, ss.updated_at, a.status AS audio_status
              FROM speaking_sessions ss JOIN audio_sessions a ON a.id = ss.session_id"""


def get_session(conn, user_id, session_id):
    row = conn.execute(f"{_SESSION} WHERE ss.session_id = ? AND ss.user_id = ?", (session_id, user_id)).fetchone()
    return dict(row) if row else None


def list_sessions(conn, user_id, language_id, limit):
    return [dict(r) for r in conn.execute(
        f"{_SESSION} WHERE ss.user_id = ? AND ss.language_id = ? ORDER BY ss.created_at DESC, ss.session_id DESC LIMIT ?",
        (user_id, language_id, limit)).fetchall()]


def mark_recorded(conn, user_id, session_id, ref, mime, size, sha256, recording_ms, now):
    return conn.execute(
        """UPDATE speaking_sessions SET stage = 'recorded', audio_ref = ?, audio_mime = ?, audio_bytes = ?, audio_sha256 = ?,
                  recording_ms = ?, recorded_at = ?, updated_at = ?
           WHERE session_id = ? AND user_id = ? AND stage = 'created'""",
        (ref, mime, size, sha256, recording_ms, now, now, session_id, user_id)).rowcount


def begin_processing(conn, user_id, session_id, now):
    """recorded -> processing, or failed -> processing (a retry), and only while the file still exists."""
    return conn.execute(
        """UPDATE speaking_sessions SET stage = 'processing', updated_at = ?
           WHERE session_id = ? AND user_id = ? AND stage IN ('recorded', 'failed') AND audio_ref IS NOT NULL""",
        (now, session_id, user_id)).rowcount


def end_processing(conn, user_id, session_id, to_stage, now):
    assert to_stage in ("completed", "failed")
    return conn.execute("UPDATE speaking_sessions SET stage = ?, updated_at = ? WHERE session_id = ? AND user_id = ? AND stage = 'processing'",
                        (to_stage, now, session_id, user_id)).rowcount


def cancel(conn, user_id, session_id, now):
    return conn.execute(
        "UPDATE speaking_sessions SET stage = 'cancelled', updated_at = ? WHERE session_id = ? AND user_id = ? AND stage IN ('created', 'recorded', 'failed')",
        (now, session_id, user_id)).rowcount


def clear_recording(conn, user_id, session_id, now):
    conn.execute("UPDATE speaking_sessions SET audio_ref = NULL, audio_deleted_at = ?, updated_at = ? WHERE session_id = ? AND user_id = ? AND audio_ref IS NOT NULL",
                 (now, now, session_id, user_id))


def sync_audio_session(conn, user_id, session_id, status, ended_at, duration_ms):
    """Keep the generic audio_sessions row in step with the pipeline stage (started while in flight, terminal once over)."""
    conn.execute("UPDATE audio_sessions SET status = ?, ended_at = ?, duration_ms = ? WHERE id = ? AND user_id = ? AND kind = 'speaking'",
                 (status, ended_at, duration_ms, session_id, user_id))


# ---------- runs and transcripts ----------
def insert_run(conn, session_id, user_id, provider, locale, now):
    return conn.execute("INSERT INTO stt_runs(session_id, user_id, provider, locale, status, started_at) VALUES (?, ?, ?, ?, 'processing', ?)",
                        (session_id, user_id, provider, locale, now)).lastrowid


def finish_run(conn, run_id, status, error_code, finished_at, duration_ms):
    conn.execute("UPDATE stt_runs SET status = ?, error_code = ?, finished_at = ?, duration_ms = ? WHERE id = ? AND status = 'processing'",
                 (status, error_code, finished_at, duration_ms, run_id))


def latest_run(conn, user_id, session_id):
    row = conn.execute(
        "SELECT id, provider, status, error_code, started_at, finished_at, duration_ms FROM stt_runs WHERE session_id = ? AND user_id = ? ORDER BY id DESC LIMIT 1",
        (session_id, user_id)).fetchone()
    return dict(row) if row else None


def run_count(conn, user_id, session_id):
    return conn.execute("SELECT COUNT(*) FROM stt_runs WHERE session_id = ? AND user_id = ?", (session_id, user_id)).fetchone()[0]


def stale_run(conn, user_id, session_id, cutoff):
    row = conn.execute("SELECT id FROM stt_runs WHERE session_id = ? AND user_id = ? AND status = 'processing' AND started_at < ?",
                       (session_id, user_id, cutoff)).fetchone()
    return row["id"] if row else None


def insert_transcript(conn, run_id, session_id, user_id, rank, text, confidence, locale, now):
    conn.execute("INSERT INTO speaking_transcripts(run_id, session_id, user_id, rank, text, confidence, locale, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                 (run_id, session_id, user_id, rank, text, confidence, locale, now))


def transcript_for(conn, user_id, session_id):
    """The best transcript (rank 1) of the session's completed run, with the provider that produced it."""
    row = conn.execute(
        """SELECT t.text, t.confidence, t.locale, r.provider FROM speaking_transcripts t JOIN stt_runs r ON r.id = t.run_id
           WHERE t.session_id = ? AND t.user_id = ? AND r.status = 'completed' AND t.rank = 1""", (session_id, user_id)).fetchone()
    return dict(row) if row else None


def progress_counts(conn, user_id, language_id):
    rows = conn.execute("SELECT stage, COUNT(*) AS n FROM speaking_sessions WHERE user_id = ? AND language_id = ? GROUP BY stage", (user_id, language_id)).fetchall()
    last = conn.execute("SELECT MAX(created_at) FROM speaking_sessions WHERE user_id = ? AND language_id = ?", (user_id, language_id)).fetchone()[0]
    return {r["stage"]: r["n"] for r in rows}, last


def expired_recordings(conn, completed_before, failed_before):
    """Recordings still on disk whose reason to exist is over (all learners: this is housekeeping, nothing is returned to a client)."""
    return [dict(r) for r in conn.execute(
        """SELECT session_id, user_id, audio_ref FROM speaking_sessions
           WHERE audio_ref IS NOT NULL AND ((stage = 'completed' AND updated_at < ?) OR (stage = 'failed' AND updated_at < ?))""",
        (completed_before, failed_before)).fetchall()]
