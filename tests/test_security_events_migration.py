"""Phase 14E: migration 0028_security_events.sql. One new append-only table; existing users, admins, sessions and two-factor credentials are
untouched. Every database here is a temp file: buddy.db is never opened."""
import shutil
import sqlite3

import pytest

from backend.auth import service, totp_crypto
from backend.db import connect
from backend.db.migrate import MIGRATIONS_DIR, migrate
from backend.repositories import two_factor as tf_repo


@pytest.fixture
def through_0027(tmp_path):
    d = tmp_path / "phase14d"
    d.mkdir()
    for f in sorted(MIGRATIONS_DIR.glob("*.sql")):
        if f.name < "0028":
            shutil.copy(f, d / f.name)
    return d


def schema(path):
    return {(r[0], r[1]): r[2] for r in sqlite3.connect(path).execute("SELECT type, name, sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'")}


def test_0028_applies_cleanly_and_idempotently(tmp_path):
    versions = [f.name.split("_")[0] for f in sorted(MIGRATIONS_DIR.glob("*.sql"))]
    assert versions[27] == "0028" and versions.count("0028") == 1 and versions[28:] == ["0029", "0030", "0031", "0032", "0033", "0034", "0035", "0036", "0037", "0038", "0039", "0040", "0041", "0042", "0043", "0044", "0045", "0046", "0047", "0048", "0049", "0050", "0051", "0052", "0053", "0054", "0055", "0056"]  # 0029-0056: city packs (0034 adds content_reviews)
    path = tmp_path / "fresh.db"
    assert migrate(path)[-29:] == ["0028", "0029", "0030", "0031", "0032", "0033", "0034", "0035", "0036", "0037", "0038", "0039", "0040", "0041", "0042", "0043", "0044", "0045", "0046", "0047", "0048", "0049", "0050", "0051", "0052", "0053", "0054", "0055", "0056"] and migrate(path) == []
    with connect(path) as conn:
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok" and not conn.execute("PRAGMA foreign_key_check").fetchall()
        assert conn.execute("SELECT COUNT(*) FROM security_events").fetchone()[0] == 0


def test_the_upgrade_adds_only_the_event_table_and_keeps_everything_else(tmp_path, through_0027):
    path = tmp_path / "t.db"
    migrate(path, through_0027)
    learner, learner_token = service.create_user(path, email="l@example.com", password="correct horse battery", display_name="L", roles=["learner"])
    admin, admin_token = service.create_user(path, email="a@example.com", password="correct horse battery", display_name="A", roles=["admin"])
    ct, nonce = totp_crypto.encrypt(b"s" * 20, admin.id)
    with connect(path) as conn:                                              # an admin with two-factor already on, before the upgrade
        conn.execute("""INSERT INTO two_factor_credentials(user_id, secret_ciphertext, secret_nonce, status, created_at, enabled_at, last_used_step)
                        VALUES (?, ?, ?, 'enabled', '2026-10-01 00:00:00', '2026-10-01 00:01:00', 5)""", (admin.id, ct, nonce))
        tf_repo.replace_recovery_codes(conn, admin.id, ["a" * 64, "b" * 64], "2026-10-01 00:01:00")
        snapshot = {t: [tuple(r) for r in conn.execute(f"SELECT * FROM {t} ORDER BY 1")] for t in
                    ("users", "user_roles", "sessions", "two_factor_credentials", "recovery_codes", "login_challenges", "admin_audit_log")}
    before = schema(path)
    assert migrate(path) == ["0028", "0029", "0030", "0031", "0032", "0033", "0034", "0035", "0036", "0037", "0038", "0039", "0040", "0041", "0042", "0043", "0044", "0045", "0046", "0047", "0048", "0049", "0050", "0051", "0052", "0053", "0054", "0055", "0056"]                                # 0029-0035 are data only but 0034, which adds one table: the schema comparison below is unchanged
    after = schema(path)
    assert {k for k in after if after[k] != before.get(k)} == {("table", "security_events"), ("index", "idx_security_events_type"), ("index", "idx_security_events_user"),
                                                                ("index", "idx_security_events_time"), ("trigger", "security_events_no_update"),
                                                                ("trigger", "security_events_no_delete"), ("table", "content_reviews")}   # 0034: the review record
    assert not set(before) - set(after)
    with connect(path) as conn:
        assert {t: [tuple(r) for r in conn.execute(f"SELECT * FROM {t} ORDER BY 1")] for t in snapshot} == snapshot
        assert conn.execute("SELECT COUNT(*) FROM security_events").fetchone()[0] == 0          # history is not invented
    assert service.authenticate(path, learner_token).handle == learner.handle and service.authenticate(path, admin_token).mfa_level == 0


def test_the_events_table_is_append_only_after_the_upgrade(tmp_path, through_0027):
    path = tmp_path / "t.db"
    migrate(path, through_0027)
    migrate(path)
    conn = sqlite3.connect(path)
    conn.execute("INSERT INTO security_events(occurred_at, event_type, outcome) VALUES ('2026-10-01 00:00:00', 'logout', 'ok')")
    for sql in ("UPDATE security_events SET outcome = 'failed'", "DELETE FROM security_events"):
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(sql)
    assert conn.execute("SELECT outcome FROM security_events").fetchone()[0] == "ok"
