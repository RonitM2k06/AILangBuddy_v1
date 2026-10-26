import pytest

from backend import main
from backend.db import connect

from .conftest import PASSWORD, plant_mfa_session, register


# ---------- protected state ----------
def test_user_can_read_and_write_own_state(client):
    me = register(client, "a@example.com")
    assert client.get(f"/api/state/{me['handle']}").json() == {"state": None}
    assert client.put(f"/api/state/{me['handle']}", json={"v": 1, "xp": 7}).json() == {"ok": True}
    assert client.get(f"/api/state/{me['handle']}").json() == {"state": {"v": 1, "xp": 7}}


def test_user_cannot_access_another_users_state(client, client2):
    a = register(client, "a@example.com")
    b = register(client2, "b@example.com")
    assert client.put(f"/api/state/{a['handle']}", json={"v": 1, "name": "A"}).status_code == 200
    assert client2.get(f"/api/state/{a['handle']}").status_code == 403
    assert client2.put(f"/api/state/{a['handle']}", json={"v": 1, "name": "hacked"}).status_code == 403
    assert client.get(f"/api/state/{a['handle']}").json()["state"]["name"] == "A"  # untouched
    assert client.get(f"/api/state/{b['handle']}").status_code == 403


def test_anonymous_cannot_access_user_state(client):
    assert client.get("/api/state/u_abcdef").status_code == 401
    assert client.put("/api/state/u_abcdef", json={"v": 1}).status_code == 401
    assert client.get("/api/state/somebody-else").status_code == 401


def test_cannot_plant_state_under_unowned_handle(client):
    assert client.put("/api/state/brand-new-handle", json={"v": 1}).status_code == 401
    with connect(main.DB_PATH) as conn:
        assert conn.execute("SELECT COUNT(*) FROM state WHERE user_id='brand-new-handle'").fetchone()[0] == 0


def test_state_unreadable_after_logout(client):
    me = register(client, "a@example.com")
    client.put(f"/api/state/{me['handle']}", json={"v": 1})
    client.post("/api/auth/logout")
    assert client.get(f"/api/state/{me['handle']}").status_code == 401


def test_admin_has_no_blanket_access_to_user_state(client, client2, make_admin):
    a = register(client, "a@example.com")
    make_admin()
    client2.post("/api/auth/login", json={"email": "admin@example.com", "password": PASSWORD})
    assert client2.get(f"/api/state/{a['handle']}").status_code == 403


# ---------- demo mode (prototype keeps working) ----------
def test_demo_learner_state_is_not_shared_in_demo_mode(client):
    """Phase 14A: demo mode no longer opens a shared server-side state. Anonymous visitors keep their state in the browser."""
    assert client.get("/api/state/demo-alex").status_code == 401
    assert client.put("/api/state/demo-alex", json={"v": 1, "xp": 1}).status_code == 401


def test_demo_learner_state_locked_when_demo_mode_off(client, lockdown, client2):
    assert client.get("/api/state/demo-alex").status_code == 401
    assert client.put("/api/state/demo-alex", json={"v": 1}).status_code == 401
    register(client2, "a@example.com")
    assert client2.get("/api/state/demo-alex").status_code == 403


def test_ai_endpoint_open_in_demo_mode_and_falls_back_offline(client, monkeypatch):
    monkeypatch.setattr(main, "provider", lambda: None)
    r = client.post("/api/ai", json={"mode": "tutor", "history": [{"role": "me", "text": "hi"}]})
    assert r.status_code == 200 and r.json() == {"ok": False, "reason": "offline"}


def test_ai_endpoint_requires_login_when_demo_mode_off(client, lockdown, monkeypatch):
    monkeypatch.setattr(main, "provider", lambda: None)
    body = {"mode": "tutor", "history": [{"role": "me", "text": "hi"}]}
    assert client.post("/api/ai", json=body).status_code == 401
    register(client, "a@example.com")
    assert client.post("/api/ai", json=body).json() == {"ok": False, "reason": "offline"}  # fallback intact


def test_public_reference_data_and_health_stay_open_in_lockdown(client, lockdown):
    for path in ("/api/health", "/api/languages", "/api/cities", "/"):
        assert client.get(path).status_code == 200


# ---------- RBAC ----------
def test_admin_endpoint_rejects_anonymous(client):
    assert client.get("/api/admin/users").status_code == 401


@pytest.mark.parametrize("role", ["learner", "parent"])
def test_admin_endpoint_rejects_non_admin_roles(client, role):
    register(client, f"{role}@example.com", role=role)
    assert client.get("/api/admin/users").status_code == 403


def test_admin_endpoint_allows_admin(client, client2, make_admin):
    register(client, "learner@example.com")
    register(client2, "parent@example.com", role="parent")
    admin = make_admin()
    assert admin.roles == {"admin"}
    client.post("/api/auth/login", json={"email": "admin@example.com", "password": PASSWORD})
    r = client.get("/api/admin/users")
    assert r.status_code == 403 and r.json()["detail"]["code"] == "mfa_required"     # Phase 14D: a password alone is not enough for an admin
    plant_mfa_session(client, "admin@example.com")
    r = client.get("/api/admin/users")
    assert r.status_code == 200
    # Phase 14E: accounts are opaque references with roles, never e-mails, names or handles
    from backend.admin.learners import ref_for
    from backend.db import connect
    with connect(main.DB_PATH) as conn:
        ids = {e: conn.execute("SELECT id FROM users WHERE email = ?", (e,)).fetchone()[0] for e in ("learner@example.com", "parent@example.com", "admin@example.com")}
    users = {u["ref"]: u for u in r.json()["items"]}
    assert users[ref_for(ids["learner@example.com"])]["roles"] == ["learner"]
    assert users[ref_for(ids["parent@example.com"])]["roles"] == ["parent"]
    assert users[ref_for(ids["admin@example.com"])]["roles"] == ["admin"]
    assert r.json()["total"] == 4 and "@example.com" not in r.text and "demo-alex" not in r.text
    assert "password" not in r.text and "scrypt" not in r.text


def test_role_is_read_from_server_not_client(client):
    register(client, "a@example.com")
    # Client-side tampering attempts: extra headers/cookies claiming admin change nothing.
    r = client.get("/api/admin/users", headers={"X-Role": "admin", "X-User-Id": "1"}, cookies={"role": "admin"})
    assert r.status_code == 403
    assert client.get("/api/auth/me").json()["user"]["roles"] == ["learner"]


def test_admin_cli_creates_admin_who_can_log_in(client, make_admin):
    make_admin("root@example.com")
    r = client.post("/api/auth/login", json={"email": "root@example.com", "password": PASSWORD})
    assert r.status_code == 200 and r.json()["user"]["roles"] == ["admin"]
