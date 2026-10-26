import sqlite3
from datetime import timedelta

import pytest

from backend import main
from backend.auth import service
from backend.auth.passwords import hash_password, verify_password
from backend.db import connect

from .conftest import PASSWORD, register


# ---------- password hashing ----------
def test_password_hash_is_not_plaintext_and_verifies():
    h = hash_password("s3cret-pass")
    assert "s3cret-pass" not in h and h.startswith("scrypt$")
    assert verify_password("s3cret-pass", h)
    assert not verify_password("wrong", h)


def test_password_hashes_are_salted():
    assert hash_password("same-password") != hash_password("same-password")


@pytest.mark.parametrize("bad", ["", "plaintext", "scrypt$x$y", "bcrypt$1$2$3$4$5"])
def test_malformed_stored_hash_fails_closed(bad):
    assert verify_password("anything", bad) is False


# ---------- registration ----------
def test_register_creates_session_and_learner_role(client):
    user = register(client, "a@example.com")
    assert user["roles"] == ["learner"] and user["email"] == "a@example.com"
    assert user["handle"].startswith("u_")
    assert client.get("/api/auth/me").json()["user"]["handle"] == user["handle"]


def test_register_parent_role(client):
    assert register(client, "p@example.com", role="parent")["roles"] == ["parent"]


def test_cannot_self_register_as_admin(client):
    r = client.post("/api/auth/register", json={"email": "x@example.com", "password": PASSWORD, "display_name": "X", "role": "admin"})
    assert r.status_code == 422
    with connect(main.DB_PATH) as conn:
        assert conn.execute("SELECT COUNT(*) FROM users WHERE email='x@example.com'").fetchone()[0] == 0


@pytest.mark.parametrize("extra", [{"roles": ["admin"]}, {"user_id": 1}, {"handle": "demo-alex"}])
def test_client_supplied_identity_fields_are_rejected(client, extra):
    body = {"email": "x@example.com", "password": PASSWORD, "display_name": "X", **extra}
    assert client.post("/api/auth/register", json=body).status_code == 422


def test_duplicate_email_case_insensitive(client):
    register(client, "Dup@Example.com")
    r = client.post("/api/auth/register", json={"email": "dup@example.COM", "password": PASSWORD, "display_name": "Y"})
    assert r.status_code == 409


@pytest.mark.parametrize("body", [
    {"email": "not-an-email", "password": PASSWORD, "display_name": "X"},
    {"email": "a@example.com", "password": "short", "display_name": "X"},
    {"email": "a@example.com", "password": PASSWORD, "display_name": "   "},
    {"email": "a@example.com", "password": "x" * 129, "display_name": "X"},
])
def test_registration_validation(client, body):
    assert client.post("/api/auth/register", json=body).status_code == 422


def test_validation_error_does_not_echo_password(client):
    r = client.post("/api/auth/register", json={"email": "bad", "password": "SuperSecretValue1", "display_name": "X"})
    assert r.status_code == 422 and "SuperSecretValue1" not in r.text


def test_no_plaintext_password_or_token_in_database(client):
    register(client, "a@example.com")
    token = client.cookies.get("llb_session")
    with connect(main.DB_PATH) as conn:
        dump = " ".join(str(v) for t in ("users", "sessions") for row in conn.execute(f"SELECT * FROM {t}") for v in tuple(row))
    assert PASSWORD not in dump and token not in dump


def test_responses_never_contain_credentials(client):
    r = client.post("/api/auth/register", json={"email": "a@example.com", "password": PASSWORD, "display_name": "A"})
    assert "password" not in r.text and "scrypt" not in r.text
    assert "scrypt" not in client.get("/api/auth/me").text


def test_session_cookie_flags(client):
    r = client.post("/api/auth/register", json={"email": "a@example.com", "password": PASSWORD, "display_name": "A"})
    cookie = r.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie and "max-age=" in cookie


def test_secure_flag_when_configured(client, monkeypatch):
    monkeypatch.setenv("COOKIE_SECURE", "1")
    r = client.post("/api/auth/register", json={"email": "s@example.com", "password": PASSWORD, "display_name": "A"})
    assert "secure" in r.headers["set-cookie"].lower()


# ---------- login / logout ----------
def test_login_success_and_me(client, client2):
    register(client, "a@example.com")
    r = client2.post("/api/auth/login", json={"email": "A@EXAMPLE.com", "password": PASSWORD})
    assert r.status_code == 200
    assert client2.get("/api/auth/me").json()["user"]["email"] == "a@example.com"


def test_login_failures_are_indistinguishable(client, client2):
    register(client, "a@example.com")
    wrong_pw = client2.post("/api/auth/login", json={"email": "a@example.com", "password": "wrong-password"})
    unknown = client2.post("/api/auth/login", json={"email": "nobody@example.com", "password": "wrong-password"})
    assert wrong_pw.status_code == unknown.status_code == 401
    assert wrong_pw.json() == unknown.json()
    assert "set-cookie" not in wrong_pw.headers


def test_demo_user_cannot_log_in(client):
    assert client.post("/api/auth/login", json={"email": "demo-alex", "password": "x"}).status_code == 422
    assert client.get("/api/auth/me").status_code == 401


def test_each_login_issues_new_token(client, client2):
    register(client, "a@example.com")
    client2.post("/api/auth/login", json={"email": "a@example.com", "password": PASSWORD})
    assert client.cookies.get("llb_session") != client2.cookies.get("llb_session")


def test_logout_invalidates_session_server_side(client):
    register(client, "a@example.com")
    stolen = client.cookies.get("llb_session")
    assert client.post("/api/auth/logout").json() == {"ok": True}
    client.cookies.set("llb_session", stolen)  # replay the old cookie
    assert client.get("/api/auth/me").status_code == 401
    with connect(main.DB_PATH) as conn:
        assert conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 0


def test_logout_without_session_is_ok(client):
    assert client.post("/api/auth/logout").status_code == 200


def test_logout_only_ends_own_session(client, client2):
    register(client, "a@example.com")
    client2.post("/api/auth/login", json={"email": "a@example.com", "password": PASSWORD})
    client.post("/api/auth/logout")
    assert client2.get("/api/auth/me").status_code == 200


def test_me_requires_login_and_rejects_garbage_cookie(client):
    assert client.get("/api/auth/me").status_code == 401
    client.cookies.set("llb_session", "not-a-real-token")
    assert client.get("/api/auth/me").status_code == 401


def test_session_expiry(client, monkeypatch):
    register(client, "a@example.com")
    assert client.get("/api/auth/me").status_code == 200
    real = service.utcnow
    monkeypatch.setattr(service, "utcnow", lambda: real() + timedelta(days=8))
    assert client.get("/api/auth/me").status_code == 401
    with connect(main.DB_PATH) as conn:
        assert conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 0  # expired row removed


def test_session_still_valid_before_expiry(client, monkeypatch):
    """The absolute lifetime on its own: the idle timeout (Phase 14C, tested in test_session_security.py) is lifted to its maximum here."""
    monkeypatch.setenv("SESSION_IDLE_MINUTES", str(7 * 24 * 60))
    register(client, "a@example.com")
    real = service.utcnow
    monkeypatch.setattr(service, "utcnow", lambda: real() + timedelta(days=6))
    assert client.get("/api/auth/me").status_code == 200


def test_login_throttle(client, client2, monkeypatch):
    register(client, "a@example.com")
    for _ in range(service.MAX_FAILURES):
        assert client2.post("/api/auth/login", json={"email": "a@example.com", "password": "wrong-password"}).status_code == 401
    r = client2.post("/api/auth/login", json={"email": "a@example.com", "password": PASSWORD})  # even the right one
    assert r.status_code == 429 and int(r.headers["retry-after"]) > 0
    real = service.utcnow
    monkeypatch.setattr(service, "utcnow", lambda: real() + timedelta(minutes=16))
    assert client2.post("/api/auth/login", json={"email": "a@example.com", "password": PASSWORD}).status_code == 200


# ---------- schema ----------
def test_roles_seeded_and_demo_user_is_learner_without_credentials(db_path):
    with connect(db_path) as conn:
        assert [r[0] for r in conn.execute("SELECT name FROM roles ORDER BY name")] == ["admin", "learner", "parent"]
        demo = conn.execute("SELECT email, password_hash FROM users WHERE handle='demo-alex'").fetchone()
        assert demo["email"] is None and demo["password_hash"] is None
        assert [r[0] for r in conn.execute("SELECT r.name FROM user_roles ur JOIN roles r ON r.id=ur.role_id JOIN users u ON u.id=ur.user_id WHERE u.handle='demo-alex'")] == ["learner"]


@pytest.mark.parametrize("sql", [
    "INSERT INTO users(handle, display_name, email, password_hash) VALUES ('h1','n','e@x.com',NULL)",
    "INSERT INTO users(handle, display_name, email, password_hash) VALUES ('h1','n',NULL,'hash')",
    "INSERT INTO user_roles(user_id, role_id) VALUES (999, 1)",
    "INSERT INTO user_roles(user_id, role_id) VALUES (1, 1)",  # demo user already has learner -> duplicate PK
    # an unknown user (FK) and an expiry before creation (CHECK, also refused by the 0026 trigger); public_id and last_seen_at are well-formed
    "INSERT INTO sessions(user_id, token_hash, public_id, created_at, last_seen_at, expires_at) VALUES (999,'t','" + "a" * 32 + "','2030-01-01 00:00:00','2030-01-01 00:00:00','2030-01-02 00:00:00')",
    "INSERT INTO sessions(user_id, token_hash, public_id, created_at, last_seen_at, expires_at) VALUES (1,'t','" + "a" * 32 + "','2030-01-02 00:00:00','2030-01-01 00:00:00','2030-01-01 00:00:00')",
    "DELETE FROM roles WHERE name='learner'",
])
def test_auth_constraints(db_path, sql):
    with pytest.raises(sqlite3.IntegrityError):
        with connect(db_path) as conn:
            conn.execute(sql)


def test_deleting_user_cascades_to_roles_and_sessions(client):
    register(client, "a@example.com")
    with connect(main.DB_PATH) as conn:
        conn.execute("DELETE FROM users WHERE email='a@example.com'")
        assert conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM user_roles WHERE user_id NOT IN (SELECT id FROM users)").fetchone()[0] == 0


def test_email_unique_index_is_case_insensitive(db_path):
    with pytest.raises(sqlite3.IntegrityError):
        with connect(db_path) as conn:
            conn.execute("INSERT INTO users(handle, display_name, email, password_hash) VALUES ('a','n','X@Y.com','h')")
            conn.execute("INSERT INTO users(handle, display_name, email, password_hash) VALUES ('b','n','x@y.COM','h')")
