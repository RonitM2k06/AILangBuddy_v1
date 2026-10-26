import sqlite3

import pytest

from backend.db import connect

from .test_speaking_schema import RECORDED, audio_session, expect_integrity, one, run, speaking, transcript, user


def assessment(conn, sid, uid, tid, **over):
    cols = {"session_id": sid, "user_id": uid, "transcript_id": tid, "provider": "mock", "method": "mock", "status": "completed", "overall_score": 70,
            "words_expected": 3, "words_matched": 2, "locale": "hi-IN", "created_at": "2026-01-01 00:00:09", **over}
    return conn.execute(f"INSERT INTO pronunciation_assessments({','.join(cols)}) VALUES ({','.join('?' * len(cols))})", list(cols.values())).lastrowid


@pytest.fixture
def base(db_path):
    """(db_path, uid, session_id, transcript_id): a completed speaking session with a transcript."""
    with connect(db_path) as conn:
        uid = user(conn)
        sid = speaking(conn, audio_session(conn, uid, status="completed"), uid, stage="completed", **{**RECORDED, "audio_ref": None, "audio_deleted_at": "2026-01-01 00:00:08"})
        rid = run(conn, sid, uid, status="completed", finished_at="2026-01-01 00:00:08")
        tid = transcript(conn, rid, sid, uid)
    return db_path, uid, sid, tid


# ---------- ownership ----------
def test_an_assessment_needs_its_own_sessions_owner_and_transcript(base):
    db_path, uid, sid, tid = base
    with connect(db_path) as conn:
        conn.execute("INSERT INTO users(handle, display_name) VALUES ('other', 'Other')")
        other = user(conn, "other")
        osid = speaking(conn, audio_session(conn, other), other)
        orid = run(conn, osid, other, status="completed", finished_at="2026-01-01 00:00:08")
        otid = transcript(conn, orid, osid, other)
    expect_integrity(db_path, lambda c: assessment(c, sid, other, tid))              # someone else's user id on my session
    expect_integrity(db_path, lambda c: assessment(c, sid, uid, otid))               # another session's transcript
    expect_integrity(db_path, lambda c: assessment(c, 99999, uid, tid))
    expect_integrity(db_path, lambda c: assessment(c, sid, uid, 99999))
    with connect(db_path) as conn:
        assessment(conn, sid, uid, tid)
        assert one(conn, "SELECT COUNT(*) FROM pronunciation_assessments") == 1


# ---------- score ranges and status consistency ----------
@pytest.mark.parametrize("over", [
    {"overall_score": -1}, {"overall_score": 101}, {"overall_score": 1000},
    {"overall_score": None},                                                          # a completed assessment has a score
    {"status": "failed", "overall_score": 50, "error_code": "provider_error"},        # a failed one never does
    {"status": "failed", "overall_score": None, "error_code": None},                  # a failed one names its error
    {"status": "completed", "error_code": "provider_error"},                          # a completed one has no error
    {"status": "failed", "overall_score": None, "error_code": "gremlins"},
    {"status": "pending"}, {"method": "magic"}, {"method": None},                     # a score always says what kind of measurement it is
    {"provider": "  "}, {"provider": "x" * 41}, {"locale": ""},
    {"words_expected": 0}, {"words_matched": -1}, {"words_expected": 2, "words_matched": 3},   # matched cannot exceed expected
])
def test_assessment_constraints(base, over):
    db_path, uid, sid, tid = base
    expect_integrity(db_path, lambda c: assessment(c, sid, uid, tid, **over))


@pytest.mark.parametrize("score", [0, 1, 50, 99, 100])
def test_score_boundaries_are_accepted(base, score):
    db_path, uid, sid, tid = base
    with connect(db_path) as conn:
        assessment(conn, sid, uid, tid, overall_score=score)


@pytest.mark.parametrize("method", ["mock", "proxy", "model"])
def test_each_measurement_method_is_accepted(base, method):
    db_path, uid, sid, tid = base
    with connect(db_path) as conn:
        assessment(conn, sid, uid, tid, method=method)


def test_a_failed_attempt_may_have_no_method_and_every_error_code_is_valid(base):
    db_path, uid, sid, tid = base
    with connect(db_path) as conn:
        for code in ("provider_unavailable", "provider_error", "provider_timeout", "malformed_output", "unsupported_language", "no_signal", "recording_unavailable"):
            assessment(conn, sid, uid, tid, status="failed", overall_score=None, error_code=code, method=None, provider="none")
        assert one(conn, "SELECT COUNT(*) FROM pronunciation_assessments") == 7        # failed attempts are history, not a conflict


def test_only_one_completed_assessment_per_session(base):
    db_path, uid, sid, tid = base
    with connect(db_path) as conn:
        assessment(conn, sid, uid, tid)
    expect_integrity(db_path, lambda c: assessment(c, sid, uid, tid, overall_score=10))     # the database refuses a second completed one
    with connect(db_path) as conn:
        assessment(conn, sid, uid, tid, status="failed", overall_score=None, error_code="provider_error")   # but a failure may sit beside it


# ---------- components and word scores ----------
def test_component_constraints(base):
    db_path, uid, sid, tid = base
    with connect(db_path) as conn:
        aid = assessment(conn, sid, uid, tid)
    ins = "INSERT INTO pronunciation_components(assessment_id, component, score) VALUES (?, ?, ?)"
    for args in ((aid, "phoneme_accuracy_x", 50), (aid, "fluency", -1), (aid, "fluency", 101), (99999, "fluency", 50), (aid, "fluency", None)):
        expect_integrity(db_path, lambda c, a=args: c.execute(ins, a))
    with connect(db_path) as conn:
        for name in ("phoneme_accuracy", "word_accuracy", "fluency", "prosody", "confidence"):
            conn.execute(ins, (aid, name, 80))
        assert one(conn, "SELECT COUNT(*) FROM pronunciation_components") == 5
    expect_integrity(db_path, lambda c: c.execute(ins, (aid, "fluency", 10)))                # one row per component


def test_word_score_constraints(base):
    db_path, uid, sid, tid = base
    with connect(db_path) as conn:
        aid = assessment(conn, sid, uid, tid)
    ins = "INSERT INTO pronunciation_word_scores(assessment_id, position, word, score) VALUES (?, ?, ?, ?)"
    for args in ((aid, 0, "w", 50), (aid, 1, " ", 50), (aid, 1, "w" * 61, 50), (aid, 1, "w", 101), (aid, 1, "w", -1), (99999, 1, "w", 50)):
        expect_integrity(db_path, lambda c, a=args: c.execute(ins, a))
    with connect(db_path) as conn:
        conn.execute(ins, (aid, 1, "नमस्ते", 55))
        conn.execute(ins, (aid, 2, "आप", 90))
    expect_integrity(db_path, lambda c: c.execute(ins, (aid, 1, "dup", 10)))                  # one score per position


def test_there_is_no_phoneme_level_storage_and_no_audio_column(db_path):
    with connect(db_path) as conn:
        names = {r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert not {n for n in names if "phoneme" in n}                                       # nothing exists to store what no provider reports
        for t in ("pronunciation_assessments", "pronunciation_components", "pronunciation_word_scores"):
            cols = {r["name"]: r["type"].upper() for r in conn.execute(f"PRAGMA table_info({t})")}
            assert "BLOB" not in cols.values() and not {"audio", "audio_ref", "path", "file"} & set(cols), t


# ---------- cascades ----------
def test_assessments_cascade_with_their_session_transcript_and_user(base):
    db_path, uid, sid, tid = base
    with connect(db_path) as conn:
        aid = assessment(conn, sid, uid, tid)
        conn.execute("INSERT INTO pronunciation_components VALUES (?, 'fluency', 70)", (aid,))
        conn.execute("INSERT INTO pronunciation_word_scores VALUES (?, 1, 'w', 70)", (aid,))
        conn.execute("DELETE FROM speaking_transcripts WHERE id=?", (tid,))
        for t in ("pronunciation_assessments", "pronunciation_components", "pronunciation_word_scores"):
            assert one(conn, f"SELECT COUNT(*) FROM {t}") == 0
    with connect(db_path) as conn:
        conn.execute("DELETE FROM users WHERE id=?", (uid,))
        assert one(conn, "SELECT COUNT(*) FROM pronunciation_assessments") == 0


def test_expected_indexes_exist(db_path):
    with connect(db_path) as conn:
        names = {r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='index'")}
    assert {"uq_speaking_transcripts_id_session", "uq_pron_one_completed", "idx_pron_session", "idx_pron_user_time"} <= names


# ---------- the evidence view keeps measurements apart from test signals ----------
def test_only_real_model_measurements_count_as_evidence(base):
    db_path, uid, sid, tid = base
    with connect(db_path) as conn:
        assessment(conn, sid, uid, tid, method="mock", overall_score=95)
        assert one(conn, "SELECT COUNT(*) FROM learner_pronunciation_evidence") == 0         # a mock score is never evidence
        conn.execute("DELETE FROM pronunciation_assessments")
        assessment(conn, sid, uid, tid, method="proxy", overall_score=95)
        assert one(conn, "SELECT COUNT(*) FROM learner_pronunciation_evidence") == 0         # neither is a proxy
        conn.execute("DELETE FROM pronunciation_assessments")
        assessment(conn, sid, uid, tid, status="failed", overall_score=None, error_code="provider_error", method="model")
        assert one(conn, "SELECT COUNT(*) FROM learner_pronunciation_evidence") == 0         # nor a failure
        conn.execute("DELETE FROM pronunciation_assessments")
        assessment(conn, sid, uid, tid, method="model", overall_score=64)
        row = conn.execute("SELECT user_id, method, overall_score, session_id FROM learner_pronunciation_evidence").fetchone()
        assert tuple(row) == (uid, "model", 64, sid)


def test_phase6_views_do_not_read_assessments(db_path):
    with connect(db_path) as conn:
        sql = " ".join(r["sql"] for r in conn.execute("SELECT sql FROM sqlite_master WHERE type='view' AND name IN ('learner_attempts', 'learner_attempt_topics')"))
    assert "pronunciation" not in sql and "speaking" not in sql
