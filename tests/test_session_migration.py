"""Phase 14C: migration 0026_session_hardening.sql. Additive on `sessions` only; existing sessions keep working; the rules ALTER TABLE
cannot express are enforced by triggers. Every database here is a temp file: the real buddy.db is never opened."""
import shutil
import sqlite3
from datetime import timedelta

import pytest

from backend.auth import service
from backend.db import connect
from backend.db.migrate import MIGRATIONS_DIR, migrate


def one(conn, sql, args=()):
    return conn.execute(sql, args).fetchone()[0]


@pytest.fixture
def through_0026(tmp_path):
    d = tmp_path / "phase14c"
    d.mkdir()
    for f in sorted(MIGRATIONS_DIR.glob("*.sql")):
        if f.name < "0027":
            shutil.copy(f, d / f.name)
    return d


@pytest.fixture
def before_0026(tmp_path):
    d = tmp_path / "phase14b"
    d.mkdir()
    for f in sorted(MIGRATIONS_DIR.glob("*.sql")):
        if f.name < "0026":
            shutil.copy(f, d / f.name)
    return d


def old_session(path, email, created):
    """An account and a session written in the pre-0026 shape."""
    user, _ = service.create_user(path, email=email, password="correct horse battery", display_name="A", roles=["learner"], with_session=False)
    raw, token_hash = service._new_token()
    with connect(path) as conn:
        conn.execute("INSERT INTO sessions(user_id, token_hash, created_at, expires_at) VALUES (?, ?, ?, ?)",
                     (user.id, token_hash, service._fmt(created), service._fmt(created + timedelta(days=7))))
    return user, raw


def test_0026_is_14c_s_only_migration_and_applies_cleanly_and_idempotently(tmp_path):
    versions = [f.name.split("_")[0] for f in sorted(MIGRATIONS_DIR.glob("*.sql"))]
    assert versions[25] == "0026" and versions.count("0026") == 1 and versions[26:] == ["0027", "0028", "0029", "0030", "0031", "0032", "0033", "0034", "0035", "0036", "0037", "0038", "0039", "0040", "0041", "0042", "0043", "0044", "0045", "0046", "0047", "0048", "0049", "0050", "0051", "0052", "0053", "0054", "0055", "0056"]   # 0027/0028: Phase 14D/E; 0029-0056: city packs
    path = tmp_path / "fresh.db"
    assert migrate(path)[-31:] == ["0026", "0027", "0028", "0029", "0030", "0031", "0032", "0033", "0034", "0035", "0036", "0037", "0038", "0039", "0040", "0041", "0042", "0043", "0044", "0045", "0046", "0047", "0048", "0049", "0050", "0051", "0052", "0053", "0054", "0055", "0056"]
    assert migrate(path) == []
    with connect(path) as conn:
        cols = {r["name"]: r for r in conn.execute("PRAGMA table_info(sessions)")}
        assert {"public_id", "last_seen_at", "auth_method", "mfa_level"} <= set(cols)
        assert one(conn, "PRAGMA integrity_check") == "ok" and not conn.execute("PRAGMA foreign_key_check").fetchall()


def test_only_the_sessions_table_changes(tmp_path, before_0026, through_0026):
    old, new = tmp_path / "old.db", tmp_path / "new.db"
    migrate(old, before_0026)
    migrate(new, through_0026)
    schema = lambda p: {(r[0], r[1]): r[2] for r in sqlite3.connect(p).execute("SELECT type, name, sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'")}
    a, b = schema(old), schema(new)
    changed = {k for k in a if a[k] != b.get(k)} | (set(b) - set(a))
    assert changed == {("table", "sessions"), ("index", "idx_sessions_public_id"), ("index", "idx_sessions_user_last_seen"),
                       ("trigger", "sessions_new_row_is_complete"), ("trigger", "sessions_identity_is_fixed")}
    assert not set(a) - set(b)


def test_existing_sessions_survive_the_upgrade_and_are_backfilled(tmp_path, before_0026):
    path = tmp_path / "t.db"
    migrate(path, before_0026)
    now = service.utcnow().replace(microsecond=0)
    users = [old_session(path, f"u{i}@example.com", now - timedelta(minutes=i)) for i in range(5)]
    with connect(path) as conn:
        before = [tuple(r) for r in conn.execute("SELECT id, user_id, token_hash, created_at, expires_at FROM sessions ORDER BY id")]
    assert migrate(path) == ["0026", "0027", "0028", "0029", "0030", "0031", "0032", "0033", "0034", "0035", "0036", "0037", "0038", "0039", "0040", "0041", "0042", "0043", "0044", "0045", "0046", "0047", "0048", "0049", "0050", "0051", "0052", "0053", "0054", "0055", "0056"]
    with connect(path) as conn:
        rows = [dict(r) for r in conn.execute("SELECT * FROM sessions ORDER BY id")]
    assert [(r["id"], r["user_id"], r["token_hash"], r["created_at"], r["expires_at"]) for r in rows] == before   # nothing else changed
    assert len({r["public_id"] for r in rows}) == 5 and all(len(r["public_id"]) == 32 and set(r["public_id"]) <= set("0123456789abcdef") for r in rows)
    assert all(r["last_seen_at"] == r["created_at"] and r["auth_method"] == "password" and r["mfa_level"] == 0 for r in rows)
    for user, raw in users:
        assert service.authenticate(path, raw).handle == user.handle                               # still signed in after the upgrade


def test_an_old_session_unused_for_longer_than_the_idle_timeout_ends_after_the_upgrade(tmp_path, before_0026):
    path = tmp_path / "t.db"
    migrate(path, before_0026)
    _, raw = old_session(path, "old@example.com", service.utcnow().replace(microsecond=0) - timedelta(hours=2))
    migrate(path)
    assert service.authenticate(path, raw) is None


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "t.db"
    migrate(path)
    user, _ = service.create_user(path, email="a@example.com", password="correct horse battery", display_name="A", roles=["learner"], with_session=False)
    other, _ = service.create_user(path, email="b@example.com", password="correct horse battery", display_name="B", roles=["learner"], with_session=False)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("CREATE TEMP TABLE other_user AS SELECT ? AS id", (other.id,))       # a real second account, so the foreign key alone cannot refuse
    yield conn, user.id
    conn.close()


def insert(conn, uid, **over):
    row = {"user_id": uid, "token_hash": "h" * 64, "public_id": "a" * 32, "created_at": "2026-10-01 00:00:00", "last_seen_at": "2026-10-01 00:00:00",
           "expires_at": "2026-10-08 00:00:00", **over}
    cols = ", ".join(row)
    conn.execute(f"INSERT INTO sessions({cols}) VALUES ({', '.join('?' * len(row))})", tuple(row.values()))


@pytest.mark.parametrize("over", [{"public_id": None}, {"public_id": "a" * 31}, {"public_id": "A" * 32}, {"public_id": "g" * 32}, {"last_seen_at": None},
                                  {"last_seen_at": "2026-09-30 23:59:59"}, {"last_seen_at": "2026-10-08 00:00:01"}, {"auth_method": "magic"},
                                  {"mfa_level": 2}, {"expires_at": "2026-09-30 00:00:00"}])
def test_an_incomplete_or_inconsistent_session_cannot_be_inserted(db, over):
    conn, uid = db
    with pytest.raises(sqlite3.IntegrityError):
        insert(conn, uid, **over)


def test_public_ids_and_token_hashes_are_unique(db):
    conn, uid = db
    insert(conn, uid)
    with pytest.raises(sqlite3.IntegrityError):
        insert(conn, uid, token_hash="x" * 64)                                  # same public id
    with pytest.raises(sqlite3.IntegrityError):
        insert(conn, uid, public_id="b" * 32)                                   # same token hash


@pytest.mark.parametrize("change", ["user_id = (SELECT id FROM other_user)", "token_hash = 'z'", "public_id = 'b' || substr(public_id, 2)", "created_at = '2026-01-01 00:00:00'",
                                    "expires_at = '2099-01-01 00:00:00'", "auth_method = 'password+totp'", "mfa_level = 1",
                                    "last_seen_at = '2026-09-30 00:00:00'", "last_seen_at = '2026-10-09 00:00:00'", "last_seen_at = NULL"])
def test_a_session_can_only_move_its_last_use_forward(db, change):
    conn, uid = db
    insert(conn, uid)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(f"UPDATE sessions SET {change}")


def test_using_and_deleting_a_session_are_allowed(db):
    conn, uid = db
    insert(conn, uid)
    conn.execute("UPDATE sessions SET last_seen_at = '2026-10-02 12:00:00'")
    assert one(conn, "SELECT last_seen_at FROM sessions") == "2026-10-02 12:00:00"
    conn.execute("DELETE FROM users WHERE id = ?", (uid,))                     # sessions still cascade with their user
    assert one(conn, "SELECT COUNT(*) FROM sessions") == 0
