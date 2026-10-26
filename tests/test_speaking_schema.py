import sqlite3

import pytest

from backend.db import connect

HI = "(SELECT id FROM languages WHERE code='hi')"
ITEM = "(SELECT id FROM vocabulary_items WHERE pronunciation='Paani milega?')"
REF = "rec_" + "a" * 32 + ".webm"
SHA = "b" * 64


def one(conn, sql, *args):
    return conn.execute(sql, args).fetchone()[0]


def expect_integrity(db_path, fn):
    with pytest.raises(sqlite3.IntegrityError):
        with connect(db_path) as conn:
            fn(conn)


def user(conn, handle="demo-alex"):
    return one(conn, "SELECT id FROM users WHERE handle=?", handle)


def audio_session(conn, uid, kind="speaking", status="started"):
    ended = None if status == "started" else "2026-01-01 00:00:09"
    return conn.execute("INSERT INTO audio_sessions(user_id, language_id, kind, status, started_at, ended_at) VALUES (?, (SELECT id FROM languages WHERE code='hi'), ?, ?, '2026-01-01 00:00:00', ?)",
                        (uid, kind, status, ended)).lastrowid


RECORDED = {"audio_ref": REF, "audio_mime": "audio/webm", "audio_bytes": 100, "audio_sha256": SHA, "recording_ms": 2000, "recorded_at": "2026-01-01 00:00:05"}


def speaking(conn, sid, uid, **over):
    cols = {"session_id": sid, "user_id": uid, "language_id": one(conn, "SELECT id FROM languages WHERE code='hi'"),
            "item_id": one(conn, "SELECT id FROM vocabulary_items WHERE pronunciation='Paani milega?'"), "locale": "hi-IN",
            "stage": "created", "created_at": "2026-01-01 00:00:00", "updated_at": "2026-01-01 00:00:00", **over}
    conn.execute(f"INSERT INTO speaking_sessions({','.join(cols)}) VALUES ({','.join('?' * len(cols))})", list(cols.values()))
    return sid


def run(conn, sid, uid, **over):
    cols = {"session_id": sid, "user_id": uid, "provider": "mock", "locale": "hi-IN", "status": "processing", "started_at": "2026-01-01 00:00:06", **over}
    return conn.execute(f"INSERT INTO stt_runs({','.join(cols)}) VALUES ({','.join('?' * len(cols))})", list(cols.values())).lastrowid


def transcript(conn, run_id, sid, uid, **over):
    cols = {"run_id": run_id, "session_id": sid, "user_id": uid, "rank": 1, "text": "नमस्ते", "locale": "hi-IN", "created_at": "2026-01-01 00:00:07", **over}
    return conn.execute(f"INSERT INTO speaking_transcripts({','.join(cols)}) VALUES ({','.join('?' * len(cols))})", list(cols.values())).lastrowid


@pytest.fixture
def base(db_path):
    """(db_path, uid, session_id) with a fresh speaking audio session and its detail row."""
    with connect(db_path) as conn:
        uid = user(conn)
        sid = speaking(conn, audio_session(conn, uid), uid)
    return db_path, uid, sid


# ---------- speaking_sessions: reuse of audio_sessions and ownership ----------
def test_a_speaking_detail_needs_a_speaking_audio_session_of_the_same_learner(db_path):
    with connect(db_path) as conn:
        me = user(conn)
        conn.execute("INSERT INTO users(handle, display_name) VALUES ('other', 'Other')")
        other = user(conn, "other")
        listening, theirs, mine = audio_session(conn, me, "listening"), audio_session(conn, other), audio_session(conn, me)
    expect_integrity(db_path, lambda c: speaking(c, listening, me))                 # the session is a LISTENING session
    expect_integrity(db_path, lambda c: speaking(c, theirs, me))                    # the session belongs to another learner
    expect_integrity(db_path, lambda c: speaking(c, 99999, me))                     # no such audio session
    with connect(db_path) as conn:
        speaking(conn, mine, me)
        assert one(conn, "SELECT COUNT(*) FROM speaking_sessions") == 1
    expect_integrity(db_path, lambda c: speaking(c, mine, me))                      # one detail per session


def test_kind_column_is_always_speaking(db_path):
    with connect(db_path) as conn:
        uid = user(conn)
        sid = audio_session(conn, uid)
    expect_integrity(db_path, lambda c: speaking(c, sid, uid, kind="listening"))


def test_no_second_session_system_was_created(db_path):
    with connect(db_path) as conn:
        names = {r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "speaking_sessions" in names and not {"sessions_speaking", "voice_sessions", "recordings"} & names


@pytest.mark.parametrize("over", [
    {"stage": "paused"}, {"stage": "recorded"},                                     # recorded needs a recording
    {"audio_mime": "audio/webm"},                                                   # a recording is all-or-nothing
    {**RECORDED},                                                                   # created but already recorded
    {**RECORDED, "stage": "recorded", "audio_ref": "../etc/passwd"},                # path traversal in the reference
    {**RECORDED, "stage": "recorded", "audio_ref": "a/b.webm"},
    {**RECORDED, "stage": "recorded", "audio_ref": "a\\b.webm"},
    {**RECORDED, "stage": "recorded", "audio_ref": "rec x.webm"},
    {**RECORDED, "stage": "recorded", "audio_ref": "x"},                            # too short
    {**RECORDED, "stage": "recorded", "audio_ref": "r" * 65},                       # too long
    {**RECORDED, "stage": "recorded", "audio_mime": "text/html"},
    {**RECORDED, "stage": "recorded", "audio_mime": "video/webm"},
    {**RECORDED, "stage": "recorded", "audio_bytes": 0}, {**RECORDED, "stage": "recorded", "audio_bytes": -5},
    {**RECORDED, "stage": "recorded", "audio_sha256": "xyz"}, {**RECORDED, "stage": "recorded", "audio_sha256": "G" * 64},
    {**RECORDED, "stage": "recorded", "recording_ms": 0},
    {**RECORDED, "stage": "recorded", "audio_ref": None},                           # recorded/processing need the file
    {**RECORDED, "stage": "processing", "audio_ref": None},
    {"audio_ref": REF},                                                             # a reference without a recording
    {**RECORDED, "stage": "completed", "audio_deleted_at": "2026-01-01 00:00:09"},  # deleted but the reference is still set
    {"audio_deleted_at": "2026-01-01 00:00:09"},                                    # deleted but there was never a recording
    {"locale": "  "},
])
def test_speaking_session_constraints(db_path, over):
    with connect(db_path) as conn:
        uid = user(conn)
        sid = audio_session(conn, uid)
    expect_integrity(db_path, lambda c: speaking(c, sid, uid, **over))


@pytest.mark.parametrize("stage,over", [
    ("created", {}), ("recorded", RECORDED), ("processing", RECORDED), ("failed", RECORDED), ("completed", RECORDED),
    ("completed", {**RECORDED, "audio_ref": None, "audio_deleted_at": "2026-01-01 00:00:09"}),       # recording purged after transcription
    ("cancelled", {}), ("cancelled", {**RECORDED, "audio_ref": None, "audio_deleted_at": "2026-01-01 00:00:09"}),
    ("recorded", {**RECORDED, "recording_ms": None}),                                                # the client may not report a duration
])
def test_speaking_session_valid_combinations(db_path, stage, over):
    with connect(db_path) as conn:
        uid = user(conn)
        speaking(conn, audio_session(conn, uid), uid, stage=stage, **over)


def test_prompt_item_must_match_the_language(db_path):
    with connect(db_path) as conn:
        uid = user(conn)
        sid = audio_session(conn, uid)
        es = one(conn, "SELECT id FROM languages WHERE code='es'")
    expect_integrity(db_path, lambda c: speaking(c, sid, uid, language_id=es))                       # the phrase is Hindi, not Spanish
    expect_integrity(db_path, lambda c: speaking(c, sid, uid, item_id=99999))


def test_a_prompt_phrase_in_use_cannot_be_deleted(base):
    db_path, *_ = base

    def delete_phrase_after_removing_every_other_reference(conn):
        for table in ("listening_attempts", "listening_options", "listening_activities", "situation_steps", "exercises", "lesson_vocabulary"):
            conn.execute(f"DELETE FROM {table}")
        conn.execute("DELETE FROM vocabulary_items WHERE pronunciation='Paani milega?'")     # still referenced by the speaking session

    expect_integrity(db_path, delete_phrase_after_removing_every_other_reference)


def test_deleting_the_audio_session_or_user_cascades_everything(base):
    db_path, uid, sid = base
    with connect(db_path) as conn:
        rid = run(conn, sid, uid, status="completed", finished_at="2026-01-01 00:00:08")
        transcript(conn, rid, sid, uid)
        conn.execute("DELETE FROM audio_sessions WHERE id=?", (sid,))
        for t in ("speaking_sessions", "stt_runs", "speaking_transcripts"):
            assert one(conn, f"SELECT COUNT(*) FROM {t}") == 0
        sid = speaking(conn, audio_session(conn, uid), uid)
        rid = run(conn, sid, uid)
        conn.execute("DELETE FROM users WHERE id=?", (uid,))
        for t in ("audio_sessions", "speaking_sessions", "stt_runs"):
            assert one(conn, f"SELECT COUNT(*) FROM {t}") == 0


# ---------- stt_runs ----------
def test_run_status_error_and_timing_consistency(base):
    db_path, uid, sid = base
    bad = [{"status": "queued"}, {"provider": "  "}, {"provider": "x" * 41}, {"locale": ""},
           {"status": "processing", "finished_at": "2026-01-01 00:00:08"},           # processing must not be finished
           {"status": "completed"}, {"status": "failed", "finished_at": "2026-01-01 00:00:08"},
           {"status": "failed", "finished_at": "2026-01-01 00:00:08", "error_code": "gremlins"},
           {"status": "completed", "finished_at": "2026-01-01 00:00:08", "error_code": "provider_error"},   # only failed runs have an error
           {"status": "processing", "error_code": "provider_error"},
           {"status": "completed", "finished_at": "2026-01-01 00:00:08", "duration_ms": -1}]
    for over in bad:
        expect_integrity(db_path, lambda c, o=over: run(c, sid, uid, **o))
    with connect(db_path) as conn:
        for code in ("provider_unavailable", "provider_timeout", "provider_error", "no_speech", "unsupported_language", "unsupported_format", "recording_unavailable"):
            run(conn, sid, uid, status="failed", error_code=code, finished_at="2026-01-01 00:00:08", duration_ms=50)      # history of failures is kept
        assert one(conn, "SELECT COUNT(*) FROM stt_runs") == 7


def test_run_ownership_composite_fk(base):
    db_path, uid, sid = base
    with connect(db_path) as conn:
        conn.execute("INSERT INTO users(handle, display_name) VALUES ('other', 'Other')")
        other = user(conn, "other")
    expect_integrity(db_path, lambda c: run(c, sid, other))                          # someone else's user id on my session
    expect_integrity(db_path, lambda c: run(c, 99999, uid))


def test_only_one_run_in_flight_and_one_completed_per_session(base):
    db_path, uid, sid = base
    with connect(db_path) as conn:
        run(conn, sid, uid)                                                          # processing
    expect_integrity(db_path, lambda c: run(c, sid, uid))                            # a second concurrent run is refused by the database
    with connect(db_path) as conn:
        conn.execute("UPDATE stt_runs SET status='completed', finished_at='2026-01-01 00:00:08'")
        run(conn, sid, uid)                                                          # a new run may start once the first finished
    expect_integrity(db_path, lambda c: c.execute("UPDATE stt_runs SET status='completed', finished_at='2026-01-01 00:00:09' WHERE status='processing'"))   # but not a second completed one


# ---------- speaking_transcripts ----------
def test_transcript_constraints_and_ownership(base):
    db_path, uid, sid = base
    with connect(db_path) as conn:
        rid = run(conn, sid, uid, status="completed", finished_at="2026-01-01 00:00:08")
        conn.execute("INSERT INTO users(handle, display_name) VALUES ('other', 'Other')")
        other = user(conn, "other")
        other_sid = speaking(conn, audio_session(conn, other), other)
        other_rid = run(conn, other_sid, other, status="completed", finished_at="2026-01-01 00:00:08")
    for over in ({"text": "  "}, {"text": "x" * 2001}, {"confidence": -0.1}, {"confidence": 1.1}, {"rank": 0}, {"locale": ""}):
        expect_integrity(db_path, lambda c, o=over: transcript(c, rid, sid, uid, **o))
    expect_integrity(db_path, lambda c: transcript(c, rid, sid, other))              # another learner's id on my transcript
    expect_integrity(db_path, lambda c: transcript(c, other_rid, sid, uid))          # a run that belongs to a different session
    expect_integrity(db_path, lambda c: transcript(c, 99999, sid, uid))
    with connect(db_path) as conn:
        transcript(conn, rid, sid, uid, confidence=0.0)
        transcript(conn, rid, sid, uid, rank=2, confidence=1.0)                      # alternatives are further ranks
        assert one(conn, "SELECT COUNT(*) FROM speaking_transcripts") == 2
    expect_integrity(db_path, lambda c: transcript(c, rid, sid, uid))                # (run, rank) is unique


def test_transcripts_cascade_with_their_run(base):
    db_path, uid, sid = base
    with connect(db_path) as conn:
        rid = run(conn, sid, uid, status="completed", finished_at="2026-01-01 00:00:08")
        transcript(conn, rid, sid, uid)
        conn.execute("DELETE FROM stt_runs WHERE id=?", (rid,))
        assert one(conn, "SELECT COUNT(*) FROM speaking_transcripts") == 0


# ---------- no blobs, indexes ----------
def test_no_raw_audio_column_anywhere(db_path):
    with connect(db_path) as conn:
        for table in ("speaking_sessions", "stt_runs", "speaking_transcripts", "audio_sessions"):
            types = {r["type"].upper() for r in conn.execute(f"PRAGMA table_info({table})")}
            assert "BLOB" not in types, table
            names = {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}
            assert not {"audio", "audio_data", "audio_blob", "data", "bytes_data"} & names, table


def test_expected_indexes_exist(db_path):
    with connect(db_path) as conn:
        names = {r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='index'")}
    assert {"uq_audio_sessions_owner_kind", "idx_speaking_sessions_user_item", "idx_speaking_sessions_item", "uq_stt_runs_one_in_flight",
            "uq_stt_runs_one_completed", "idx_stt_runs_session", "idx_speaking_transcripts_session"} <= names


def test_listening_data_is_unaffected_by_the_new_index_and_tables(db_path):
    with connect(db_path) as conn:
        uid = user(conn)
        s1 = audio_session(conn, uid, "listening")
        s2 = audio_session(conn, uid, "listening")
        assert s1 != s2 and one(conn, "SELECT COUNT(*) FROM audio_sessions WHERE kind='listening'") == 2
