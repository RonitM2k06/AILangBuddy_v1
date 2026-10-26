"""Phase 14D: migration 0027_two_factor.sql. New tables only; existing users, sessions and admins are untouched (nobody has 2FA until they
set it up); the single-use and immutability rules are enforced by the schema. Every database is a temp file: buddy.db is never opened."""
import shutil
import sqlite3

import pytest

from backend.auth import service
from backend.db import connect
from backend.db.migrate import MIGRATIONS_DIR, migrate

NEW_TABLES = {"two_factor_credentials", "recovery_codes", "login_challenges", "mfa_failures"}


@pytest.fixture
def through_0027(tmp_path):
    d = tmp_path / "phase14d"
    d.mkdir()
    for f in sorted(MIGRATIONS_DIR.glob("*.sql")):
        if f.name < "0028":
            shutil.copy(f, d / f.name)
    return d


@pytest.fixture
def through_0026(tmp_path):
    d = tmp_path / "phase14c"
    d.mkdir()
    for f in sorted(MIGRATIONS_DIR.glob("*.sql")):
        if f.name < "0027":
            shutil.copy(f, d / f.name)
    return d


def tables(path):
    return {r[0] for r in sqlite3.connect(path).execute("SELECT name FROM sqlite_master WHERE type = 'table'")}


def test_0027_is_14d_s_only_migration_and_applies_cleanly_and_idempotently(tmp_path):
    versions = [f.name.split("_")[0] for f in sorted(MIGRATIONS_DIR.glob("*.sql"))]
    assert versions[26] == "0027" and versions.count("0027") == 1 and versions[27:] == ["0028", "0029", "0030", "0031", "0032", "0033", "0034", "0035", "0036", "0037", "0038", "0039", "0040", "0041", "0042", "0043", "0044", "0045", "0046", "0047", "0048", "0049", "0050", "0051", "0052", "0053", "0054", "0055", "0056"]   # 0028: Phase 14E (security events); 0029-0056: city packs
    path = tmp_path / "fresh.db"
    assert migrate(path)[-30:] == ["0027", "0028", "0029", "0030", "0031", "0032", "0033", "0034", "0035", "0036", "0037", "0038", "0039", "0040", "0041", "0042", "0043", "0044", "0045", "0046", "0047", "0048", "0049", "0050", "0051", "0052", "0053", "0054", "0055", "0056"] and migrate(path) == []
    assert NEW_TABLES <= tables(path)
    with connect(path) as conn:
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok" and not conn.execute("PRAGMA foreign_key_check").fetchall()


def test_the_upgrade_adds_only_the_new_tables_and_keeps_users_sessions_and_admins(tmp_path, through_0026, through_0027):
    path = tmp_path / "t.db"
    migrate(path, through_0026)
    before_tables = tables(path)
    learner, token = service.create_user(path, email="l@example.com", password="correct horse battery", display_name="L", roles=["learner"])
    admin, admin_token = service.create_user(path, email="a@example.com", password="correct horse battery", display_name="A", roles=["admin"])
    with connect(path) as conn:
        sessions_before = [tuple(r) for r in conn.execute("SELECT * FROM sessions ORDER BY id")]
        users_before = [tuple(r) for r in conn.execute("SELECT * FROM users ORDER BY id")]
    assert migrate(path, through_0027) == ["0027"]
    assert tables(path) - before_tables == NEW_TABLES and not before_tables - tables(path)
    with connect(path) as conn:
        assert [tuple(r) for r in conn.execute("SELECT * FROM sessions ORDER BY id")] == sessions_before
        assert [tuple(r) for r in conn.execute("SELECT * FROM users ORDER BY id")] == users_before
        assert all(conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] == 0 for t in NEW_TABLES)
    assert service.authenticate(path, token).mfa_level == 0 and service.authenticate(path, admin_token).mfa_level == 0   # sessions keep their level
    assert migrate(path) == ["0028", "0029", "0030", "0031", "0032", "0033", "0034", "0035", "0036", "0037", "0038", "0039", "0040", "0041", "0042", "0043", "0044", "0045", "0046", "0047", "0048", "0049", "0050", "0051", "0052", "0053", "0054", "0055", "0056"]                                 # the rest of the chain, as a real upgrade would apply it
    user, fresh = service.login(path, email="l@example.com", password="correct horse battery")                          # no 2FA yet: password sign-in
    assert fresh and user.mfa_level == 0


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "t.db"
    migrate(path)
    a, _ = service.create_user(path, email="a@example.com", password="correct horse battery", display_name="A", roles=["learner"], with_session=False)
    b, _ = service.create_user(path, email="b@example.com", password="correct horse battery", display_name="B", roles=["learner"], with_session=False)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON")
    yield conn, a.id, b.id
    conn.close()


def cred(conn, uid, **over):
    row = {"user_id": uid, "secret_ciphertext": b"c" * 36, "secret_nonce": b"n" * 12, "status": "pending", "created_at": "2026-10-01 00:00:00",
           "setup_expires_at": "2026-10-01 00:10:00", "enabled_at": None, "last_used_step": None, **over}
    conn.execute(f"INSERT INTO two_factor_credentials({', '.join(row)}) VALUES ({', '.join('?' * len(row))})", tuple(row.values()))


ENABLED = {"status": "enabled", "setup_expires_at": None, "enabled_at": "2026-10-01 00:05:00", "last_used_step": 100}


@pytest.mark.parametrize("over", [{"secret_ciphertext": "plaintext-secret-here-is-36-chars!!!"}, {"secret_ciphertext": b"c" * 20},
                                  {"secret_nonce": b"n" * 11}, {"secret_nonce": b"n" * 16}, {"status": "on"}, {"setup_expires_at": None},
                                  {"status": "enabled", "enabled_at": None, "setup_expires_at": None}, {**ENABLED, "setup_expires_at": "2026-10-01 00:10:00"},
                                  {"last_used_step": -1}, {"user_id": 999}, {"setup_expires_at": "2026-09-30 00:00:00"}])
def test_a_malformed_credential_is_refused(db, over):
    conn, a, _ = db
    with pytest.raises(sqlite3.IntegrityError):
        cred(conn, a, **over)


def test_one_credential_per_user(db):
    conn, a, _ = db
    cred(conn, a)
    with pytest.raises(sqlite3.IntegrityError):
        cred(conn, a)


@pytest.mark.parametrize("change", ["secret_ciphertext = randomblob(36)", "secret_nonce = randomblob(12)", "status = 'pending', setup_expires_at = '2026-10-02 00:00:00', enabled_at = NULL",
                                    "enabled_at = '2026-10-02 00:00:00'", "last_used_step = 100", "last_used_step = 99", "last_used_step = NULL"])
def test_an_enabled_credential_cannot_be_edited_and_its_step_only_moves_forward(db, change):
    conn, a, _ = db
    cred(conn, a, **ENABLED)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(f"UPDATE two_factor_credentials SET {change}")


def test_using_a_later_step_and_removing_the_credential_are_allowed(db):
    conn, a, _ = db
    cred(conn, a, **ENABLED)
    conn.execute("UPDATE two_factor_credentials SET last_used_step = 101")
    conn.execute("DELETE FROM two_factor_credentials")
    assert conn.execute("SELECT COUNT(*) FROM two_factor_credentials").fetchone()[0] == 0


def code(conn, uid, h="a" * 64, used=None):
    conn.execute("INSERT INTO recovery_codes(user_id, code_hash, created_at, used_at) VALUES (?, ?, '2026-10-01 00:00:00', ?)", (uid, h, used))


@pytest.mark.parametrize("h", ["A" * 64, "a" * 63, "plain-text-recovery-code", "g" * 64])
def test_recovery_codes_are_stored_as_hashes_only(db, h):
    conn, a, _ = db
    with pytest.raises(sqlite3.IntegrityError):
        code(conn, a, h)


@pytest.mark.parametrize("change", ["used_at = NULL", "used_at = '2026-10-03 00:00:00'", "user_id = (SELECT MAX(id) FROM users)", "code_hash = '" + "b" * 64 + "'"])
def test_a_spent_recovery_code_stays_spent_and_never_changes_hands(db, change):
    conn, a, _ = db
    code(conn, a, used="2026-10-02 00:00:00")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(f"UPDATE recovery_codes SET {change}")


def test_an_unspent_code_cannot_move_to_another_user(db):
    conn, a, b = db
    code(conn, a)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("UPDATE recovery_codes SET user_id = ?", (b,))
    with pytest.raises(sqlite3.IntegrityError):
        code(conn, b)                                                        # the same hash twice


def challenge(conn, uid, **over):
    row = {"user_id": uid, "token_hash": "c" * 64, "created_at": "2026-10-01 00:00:00", "expires_at": "2026-10-01 00:05:00", **over}
    conn.execute(f"INSERT INTO login_challenges({', '.join(row)}) VALUES ({', '.join('?' * len(row))})", tuple(row.values()))


@pytest.mark.parametrize("over", [{"token_hash": "raw-token"}, {"expires_at": "2026-09-30 00:00:00"}, {"attempts": 6}, {"attempts": -1},
                                  {"completed_at": "2026-09-30 00:00:00"}])
def test_a_malformed_challenge_is_refused(db, over):
    conn, a, _ = db
    with pytest.raises(sqlite3.IntegrityError):
        challenge(conn, a, **over)


@pytest.mark.parametrize("change", ["user_id = (SELECT MAX(id) FROM users)", "token_hash = '" + "d" * 64 + "'", "expires_at = '2099-01-01 00:00:00'",
                                    "created_at = '2026-10-01 00:01:00'", "attempts = 0"])
def test_a_challenge_belongs_to_one_user_for_one_lifetime(db, change):
    conn, a, _ = db
    challenge(conn, a, attempts=2)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(f"UPDATE login_challenges SET {change}")


def test_a_challenge_is_completed_once(db):
    conn, a, _ = db
    challenge(conn, a)
    conn.execute("UPDATE login_challenges SET attempts = 3")
    conn.execute("UPDATE login_challenges SET completed_at = '2026-10-01 00:02:00'")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("UPDATE login_challenges SET completed_at = '2026-10-01 00:03:00'")


def test_failures_have_a_known_kind_and_everything_cascades_with_the_user(db):
    conn, a, _ = db
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO mfa_failures(user_id, kind, occurred_at) VALUES (?, 'guess', '2026-10-01 00:00:00')", (a,))
    cred(conn, a, **ENABLED)
    code(conn, a)
    challenge(conn, a)
    conn.execute("INSERT INTO mfa_failures(user_id, kind, occurred_at) VALUES (?, 'verify', '2026-10-01 00:00:00')", (a,))
    conn.execute("DELETE FROM users WHERE id = ?", (a,))
    assert all(conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] == 0 for t in NEW_TABLES)
