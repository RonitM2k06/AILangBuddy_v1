from datetime import date

import pytest

from backend import main
from backend.db import connect
from backend.learner import service as learner_service

from .conftest import PASSWORD, register

VALID = {"native_language": "en", "target_language": "hi", "cefr_level": "A1", "date_of_birth": "2000-05-20"}


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch):
    monkeypatch.setattr(learner_service, "today", lambda: date(2026, 9, 30))


@pytest.fixture
def learner(client):
    return register(client, "l@example.com")


# ---------- catalogue ----------
def test_catalogue_endpoints_are_public(client):
    for p in ("/api/languages", "/api/cefr-levels", "/api/language-levels"):
        assert client.get(p).status_code == 200


def test_existing_languages_contract_unchanged(client):
    assert client.get("/api/languages").json()["languages"][0] == {"code": "en", "name": "English", "native_name": "English", "tts_locale": "en-IN"}


# ---------- profile read / write ----------
def test_no_profile_initially(client, learner):
    assert client.get("/api/profile").json() == {"profile": None}


def test_create_and_read_profile_with_derived_age_group(client, learner):
    r = client.put("/api/profile", json=VALID)
    assert r.status_code == 200
    p = r.json()["profile"]
    assert (p["native_language"], p["target_language"], p["cefr_level"]) == ("en", "hi", "A1")
    assert p["age"] == 26 and p["age_group"] == {"code": "adult", "label": "18+"}
    assert client.get("/api/profile").json()["profile"] == p


@pytest.mark.parametrize("dob,group", [("2020-01-01", "child"), ("2016-09-30", "teen"), ("2016-10-01", "child"),
                                       ("2008-09-30", "adult"), ("2008-10-01", "teen")])
def test_age_group_derived_from_dob(client, learner, dob, group):
    assert client.put("/api/profile", json={**VALID, "date_of_birth": dob}).json()["profile"]["age_group"]["code"] == group


def test_age_group_changes_with_time_without_rewriting_data(client, learner, monkeypatch):
    client.put("/api/profile", json={**VALID, "date_of_birth": "2008-12-01"})
    assert client.get("/api/profile").json()["profile"]["age_group"]["code"] == "teen"
    monkeypatch.setattr(learner_service, "today", lambda: date(2026, 12, 1))  # their 18th birthday
    assert client.get("/api/profile").json()["profile"]["age_group"]["code"] == "adult"


def test_update_replaces_profile_in_place(client, learner):
    client.put("/api/profile", json=VALID)
    client.put("/api/profile", json={**VALID, "target_language": "hinglish", "cefr_level": "A2"})
    p = client.get("/api/profile").json()["profile"]
    assert (p["target_language"], p["cefr_level"]) == ("hinglish", "A2")
    with connect(main.DB_PATH) as conn:
        assert conn.execute("SELECT COUNT(*) FROM learner_profiles").fetchone()[0] == 1


def test_client_cannot_set_age_group_or_user(client, learner):
    for extra in ({"age_group": "child"}, {"user_id": 1}, {"handle": "demo-alex"}, {"age": 5}):
        assert client.put("/api/profile", json={**VALID, **extra}).status_code == 422
    assert client.get("/api/profile").json() == {"profile": None}


# ---------- validation ----------
@pytest.mark.parametrize("change,field", [
    ({"cefr_level": "B1"}, "cefr_level"),                 # unsupported combination
    ({"cefr_level": "Z9"}, "cefr_level"),
    ({"target_language": "es"}, "cefr_level"),            # catalogued but no levels yet
    ({"target_language": "xx"}, "target_language"),
    ({"native_language": "xx"}, "native_language"),
    ({"native_language": "hi"}, "target_language"),       # same language
    ({"date_of_birth": "2027-01-01"}, "date_of_birth"),   # future
    ({"date_of_birth": "1800-01-01"}, "date_of_birth"),   # implausible
    ({"date_of_birth": "2001-02-30"}, "date_of_birth"),   # impossible date
])
def test_invalid_profiles_rejected_and_nothing_saved(client, learner, change, field):
    r = client.put("/api/profile", json={**VALID, **change})
    assert r.status_code == 422 and r.json()["detail"][0]["loc"] == ["body", field]
    assert client.get("/api/profile").json() == {"profile": None}


@pytest.mark.parametrize("missing", list(VALID))
def test_missing_fields_rejected(client, learner, missing):
    body = {k: v for k, v in VALID.items() if k != missing}
    assert client.put("/api/profile", json=body).status_code == 422


def test_bad_date_format_rejected(client, learner):
    assert client.put("/api/profile", json={**VALID, "date_of_birth": "20/05/2000"}).status_code == 422


def test_non_native_language_can_be_any_catalogue_language(client, learner):
    assert client.put("/api/profile", json={**VALID, "native_language": "es"}).status_code == 200


# ---------- authorization ----------
def test_profile_requires_login(client):
    assert client.get("/api/profile").status_code == 401
    assert client.put("/api/profile", json=VALID).status_code == 401


def test_profile_requires_login_even_in_demo_mode(client):
    assert client.put("/api/profile", json=VALID).status_code == 401  # demo mode only opens the prototype's own endpoints


def test_parent_and_admin_have_no_learner_profile(client, client2, make_admin):
    register(client, "p@example.com", role="parent")
    assert client.get("/api/profile").status_code == 403
    assert client.put("/api/profile", json=VALID).status_code == 403
    make_admin()
    client2.post("/api/auth/login", json={"email": "admin@example.com", "password": PASSWORD})
    assert client2.get("/api/profile").status_code == 403


def test_learners_cannot_see_or_change_each_others_profile(client, client2):
    register(client, "a@example.com")
    register(client2, "b@example.com")
    client.put("/api/profile", json={**VALID, "date_of_birth": "1990-01-01"})
    assert client2.get("/api/profile").json() == {"profile": None}
    client2.put("/api/profile", json={**VALID, "target_language": "hinglish", "date_of_birth": "2015-01-01"})
    a = client.get("/api/profile").json()["profile"]
    assert a["target_language"] == "hi" and a["date_of_birth"] == "1990-01-01"


def test_profile_unreadable_after_logout(client, learner):
    client.put("/api/profile", json=VALID)
    client.post("/api/auth/logout")
    assert client.get("/api/profile").status_code == 401


# ---------- existing prototype behaviour ----------
def test_demo_behaviour_unchanged_by_phase3(client):
    assert client.get("/api/state/demo-alex").status_code == 401          # Phase 14A: no shared demo state (anonymous state stays in the browser)
    assert client.put("/api/state/demo-alex", json={"v": 1, "level": "A1"}).status_code == 401
    assert client.get("/api/cities").json()["cities"][0]["languages"] == ["hi", "hinglish", "en"]
