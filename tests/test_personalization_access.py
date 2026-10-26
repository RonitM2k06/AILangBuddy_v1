import pytest

from .conftest import PASSWORD, register
from .pers import cycle_attempts, db, uid

PROFILE = {"native_language": "en", "target_language": "hi", "cefr_level": "A1", "date_of_birth": "2000-05-20"}

ENDPOINTS = [
    ("get", "/api/confidence", None), ("get", "/api/confidence/history", None),
    ("post", "/api/confidence", {"topic": "food", "score": 50}),
    ("get", "/api/weaknesses", None), ("get", "/api/difficulty", None), ("get", "/api/recommendations", None),
    ("get", "/api/daily-plan", None), ("post", "/api/daily-plan/generate", None),
    ("post", "/api/daily-plan/tasks/1/status", {"status": "done"}),
]


def call(c, method, path, body):
    return getattr(c, method)(path, **({"json": body} if body is not None else {}))


@pytest.mark.parametrize("method,path,body", ENDPOINTS)
def test_anonymous_rejected_even_in_demo_mode(client, method, path, body):
    assert call(client, method, path, body).status_code == 401


@pytest.mark.parametrize("method,path,body", ENDPOINTS)
def test_parent_rejected(client, method, path, body):
    register(client, "p@example.com", role="parent")
    assert call(client, method, path, body).status_code == 403


@pytest.mark.parametrize("method,path,body", ENDPOINTS)
def test_admin_is_not_a_learner(client, client2, make_admin, method, path, body):
    make_admin()
    client2.post("/api/auth/login", json={"email": "admin@example.com", "password": PASSWORD})
    assert call(client2, method, path, body).status_code == 403


@pytest.mark.parametrize("method,path,body", ENDPOINTS)
def test_profile_required(client, method, path, body):
    register(client, "noprofile@example.com")
    assert call(client, method, path, body).status_code == 409


@pytest.mark.parametrize("method,path,body", ENDPOINTS)
def test_access_ends_at_logout(client, method, path, body):
    register(client, "l@example.com")
    client.put("/api/profile", json=PROFILE)
    client.post("/api/auth/logout")
    assert call(client, method, path, body).status_code == 401


def test_demo_learner_data_is_not_reachable_through_the_new_endpoints(client):
    """DEMO_MODE opens only the prototype's AI endpoint (offline unless DEMO_LIVE_AI), never the personalization ones. Since Phase 14A there is
    no shared demo state at all."""
    assert client.get("/api/state/demo-alex").status_code == 401
    for method, path, body in ENDPOINTS:
        assert call(client, method, path, body).status_code == 401


def test_every_learner_sees_only_their_own_data_everywhere(client, client2):
    register(client, "a@example.com")
    client.put("/api/profile", json=PROFILE)
    register(client2, "b@example.com")
    client2.put("/api/profile", json=PROFILE)
    cycle_attempts(uid("a@example.com"), "food", [0] * 8)
    client.post("/api/confidence", json={"topic": "food", "score": 12})
    client.post("/api/daily-plan/generate")
    # A sees it all
    assert client.get("/api/weaknesses").json()["weaknesses"] and client.get("/api/confidence/history").json()["history"]
    assert client.get("/api/daily-plan").json()["plan"]["generated"]
    # B sees none of it, whatever query parameters are sent
    a_id = uid("a@example.com")
    for suffix in ("", f"?user_id={a_id}"):
        assert client2.get("/api/weaknesses" + suffix).json()["weaknesses"] == []
        assert client2.get("/api/confidence/history" + suffix).json()["history"] == []
        assert client2.get("/api/daily-plan" + suffix).json()["plan"]["generated"] is False
        assert [r["kind"] for r in client2.get("/api/recommendations" + suffix).json()["recommendations"]] == ["next_lesson", "next_situation"]
    assert client2.get("/api/confidence").json()["overall"] is None


@pytest.mark.parametrize("path,body", [
    ("/api/confidence", {"topic": "food", "score": 50, "user_id": 1}),
    ("/api/confidence", {"topic": "food", "score": 50, "language_id": 1}),
    ("/api/daily-plan/tasks/1/status", {"status": "done", "user_id": 1}),
])
def test_unknown_body_fields_are_rejected(client, path, body):
    register(client, "l@example.com")
    client.put("/api/profile", json=PROFILE)
    client.post("/api/daily-plan/generate")
    assert client.post(path, json=body).status_code == 422


def test_responses_never_expose_internal_ids_of_other_users(client):
    register(client, "l@example.com")
    client.put("/api/profile", json=PROFILE)
    cycle_attempts(uid("l@example.com"), "food", [0] * 8)
    client.post("/api/confidence", json={"topic": "food", "score": 12})
    client.post("/api/daily-plan/generate")
    blob = " ".join(client.get(p).text for p in ("/api/confidence", "/api/confidence/history", "/api/weaknesses", "/api/recommendations", "/api/daily-plan"))
    assert "user_id" not in blob and "password" not in blob and "email" not in blob and "l@example.com" not in blob


def test_prototype_and_earlier_phases_unchanged(client):
    assert client.get("/api/state/demo-alex").status_code == 401          # Phase 14A: no shared demo state
    assert client.put("/api/state/demo-alex", json={"v": 1}).status_code == 401
    assert client.get("/api/cities").json()["cities"][0]["slug"] == "delhi"
    register(client, "l@example.com")
    client.put("/api/profile", json=PROFILE)
    assert len(client.get("/api/lessons").json()["lessons"]) == 7 and len(client.get("/api/situations").json()["situations"]) == 8
