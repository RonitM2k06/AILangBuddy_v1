import sqlite3

import pytest

from backend.db import connect
from backend.db.migrate import MigrationError, discover, migrate

FOUNDATION_TABLES = {"users", "languages", "cefr_levels", "cities", "city_languages", "state", "schema_migrations", "roles", "user_roles", "sessions", "language_levels", "age_groups", "learner_profiles",
                     "topics", "lessons", "lesson_topics", "vocabulary_items", "vocabulary_translations", "vocabulary_examples",
                     "lesson_vocabulary", "grammar_topics", "grammar_topic_texts", "grammar_examples", "lesson_grammar",
                     "exercises", "exercise_answers", "lesson_progress", "exercise_attempts",
                     "situations", "situation_steps", "situation_step_answers", "situation_progress", "situation_step_attempts",
                     "skills", "confidence_scores", "weaknesses", "daily_tasks",
                     "audio_assets", "listening_activities", "listening_options", "audio_sessions", "listening_attempts",
                     "speaking_sessions", "stt_runs", "speaking_transcripts",
                     "pronunciation_assessments", "pronunciation_components", "pronunciation_word_scores",
                     "lesson_age_groups", "situation_age_groups", "listening_activity_age_groups", "child_game_state", "child_life_losses",
                     "parent_links", "parent_link_codes", "parent_controls",
                     "learner_gamification", "xp_events", "streak_days", "streak_freezes", "achievements", "learner_achievements", "challenges",
                     "learner_challenges", "friend_requests", "friendships",
                     "tutor_conversations", "tutor_messages", "tutor_message_facts", "roleplay_sessions", "roleplay_turns", "roleplay_feedback",
                     "ai_recommendations", "ai_learning_insights", "ai_micro_lessons", "ai_micro_lesson_options", "ai_micro_lesson_attempts", "ai_evidence",
                     "adaptive_learning_events", "roleplay_turn_grades", "admin_audit_log",
                     "two_factor_credentials", "recovery_codes", "login_challenges", "mfa_failures", "security_events", "content_reviews"}


def old_signup(path, *, email, password, display_name, roles):
    """An account and a sign-in session as they existed BEFORE migration 0026 (no public_id or last_seen_at), written straight into the
    old schema: the service code is current and expects the current schema. Returns (user, raw token), like service.create_user."""
    from backend.auth import service
    user, _ = service.create_user(path, email=email, password=password, display_name=display_name, roles=roles, with_session=False)
    token, token_hash = service._new_token()
    now = service.utcnow()
    with connect(path) as conn:
        conn.execute("INSERT INTO sessions(user_id, token_hash, created_at, expires_at) VALUES (?, ?, ?, ?)",
                     (user.id, token_hash, service._fmt(now), service._fmt(now + service.timedelta(days=7))))
    return user, token


def tables(path):
    with connect(path) as conn:
        return {r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}


def test_migrations_apply_in_order(tmp_path):
    path = tmp_path / "t.db"
    applied = migrate(path)
    assert applied == [v for v, *_ in discover()]
    assert applied == sorted(applied)
    with connect(path) as conn:
        rows = conn.execute("SELECT version FROM schema_migrations ORDER BY version").fetchall()
    assert [r["version"] for r in rows] == applied


def test_schema_created(db_path):
    assert tables(db_path) == FOUNDATION_TABLES


def test_migrate_is_idempotent(db_path):
    with connect(db_path) as conn:
        before = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in FOUNDATION_TABLES}
    assert migrate(db_path) == []
    assert migrate(db_path) == []
    with connect(db_path) as conn:
        after = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in FOUNDATION_TABLES}
    assert before == after


def test_existing_legacy_database_is_preserved(tmp_path):
    """A buddy.db created by the pre-migration app keeps its state row."""
    path = tmp_path / "legacy.db"
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE state (user_id TEXT PRIMARY KEY, data TEXT NOT NULL, updated TEXT DEFAULT CURRENT_TIMESTAMP)")
    conn.execute("INSERT INTO state(user_id, data) VALUES ('demo-alex', '{\"xp\": 999}')")
    conn.commit()
    conn.close()
    migrate(path)
    with connect(path) as c:
        assert c.execute("SELECT data FROM state WHERE user_id='demo-alex'").fetchone()["data"] == '{"xp": 999}'
        assert c.execute("SELECT COUNT(*) FROM languages").fetchone()[0] > 0


def test_failed_migration_rolls_back(tmp_path):
    d = tmp_path / "m"
    d.mkdir()
    (d / "0001_ok.sql").write_text("CREATE TABLE a (id INTEGER PRIMARY KEY);")
    (d / "0002_bad.sql").write_text("CREATE TABLE b (id INTEGER PRIMARY KEY);\nINSERT INTO nope VALUES (1);")
    path = tmp_path / "t.db"
    with pytest.raises(MigrationError):
        migrate(path, d)
    assert tables(path) == {"a", "schema_migrations"}  # b rolled back, 0001 kept
    with connect(path) as conn:
        assert [r[0] for r in conn.execute("SELECT version FROM schema_migrations")] == ["0001"]


def test_modified_applied_migration_is_rejected(tmp_path):
    d = tmp_path / "m"
    d.mkdir()
    f = d / "0001_x.sql"
    f.write_text("CREATE TABLE a (id INTEGER PRIMARY KEY);")
    path = tmp_path / "t.db"
    migrate(path, d)
    f.write_text("CREATE TABLE a (id INTEGER PRIMARY KEY, extra TEXT);")
    with pytest.raises(MigrationError):
        migrate(path, d)


def test_upgrade_from_phase1_database_preserves_data(tmp_path):
    """A DB already at Phase 1 (migrations 0001-0002) upgrades in place, keeping users and legacy state."""
    import shutil
    from backend.db.migrate import MIGRATIONS_DIR

    phase1 = tmp_path / "phase1"
    phase1.mkdir()
    for f in ("0001_foundation_schema.sql", "0002_seed_foundation.sql"):
        shutil.copy(MIGRATIONS_DIR / f, phase1 / f)
    path = tmp_path / "t.db"
    assert migrate(path, phase1) == ["0001", "0002"]
    with connect(path) as conn:
        conn.execute("INSERT INTO state(user_id, data) VALUES ('demo-alex', '{\"xp\": 5}')")
        conn.execute("INSERT INTO users(handle, display_name) VALUES ('legacy-bob', 'Bob')")
    assert migrate(path) == [v for v, *_ in discover() if v > "0002"]
    with connect(path) as conn:
        assert conn.execute("SELECT data FROM state WHERE user_id='demo-alex'").fetchone()[0] == '{"xp": 5}'
        assert [r[0] for r in conn.execute("SELECT handle FROM users ORDER BY id")] == ["demo-alex", "legacy-bob"]
        assert conn.execute("SELECT COUNT(*) FROM users WHERE email IS NOT NULL").fetchone()[0] == 0


def test_upgrade_from_phase2_database_preserves_data(tmp_path):
    """A DB at Phase 2 (0001-0004) with real accounts and sessions upgrades in place."""
    import shutil
    from backend.auth import service
    from backend.db.migrate import MIGRATIONS_DIR

    phase2 = tmp_path / "phase2"
    phase2.mkdir()
    for f in sorted(MIGRATIONS_DIR.glob("000[1-4]_*.sql")):
        shutil.copy(f, phase2 / f.name)
    path = tmp_path / "t.db"
    assert migrate(path, phase2) == ["0001", "0002", "0003", "0004"]
    user, token = old_signup(path, email="a@example.com", password="correct horse battery", display_name="A", roles=["learner"])
    with connect(path) as conn:
        conn.execute("INSERT INTO state(user_id, data) VALUES ('demo-alex', '{\"xp\": 5}')")
    assert migrate(path) == [v for v, *_ in discover() if v > "0004"]
    assert service.authenticate(path, token).handle == user.handle  # existing login session survives
    with connect(path) as conn:
        assert conn.execute("SELECT data FROM state WHERE user_id='demo-alex'").fetchone()[0] == '{"xp": 5}'
        assert conn.execute("SELECT COUNT(*) FROM learner_profiles").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM language_levels WHERE language_id NOT IN (SELECT id FROM languages WHERE code IN ('mr', 'kn', 'ta', 'fr', 'bn', 'te', 'ur', 'ks', 'doi'))").fetchone()[0] == 6
        assert conn.execute("SELECT COUNT(*) FROM language_levels WHERE language_id = (SELECT id FROM languages WHERE code = 'kn')").fetchone()[0] == 3      # Kannada A1 (0037), A2 and B1 (0038)
        assert conn.execute("SELECT COUNT(*) FROM language_levels WHERE language_id = (SELECT id FROM languages WHERE code = 'ta')").fetchone()[0] == 3      # Tamil (0040, 0041)
        assert conn.execute("SELECT COUNT(*) FROM language_levels WHERE language_id = (SELECT id FROM languages WHERE code = 'fr')").fetchone()[0] == 1      # French A1 (0044)
        assert conn.execute("SELECT COUNT(*) FROM language_levels WHERE language_id = (SELECT id FROM languages WHERE code = 'mr')").fetchone()[0] == 3     # Marathi A1/A2 (0031) and B1 (0035)
        assert conn.execute("SELECT COUNT(*) FROM age_groups").fetchone()[0] == 3
    assert migrate(path) == []


def test_upgrade_from_phase3_database_preserves_data(tmp_path):
    """A DB at Phase 3 (0001-0006) with an account, a learner profile and demo state gains the curriculum in place."""
    import shutil
    from backend.auth import service
    from backend.db.migrate import MIGRATIONS_DIR
    from backend.learner import service as learner_service

    phase3 = tmp_path / "phase3"
    phase3.mkdir()
    for f in sorted(MIGRATIONS_DIR.glob("000[1-6]_*.sql")):
        shutil.copy(f, phase3 / f.name)
    path = tmp_path / "t.db"
    assert migrate(path, phase3) == ["0001", "0002", "0003", "0004", "0005", "0006"]
    user, token = old_signup(path, email="a@example.com", password="correct horse battery", display_name="A", roles=["learner"])
    learner_service.save_profile(path, user.id, native_language="en", target_language="hi", cefr_level="A1", date_of_birth="2000-01-01")
    with connect(path) as conn:
        conn.execute("INSERT INTO state(user_id, data) VALUES ('demo-alex', '{\"xp\": 5}')")
    assert migrate(path) == [v for v, *_ in discover() if v > "0006"]
    assert service.authenticate(path, token).handle == user.handle
    assert learner_service.get_profile(path, user.id)["target_language"] == "hi"
    with connect(path) as conn:
        assert conn.execute("SELECT data FROM state WHERE user_id='demo-alex'").fetchone()[0] == '{"xp": 5}'
        assert conn.execute("SELECT COUNT(*) FROM lessons WHERE language_id = (SELECT id FROM languages WHERE code = 'hi')").fetchone()[0] == 7
        assert conn.execute("SELECT COUNT(*) FROM lessons WHERE language_id != (SELECT id FROM languages WHERE code = 'hi')").fetchone()[0] == 150      # Marathi's 27, Kannada's 25, Tamil's 28 (0040-0045), French's 9 (0044), Bengali's 25 (0048, 0049), Telugu's 9 (0051), Urdu's 9 (0052), Kashmiri's 9 (0055), Dogri's 9 (0056)
        assert conn.execute("SELECT COUNT(*) FROM lesson_progress").fetchone()[0] == 0
    assert migrate(path) == []


def test_upgrade_from_phase5_database_preserves_data(tmp_path):
    """A DB at Phase 5 (0001-0012) with an account, profile, lesson attempts and demo state gains personalization in place."""
    import shutil
    from backend.auth import service
    from backend.db.migrate import MIGRATIONS_DIR
    from backend.learner import service as learner_service

    phase5 = tmp_path / "phase5"
    phase5.mkdir()
    for f in sorted(MIGRATIONS_DIR.glob("*.sql")):
        if f.name < "0013":
            shutil.copy(f, phase5 / f.name)
    path = tmp_path / "t.db"
    assert migrate(path, phase5) == [f"{i:04d}" for i in range(1, 13)]
    user, token = old_signup(path, email="a@example.com", password="correct horse battery", display_name="A", roles=["learner"])
    learner_service.save_profile(path, user.id, native_language="en", target_language="hi", cefr_level="A1", date_of_birth="2000-01-01")
    with connect(path) as conn:
        conn.execute("INSERT INTO state(user_id, data) VALUES ('demo-alex', '{\"xp\": 5}')")
        conn.execute("INSERT INTO exercise_attempts(user_id, exercise_id, submitted_text, is_correct, attempted_at) VALUES (?, 1, 'x', 0, '2026-01-01 00:00:00')", (user.id,))
        hindi_answers = "SELECT COUNT(*), SUM(is_correct) FROM exercise_answers a JOIN exercises e ON e.id = a.exercise_id WHERE e.language_id = (SELECT id FROM languages WHERE code = 'hi')"
        answers_before = conn.execute(hindi_answers).fetchone()[:]
        prompts_before = [r[0] for r in conn.execute("SELECT prompt FROM exercises ORDER BY id")]
    assert migrate(path) == [v for v, *_ in discover() if v > "0012"]
    assert service.authenticate(path, token).handle == user.handle
    with connect(path) as conn:
        assert conn.execute("SELECT data FROM state WHERE user_id='demo-alex'").fetchone()[0] == '{"xp": 5}'
        assert conn.execute("SELECT COUNT(*) FROM exercise_attempts").fetchone()[0] == 1
        assert conn.execute(hindi_answers).fetchone()[:] == answers_before   # the existing content is untouched (0031 only adds Marathi's)
        assert [r[0] for r in conn.execute("SELECT prompt FROM exercises WHERE language_id = (SELECT id FROM languages WHERE code = 'hi') ORDER BY id")] == prompts_before
        assert conn.execute("SELECT COUNT(*) FROM learner_attempts").fetchone()[0] == 1                               # the view sees old data
        assert conn.execute("SELECT COUNT(*) FROM confidence_scores").fetchone()[0] == 0
    assert migrate(path) == []


def test_upgrade_from_phase6_database_preserves_data_and_views(tmp_path):
    """A DB at Phase 6 (0001-0014) with a learner, lesson attempts and a weakness gains listening in place; the
    personalization views keep returning the old evidence and the demo state survives."""
    import shutil
    from backend.auth import service
    from backend.db.migrate import MIGRATIONS_DIR
    from backend.learner import service as learner_service

    phase6 = tmp_path / "phase6"
    phase6.mkdir()
    for f in sorted(MIGRATIONS_DIR.glob("*.sql")):
        if f.name < "0015":
            shutil.copy(f, phase6 / f.name)
    path = tmp_path / "t.db"
    assert migrate(path, phase6) == [f"{i:04d}" for i in range(1, 15)]
    user, token = old_signup(path, email="a@example.com", password="correct horse battery", display_name="A", roles=["learner"])
    learner_service.save_profile(path, user.id, native_language="en", target_language="hi", cefr_level="A1", date_of_birth="2000-01-01")
    with connect(path) as conn:
        conn.execute("INSERT INTO state(user_id, data) VALUES ('demo-alex', '{\"xp\": 5}')")
        conn.execute("INSERT INTO exercise_attempts(user_id, exercise_id, submitted_text, is_correct, attempted_at) VALUES (?, 1, 'x', 0, '2026-01-01 00:00:00')", (user.id,))
        conn.execute("INSERT INTO confidence_scores(user_id, language_id, topic_id, score, source, recorded_at) VALUES (?, (SELECT id FROM languages WHERE code='hi'), 1, 40, 'self_report', '2026-01-01 00:00:00')", (user.id,))
        before = [tuple(r) for r in conn.execute("SELECT source, attempt_id, user_id, language_id, item_id, difficulty, is_correct FROM learner_attempts")]
    assert migrate(path) == [v for v, *_ in discover() if v > "0014"]
    assert service.authenticate(path, token).handle == user.handle
    with connect(path) as conn:
        assert conn.execute("SELECT data FROM state WHERE user_id='demo-alex'").fetchone()[0] == '{"xp": 5}'
        assert [tuple(r) for r in conn.execute("SELECT source, attempt_id, user_id, language_id, item_id, difficulty, is_correct FROM learner_attempts")] == before
        assert conn.execute("SELECT COUNT(*) FROM confidence_scores").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM listening_activities WHERE language_id = (SELECT id FROM languages WHERE code = 'hi')").fetchone()[0] == 15   # the Hindi seed (Marathi's: 0033)
        assert conn.execute("SELECT COUNT(*) FROM listening_attempts").fetchone()[0] == 0
    assert migrate(path) == []


def test_upgrade_from_phase7a_database_preserves_listening_data(tmp_path):
    """A DB at Phase 7A (0001-0017) with a learner's listening session and attempt gains speaking in place; the listening
    data, the views and the demo state survive, and the new tables start empty."""
    import shutil
    from backend.auth import service
    from backend.db.migrate import MIGRATIONS_DIR
    from backend.learner import service as learner_service

    phase7a = tmp_path / "phase7a"
    phase7a.mkdir()
    for f in sorted(MIGRATIONS_DIR.glob("*.sql")):
        if f.name < "0018":
            shutil.copy(f, phase7a / f.name)
    path = tmp_path / "t.db"
    assert migrate(path, phase7a) == [f"{i:04d}" for i in range(1, 18)]
    user, token = old_signup(path, email="a@example.com", password="correct horse battery", display_name="A", roles=["learner"])
    learner_service.save_profile(path, user.id, native_language="en", target_language="hi", cefr_level="A1", date_of_birth="2000-01-01")
    with connect(path) as conn:
        conn.execute("INSERT INTO state(user_id, data) VALUES ('demo-alex', '{\"xp\": 5}')")
        hi = conn.execute("SELECT id FROM languages WHERE code='hi'").fetchone()[0]
        sid = conn.execute("INSERT INTO audio_sessions(user_id, language_id, kind, status, started_at, ended_at, duration_ms) VALUES (?, ?, 'listening', 'completed', '2026-01-01 00:00:00', '2026-01-01 00:00:05', 5000)", (user.id, hi)).lastrowid
        conn.execute("INSERT INTO listening_attempts(user_id, session_id, activity_id, option_id, is_correct, plays, attempted_at) VALUES (?, ?, 1, (SELECT id FROM listening_options WHERE activity_id=1 LIMIT 1), 0, 1, '2026-01-01 00:00:05')", (user.id, sid))
        before = [tuple(r) for r in conn.execute("SELECT source, attempt_id, user_id, is_correct FROM learner_attempts")]
    assert migrate(path) == [v for v, *_ in discover() if v > "0017"]
    assert service.authenticate(path, token).handle == user.handle
    with connect(path) as conn:
        assert conn.execute("SELECT data FROM state WHERE user_id='demo-alex'").fetchone()[0] == '{"xp": 5}'
        assert conn.execute("SELECT kind, status FROM audio_sessions").fetchone()[:] == ("listening", "completed")   # the existing session is untouched
        assert [tuple(r) for r in conn.execute("SELECT source, attempt_id, user_id, is_correct FROM learner_attempts")] == before
        for t in ("speaking_sessions", "stt_runs", "speaking_transcripts"):
            assert conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] == 0
    assert migrate(path) == []


def test_upgrade_from_phase7b_database_preserves_speaking_data(tmp_path):
    """A DB at Phase 7B (0001-0018) with a completed speaking session and transcript gains pronunciation assessment in place;
    the speaking data and the demo state survive and the new tables start empty."""
    import shutil
    from backend.auth import service
    from backend.db.migrate import MIGRATIONS_DIR
    from backend.learner import service as learner_service

    phase7b = tmp_path / "phase7b"
    phase7b.mkdir()
    for f in sorted(MIGRATIONS_DIR.glob("*.sql")):
        if f.name < "0019":
            shutil.copy(f, phase7b / f.name)
    path = tmp_path / "t.db"
    assert migrate(path, phase7b) == [f"{i:04d}" for i in range(1, 19)]
    user, token = old_signup(path, email="a@example.com", password="correct horse battery", display_name="A", roles=["learner"])
    learner_service.save_profile(path, user.id, native_language="en", target_language="hi", cefr_level="A1", date_of_birth="2000-01-01")
    with connect(path) as conn:
        conn.execute("INSERT INTO state(user_id, data) VALUES ('demo-alex', '{\"xp\": 5}')")
        hi = conn.execute("SELECT id FROM languages WHERE code='hi'").fetchone()[0]
        item = conn.execute("SELECT id FROM vocabulary_items WHERE kind='phrase' LIMIT 1").fetchone()[0]
        sid = conn.execute("INSERT INTO audio_sessions(user_id, language_id, kind, status, started_at, ended_at, duration_ms) VALUES (?, ?, 'speaking', 'completed', '2026-01-01 00:00:00', '2026-01-01 00:00:09', 2000)", (user.id, hi)).lastrowid
        conn.execute("INSERT INTO speaking_sessions(session_id, user_id, language_id, item_id, locale, stage, created_at, updated_at) VALUES (?, ?, ?, ?, 'hi-IN', 'cancelled', 't', 't')", (sid, user.id, hi, item))
        conn.execute("UPDATE speaking_sessions SET stage='created' WHERE session_id=?", (sid,))
    assert migrate(path) == ["0019", "0020", "0021", "0022", "0023", "0024", "0025", "0026", "0027", "0028", "0029", "0030", "0031", "0032", "0033", "0034", "0035", "0036", "0037", "0038", "0039", "0040", "0041", "0042", "0043", "0044", "0045", "0046", "0047", "0048", "0049", "0050", "0051", "0052", "0053", "0054", "0055", "0056"]
    assert service.authenticate(path, token).handle == user.handle
    with connect(path) as conn:
        assert conn.execute("SELECT data FROM state WHERE user_id='demo-alex'").fetchone()[0] == '{"xp": 5}'
        assert conn.execute("SELECT COUNT(*) FROM speaking_sessions").fetchone()[0] == 1
        for t in ("pronunciation_assessments", "pronunciation_components", "pronunciation_word_scores"):
            assert conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM learner_pronunciation_evidence").fetchone()[0] == 0
    assert migrate(path) == []


def test_upgrade_from_phase7c_database_preserves_learner_data(tmp_path):
    """A DB at Phase 7C (0001-0019) with a learner who has a listening attempt gains age targeting and child game state in place:
    the attempt survives, the college content is restricted to teen and adult, and the new state tables start empty."""
    import shutil
    from backend.auth import service
    from backend.db.migrate import MIGRATIONS_DIR
    from backend.learner import service as learner_service

    phase7c = tmp_path / "phase7c"
    phase7c.mkdir()
    for f in sorted(MIGRATIONS_DIR.glob("*.sql")):
        if f.name < "0020":
            shutil.copy(f, phase7c / f.name)
    path = tmp_path / "t.db"
    assert migrate(path, phase7c) == [f"{i:04d}" for i in range(1, 20)]
    user, token = old_signup(path, email="a@example.com", password="correct horse battery", display_name="A", roles=["learner"])
    learner_service.save_profile(path, user.id, native_language="en", target_language="hi", cefr_level="A1", date_of_birth="2000-01-01")
    with connect(path) as conn:
        act = conn.execute("SELECT id, language_id FROM listening_activities ORDER BY id LIMIT 1").fetchone()
        opt = conn.execute("SELECT id FROM listening_options WHERE activity_id = ?", (act["id"],)).fetchone()[0]
        sid = conn.execute("INSERT INTO audio_sessions(user_id, language_id, kind, status, started_at, ended_at, duration_ms) VALUES (?, ?, 'listening', 'completed', 't', 't', 1)", (user.id, act["language_id"])).lastrowid
        conn.execute("INSERT INTO listening_attempts(user_id, session_id, activity_id, option_id, is_correct, plays, attempted_at) VALUES (?, ?, ?, ?, 0, 1, 't')", (user.id, sid, act["id"], opt))
    assert migrate(path) == ["0020", "0021", "0022", "0023", "0024", "0025", "0026", "0027", "0028", "0029", "0030", "0031", "0032", "0033", "0034", "0035", "0036", "0037", "0038", "0039", "0040", "0041", "0042", "0043", "0044", "0045", "0046", "0047", "0048", "0049", "0050", "0051", "0052", "0053", "0054", "0055", "0056"]
    assert service.authenticate(path, token).handle == user.handle
    with connect(path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM listening_attempts").fetchone()[0] == 1
        for t in ("child_game_state", "child_life_losses"):
            assert conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] == 0
        groups = {r[0] for r in conn.execute("SELECT g.code FROM lesson_age_groups x JOIN age_groups g ON g.id = x.age_group_id")}
        assert groups == {"teen", "adult"}
    assert migrate(path) == []


def test_upgrade_from_phase8_database_preserves_learner_data(tmp_path):
    """A DB at Phase 8 (0001-0020) with a child's lives and a parent account gains the parent portal in place: nothing is lost, the
    new tables start empty, and the parent can then link."""
    import shutil
    from backend.auth import service
    from backend.db.migrate import MIGRATIONS_DIR
    from backend.learner import service as learner_service

    phase8 = tmp_path / "phase8"
    phase8.mkdir()
    for f in sorted(MIGRATIONS_DIR.glob("*.sql")):
        if f.name < "0021":
            shutil.copy(f, phase8 / f.name)
    path = tmp_path / "t.db"
    assert migrate(path, phase8) == [f"{i:04d}" for i in range(1, 21)]
    kid, _ = old_signup(path, email="k@example.com", password="correct horse battery", display_name="K", roles=["learner"])
    parent, token = old_signup(path, email="p@example.com", password="correct horse battery", display_name="P", roles=["parent"])
    learner_service.save_profile(path, kid.id, native_language="en", target_language="hi", cefr_level="A1", date_of_birth="2018-01-01")
    with connect(path) as conn:
        conn.execute("INSERT INTO child_game_state(user_id, lives, lives_updated_at, created_at) VALUES (?, 3, 't', 't')", (kid.id,))
    assert migrate(path) == ["0021", "0022", "0023", "0024", "0025", "0026", "0027", "0028", "0029", "0030", "0031", "0032", "0033", "0034", "0035", "0036", "0037", "0038", "0039", "0040", "0041", "0042", "0043", "0044", "0045", "0046", "0047", "0048", "0049", "0050", "0051", "0052", "0053", "0054", "0055", "0056"]
    assert service.authenticate(path, token).handle == parent.handle
    with connect(path) as conn:
        assert conn.execute("SELECT lives FROM child_game_state WHERE user_id = ?", (kid.id,)).fetchone()[0] == 3
        for t in ("parent_links", "parent_link_codes", "parent_controls"):
            assert conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] == 0
    from backend.parent import service as parent_service
    code = parent_service.issue_code(path, kid.id)["code"]
    assert parent_service.link_with_code(path, parent.id, code)["display_name"] == "K"
    assert migrate(path) == []


def test_upgrade_from_phase9_database_preserves_data_and_starts_gamification_empty(tmp_path):
    """A DB at Phase 9 (0001-0021) with a learner, a listening attempt and a parent link gains gamification and friends in place:
    nothing is lost, the new ledgers start empty, the seeded achievements and challenges exist, and XP is then credited from the
    attempt that was already there."""
    import shutil
    from backend.auth import service
    from backend.db.migrate import MIGRATIONS_DIR
    from backend.gamification import service as gamification
    from backend.learner import service as learner_service
    from backend.parent import service as parent_service

    phase9 = tmp_path / "phase9"
    phase9.mkdir()
    for f in sorted(MIGRATIONS_DIR.glob("*.sql")):
        if f.name < "0022":
            shutil.copy(f, phase9 / f.name)
    path = tmp_path / "t.db"
    assert migrate(path, phase9) == [f"{i:04d}" for i in range(1, 22)]
    kid, token = old_signup(path, email="k@example.com", password="correct horse battery", display_name="K", roles=["learner"])
    parent, _ = old_signup(path, email="p@example.com", password="correct horse battery", display_name="P", roles=["parent"])
    learner_service.save_profile(path, kid.id, native_language="en", target_language="hi", cefr_level="A1", date_of_birth="2010-01-01")
    parent_service.link_with_code(path, parent.id, parent_service.issue_code(path, kid.id)["code"])
    with connect(path) as conn:
        act = conn.execute("SELECT a.id, a.language_id, o.id AS opt FROM listening_activities a JOIN listening_options o ON o.activity_id = a.id AND o.item_id = a.item_id LIMIT 1").fetchone()
        sid = conn.execute("INSERT INTO audio_sessions(user_id, language_id, kind, status, started_at, ended_at, duration_ms) VALUES (?, ?, 'listening', 'completed', 't', 't', 1)", (kid.id, act["language_id"])).lastrowid
        conn.execute("INSERT INTO listening_attempts(user_id, session_id, activity_id, option_id, is_correct, plays, attempted_at) VALUES (?, ?, ?, ?, 1, 1, '2026-09-01 09:00:00')", (kid.id, sid, act["id"], act["opt"]))
    assert migrate(path) == ["0022", "0023", "0024", "0025", "0026", "0027", "0028", "0029", "0030", "0031", "0032", "0033", "0034", "0035", "0036", "0037", "0038", "0039", "0040", "0041", "0042", "0043", "0044", "0045", "0046", "0047", "0048", "0049", "0050", "0051", "0052", "0053", "0054", "0055", "0056"]
    assert service.authenticate(path, token).handle == kid.handle
    with connect(path) as conn:
        for t in ("xp_events", "streak_days", "streak_freezes", "learner_achievements", "learner_challenges", "friend_requests", "friendships", "learner_gamification"):
            assert conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM parent_links").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM listening_attempts").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM achievements").fetchone()[0] >= 5 and conn.execute("SELECT COUNT(*) FROM challenges").fetchone()[0] >= 5
    assert gamification.summary(path, kid.id)["xp"]["total"] == 5          # the old attempt is rewarded, once
    assert gamification.summary(path, kid.id)["xp"]["total"] == 5
    assert migrate(path) == []


def test_upgrade_from_phase10_database_preserves_data_and_starts_ai_tables_empty(tmp_path):
    """A DB at Phase 10 (0001-0022) with a learner, XP and a friendship gains tutor and roleplay tables in place: nothing is lost, the
    new tables start empty, and a roleplay can then be run and rewarded through the existing ledger."""
    import shutil
    from backend.auth import service
    from backend.db.migrate import MIGRATIONS_DIR
    from backend.gamification import service as gamification
    from backend.learner import service as learner_service
    from backend.roleplay import service as roleplay
    from backend.tutor import service as tutor

    phase10 = tmp_path / "phase10"
    phase10.mkdir()
    for f in sorted(MIGRATIONS_DIR.glob("*.sql")):
        if f.name < "0023":
            shutil.copy(f, phase10 / f.name)
    path = tmp_path / "t.db"
    assert migrate(path, phase10) == [f"{i:04d}" for i in range(1, 23)]
    a, token = old_signup(path, email="a@example.com", password="correct horse battery", display_name="A", roles=["learner"])
    b, _ = old_signup(path, email="b@example.com", password="correct horse battery", display_name="B", roles=["learner"])
    for u in (a, b):
        learner_service.save_profile(path, u.id, native_language="en", target_language="hi", cefr_level="A1", date_of_birth="2010-01-01")
    with connect(path) as conn:
        conn.execute("INSERT INTO friendships(user_low, user_high, created_at) VALUES (?, ?, 't')", (a.id, b.id))
        conn.execute("INSERT INTO lesson_progress(user_id, lesson_id, started_at, completed_at) VALUES (?, 1, '2026-09-01 08:00:00', '2026-09-01 09:00:00')", (a.id,))
    assert migrate(path) == ["0023", "0024", "0025", "0026", "0027", "0028", "0029", "0030", "0031", "0032", "0033", "0034", "0035", "0036", "0037", "0038", "0039", "0040", "0041", "0042", "0043", "0044", "0045", "0046", "0047", "0048", "0049", "0050", "0051", "0052", "0053", "0054", "0055", "0056"]
    assert service.authenticate(path, token).handle == a.handle
    with connect(path) as conn:
        for t in ("tutor_conversations", "tutor_messages", "tutor_message_facts", "roleplay_sessions", "roleplay_turns", "roleplay_feedback"):
            assert conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM friendships").fetchone()[0] == 1 and conn.execute("SELECT COUNT(*) FROM xp_events").fetchone()[0] == 0
    assert gamification.summary(path, a.id)["xp"]["total"] == 20                # the old lesson is credited once the gamification code runs on the new schema
    assert gamification.summary(path, a.id)["xp"]["total"] == 20
    cid = tutor.create_conversation(path, a.id)["conversation"]["id"]
    assert tutor.send_message(path, a.id, cid, message="hello")["reply"]["provider"] == "mock"
    with connect(path) as conn:
        sit = conn.execute("SELECT id FROM situations WHERE slug = 'emergency' AND language_id = (SELECT id FROM languages WHERE code='hi')").fetchone()[0]
    session = roleplay.start(path, a.id, sit)[0]["session"]
    assert session["progress"]["steps_total"] == 7
    assert migrate(path) == []


def test_upgrade_from_phase11_database_preserves_data_and_starts_adaptive_tables_empty(tmp_path):
    """A DB at Phase 11 (0001-0023) with a learner, a tutor conversation and a completed roleplay gains the adaptive AI tables in place: nothing is
    lost, the new tables start empty, and the old roleplay turns simply have no grades (the adaptive layer works from stored evidence)."""
    import shutil
    from backend.auth import service
    from backend.db.migrate import MIGRATIONS_DIR
    from backend.learner import service as learner_service
    from backend.roleplay import service as roleplay
    from backend.tutor import service as tutor
    from backend.adaptive import service as adaptive

    phase11 = tmp_path / "phase11"
    phase11.mkdir()
    for f in sorted(MIGRATIONS_DIR.glob("*.sql")):
        if f.name < "0024":
            shutil.copy(f, phase11 / f.name)
    path = tmp_path / "t.db"
    assert migrate(path, phase11) == [f"{i:04d}" for i in range(1, 24)]
    a, token = old_signup(path, email="a@example.com", password="correct horse battery", display_name="A", roles=["learner"])
    learner_service.save_profile(path, a.id, native_language="en", target_language="hi", cefr_level="A1", date_of_birth="2010-01-01")
    with connect(path) as conn:
        conn.execute("INSERT INTO lesson_progress(user_id, lesson_id, started_at, completed_at) VALUES (?, 1, '2026-09-01 08:00:00', '2026-09-01 09:00:00')", (a.id,))
        sit = conn.execute("SELECT id FROM situations WHERE slug = 'emergency' AND language_id = (SELECT id FROM languages WHERE code='hi')").fetchone()[0]
    from backend.repositories import roleplay as rp_repo, tutor as tutor_repo       # Phase 11 data, written with the Phase 11 repositories (the new code needs the new schema)
    with connect(path) as conn:
        lang = conn.execute("SELECT id FROM languages WHERE code = 'hi'").fetchone()[0]
        cid = tutor_repo.create_conversation(conn, a.id, lang, "A1", "teen", None, None, None, "Chat", "2026-09-01 09:00:00")
        tutor_repo.insert_message(conn, cid, a.id, 1, "learner", "hello", None, None, None, "2026-09-01 09:00:00")
        tutor_repo.insert_message(conn, cid, a.id, 2, "tutor", "hi", None, None, "mock", "2026-09-01 09:00:00")
        sid = rp_repo.create_session(conn, a.id, sit, lang, "A1", "teen", 7, "2026-09-01 09:00:00")
    assert migrate(path) == ["0024", "0025", "0026", "0027", "0028", "0029", "0030", "0031", "0032", "0033", "0034", "0035", "0036", "0037", "0038", "0039", "0040", "0041", "0042", "0043", "0044", "0045", "0046", "0047", "0048", "0049", "0050", "0051", "0052", "0053", "0054", "0055", "0056"]
    assert service.authenticate(path, token).handle == a.handle
    with connect(path) as conn:
        for t in ("ai_recommendations", "ai_learning_insights", "ai_micro_lessons", "ai_micro_lesson_options", "ai_micro_lesson_attempts", "ai_evidence", "adaptive_learning_events", "roleplay_turn_grades"):
            assert conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM tutor_messages").fetchone()[0] == 2 and conn.execute("SELECT COUNT(*) FROM roleplay_sessions").fetchone()[0] == 1
    out = adaptive.recommendations(path, a.id)
    assert out["mode"] == "teen" and out["date"]
    assert roleplay.get(path, a.id, sid)["session"]["progress"]["steps_total"] == 7
    assert migrate(path) == []
