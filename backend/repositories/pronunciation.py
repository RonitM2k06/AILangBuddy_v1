"""Pronunciation assessments. Takes an open connection; every learner-data function is scoped by user_id."""


def best_transcript(conn, user_id, session_id):
    """The session's best transcript (rank 1 of its completed run): the text that was assessed."""
    row = conn.execute(
        """SELECT t.id, t.text, t.confidence, t.locale FROM speaking_transcripts t JOIN stt_runs r ON r.id = t.run_id
           WHERE t.session_id = ? AND t.user_id = ? AND r.status = 'completed' AND t.rank = 1""", (session_id, user_id)).fetchone()
    return dict(row) if row else None


def transcript_by_id(conn, user_id, session_id, transcript_id):
    row = conn.execute("SELECT id, text, confidence, locale FROM speaking_transcripts WHERE id = ? AND session_id = ? AND user_id = ?",
                       (transcript_id, session_id, user_id)).fetchone()
    return dict(row) if row else None


_COLUMNS = """id, session_id, transcript_id, provider, method, status, error_code, overall_score, words_expected, words_matched, locale, created_at"""


def completed_assessment(conn, user_id, session_id):
    row = conn.execute(f"SELECT {_COLUMNS} FROM pronunciation_assessments WHERE session_id = ? AND user_id = ? AND status = 'completed'", (session_id, user_id)).fetchone()
    return dict(row) if row else None


def latest_assessment(conn, user_id, session_id):
    """The completed assessment if there is one, otherwise the most recent failed attempt."""
    row = conn.execute(f"SELECT {_COLUMNS} FROM pronunciation_assessments WHERE session_id = ? AND user_id = ? ORDER BY (status = 'completed') DESC, id DESC LIMIT 1",
                       (session_id, user_id)).fetchone()
    return dict(row) if row else None


def attempt_count(conn, user_id, session_id):
    return conn.execute("SELECT COUNT(*) FROM pronunciation_assessments WHERE session_id = ? AND user_id = ?", (session_id, user_id)).fetchone()[0]


def insert_assessment(conn, session_id, user_id, transcript_id, provider, method, status, error_code, overall, expected, matched, locale, now):
    return conn.execute(
        """INSERT INTO pronunciation_assessments(session_id, user_id, transcript_id, provider, method, status, error_code, overall_score,
                                                 words_expected, words_matched, locale, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (session_id, user_id, transcript_id, provider, method, status, error_code, overall, expected, matched, locale, now)).lastrowid


def insert_components(conn, assessment_id, components):
    for name, score in components.items():
        conn.execute("INSERT INTO pronunciation_components(assessment_id, component, score) VALUES (?, ?, ?)", (assessment_id, name, score))


def insert_word_scores(conn, assessment_id, words):
    for position, (word, score) in enumerate(words, start=1):
        conn.execute("INSERT INTO pronunciation_word_scores(assessment_id, position, word, score) VALUES (?, ?, ?, ?)", (assessment_id, position, word, score))


def components_for(conn, assessment_id):
    return {r["component"]: r["score"] for r in conn.execute("SELECT component, score FROM pronunciation_components WHERE assessment_id = ? ORDER BY component", (assessment_id,))}


def word_scores_for(conn, assessment_id):
    return [dict(r) for r in conn.execute("SELECT position, word, score FROM pronunciation_word_scores WHERE assessment_id = ? ORDER BY position", (assessment_id,))]


def history(conn, user_id, language_id, limit):
    return [dict(r) for r in conn.execute(
        f"""SELECT a.id, a.session_id, a.method, a.status, a.error_code, a.overall_score, a.words_expected, a.words_matched, a.created_at, ss.item_id
            FROM pronunciation_assessments a JOIN speaking_sessions ss ON ss.session_id = a.session_id
            WHERE a.user_id = ? AND ss.language_id = ? ORDER BY a.created_at DESC, a.id DESC LIMIT ?""", (user_id, language_id, limit)).fetchall()]


def stats(conn, user_id, language_id):
    totals = conn.execute(
        """SELECT COUNT(*) AS attempts, SUM(a.status = 'failed') AS failed, COUNT(DISTINCT CASE WHEN a.status = 'completed' THEN a.session_id END) AS assessed,
                  COALESCE(SUM(CASE WHEN a.status = 'completed' THEN a.words_expected END), 0) AS expected,
                  COALESCE(SUM(CASE WHEN a.status = 'completed' THEN a.words_matched END), 0) AS matched
           FROM pronunciation_assessments a JOIN speaking_sessions ss ON ss.session_id = a.session_id WHERE a.user_id = ? AND ss.language_id = ?""", (user_id, language_id)).fetchone()
    by_method = conn.execute(
        """SELECT a.method, COUNT(*) AS n, AVG(a.overall_score) AS average FROM pronunciation_assessments a JOIN speaking_sessions ss ON ss.session_id = a.session_id
           WHERE a.user_id = ? AND ss.language_id = ? AND a.status = 'completed' GROUP BY a.method ORDER BY a.method""", (user_id, language_id)).fetchall()
    return dict(totals), [dict(r) for r in by_method]
