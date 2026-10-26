"""Child adventure and teen home over HTTP: access, ownership, validation, lives behaviour, no leakage of ids or answers."""
import json

import pytest

from .agekids import answer_key, clear_level, db, freeze_clock, make_learner, play, uid
from .conftest import PASSWORD, register


@pytest.fixture
def kid(client):
    return make_learner(client, "kid@example.com", 7)


def lives_of(c):
    return c.get("/api/kids/adventure").json()["lives"]


def burn(c, n, key=None):
    key = key or answer_key()
    q, _, wrong = key[1][0]
    for _ in range(n):
        r = play(c, 1, q, wrong)
        assert r.status_code == 200, r.text
    return r


# ---------- access ----------
ENDPOINTS = [("get", "/api/experience", None), ("get", "/api/kids/adventure", None), ("get", "/api/kids/levels/1", None),
             ("post", "/api/kids/levels/1/answers", {"question": 1, "choice": 1}), ("get", "/api/teen/home", None)]


def call(c, method, path, body):
    return getattr(c, method)(path, **({"json": body} if body is not None else {}))


@pytest.mark.parametrize("method,path,body", ENDPOINTS)
def test_requires_login(client, lockdown, method, path, body):
    assert call(client, method, path, body).status_code == 401


@pytest.mark.parametrize("method,path,body", ENDPOINTS)
def test_admin_rejected(client, client2, make_admin, method, path, body):
    make_admin()
    client2.post("/api/auth/login", json={"email": "admin@example.com", "password": PASSWORD})
    assert call(client2, method, path, body).status_code == 403


@pytest.mark.parametrize("method,path,body", ENDPOINTS)
def test_profile_required(client, method, path, body):
    register(client, "np@example.com")
    assert call(client, method, path, body).status_code == 409


@pytest.mark.parametrize("age", [12, 30])
@pytest.mark.parametrize("method,path,body", ENDPOINTS[1:4])
def test_kids_endpoints_are_child_only(client, age, method, path, body):
    make_learner(client, "x@example.com", age)
    assert call(client, method, path, body).status_code == 403
    with db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM child_game_state").fetchone()[0] == 0     # nothing was created for them


@pytest.mark.parametrize("age", [7, 30])
def test_teen_home_is_teen_only(client, age):
    make_learner(client, "x@example.com", age)
    assert client.get("/api/teen/home").status_code == 403


# ---------- adventure ----------
def test_adventure_shape(kid):
    body = kid.get("/api/kids/adventure").json()
    assert body["lives"] == {"current": 5, "max": 5, "next_life_in_seconds": None}
    levels = body["levels"]
    assert len(levels) >= 5
    assert [l["number"] for l in levels] == list(range(1, len(levels) + 1))
    assert levels[0]["status"] == "open" and all(l["status"] == "locked" for l in levels[1:])
    assert set(levels[0]) == {"number", "title", "icon", "status", "done", "total"}
    assert all(l["done"] == 0 and l["total"] >= 1 for l in levels)


def test_child_levels_exclude_college(kid):
    titles = [l["title"].lower() for l in kid.get("/api/kids/adventure").json()["levels"]]
    assert not any("college" in t for t in titles)


def test_level_shows_questions_without_ids_or_answers(kid):
    body = kid.get("/api/kids/levels/1").json()
    text = json.dumps(body)
    for forbidden in ("is_correct", "correct", "item_id", "option_id", "activity_id", "user", "slug"):
        assert forbidden not in text
    q = body["questions"][0]
    assert q["number"] == 1 and q["instruction"] and q["done"] is False
    assert [c["choice"] for c in q["choices"]] == list(range(1, len(q["choices"]) + 1))
    assert len(q["choices"]) >= 2
    assert all(set(c) <= {"choice", "text", "pronunciation"} for c in q["choices"])
    assert "id" not in q


def test_locked_level_is_refused(kid):
    assert kid.get("/api/kids/levels/2").status_code == 409
    assert play(kid, 2, 1, 1).status_code == 409
    with db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM listening_attempts").fetchone()[0] == 0


@pytest.mark.parametrize("n", [0, -1, 999])
def test_unknown_level_is_404(kid, n):
    assert kid.get(f"/api/kids/levels/{n}").status_code == 404
    assert play(kid, n, 1, 1).status_code == 404


def test_level_number_must_be_integer(kid):
    assert kid.get("/api/kids/levels/abc").status_code == 422


# ---------- answers ----------
def test_correct_answer_costs_nothing(kid):
    key = answer_key()
    q, right, _ = key[1][0]
    r = play(kid, 1, q, right).json()
    assert r["correct"] is True and r["correct_choice"] == right and r["lives"]["current"] == 5 and r["game_over"] is False
    assert r["level"]["done"] == 1
    if len(key[1]) > 1:                                   # one right answer does not finish a level of several questions
        assert r["level_completed"] is False and r["next_level_unlocked"] is False and r["level"]["total"] == len(key[1])
        levels = kid.get("/api/kids/adventure").json()["levels"]
        assert levels[0]["status"] == "open" and levels[1]["status"] == "locked"
    with db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM child_life_losses").fetchone()[0] == 0


def test_wrong_answer_costs_one_life_and_reveals_the_right_one(kid):
    key = answer_key()
    q, right, wrong = key[1][0]
    r = play(kid, 1, q, wrong).json()
    assert r["correct"] is False and r["correct_choice"] == right
    assert r["lives"]["current"] == 4 and r["lives"]["next_life_in_seconds"] == 600
    assert lives_of(kid)["current"] == 4
    with db() as conn:
        assert [x["lives_after"] for x in conn.execute("SELECT lives_after FROM child_life_losses")] == [4]


def test_wrong_answer_feeds_the_existing_attempt_history(kid):
    key = answer_key()
    q, _, wrong = key[1][0]
    play(kid, 1, q, wrong)
    attempts = kid.get("/api/listening/attempts").json()["attempts"]
    assert len(attempts) == 1 and attempts[0]["correct"] is False


def test_lives_persist_in_the_database_not_the_client(kid, client2):
    burn(kid, 2)
    with db() as conn:
        row = conn.execute("SELECT lives FROM child_game_state WHERE user_id = ?", (uid("kid@example.com"),)).fetchone()
    assert row["lives"] == 3
    # a fresh browser session of the same learner sees the same lives
    client2.post("/api/auth/login", json={"email": "kid@example.com", "password": PASSWORD})
    assert client2.get("/api/kids/adventure").json()["lives"]["current"] == 3


def test_lives_never_go_below_zero_and_play_stops(kid, monkeypatch):
    freeze_clock(monkeypatch)
    key = answer_key()
    q, right, wrong = key[1][0]
    for expected in (4, 3, 2, 1):
        assert play(kid, 1, q, wrong).json()["lives"]["current"] == expected
    last = play(kid, 1, q, wrong).json()
    assert last["lives"]["current"] == 0 and last["game_over"] is True
    for choice in (wrong, right):                                   # even a right answer is refused with no lives
        r = play(kid, 1, q, choice)
        assert r.status_code == 409
        assert r.json()["detail"]["next_life_in_seconds"] == 600 and r.headers["Retry-After"] == "600"
    assert lives_of(kid)["current"] == 0
    with db() as conn:
        assert conn.execute("SELECT lives FROM child_game_state").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM listening_attempts").fetchone()[0] == 5      # refused answers leave no attempt
        assert conn.execute("SELECT COUNT(*) FROM child_life_losses").fetchone()[0] == 5


def test_lives_come_back_with_time_and_cap_at_five(kid, monkeypatch):
    tick = freeze_clock(monkeypatch)
    burn(kid, 5)
    assert lives_of(kid) == {"current": 0, "max": 5, "next_life_in_seconds": 600}
    tick(599)
    assert lives_of(kid) == {"current": 0, "max": 5, "next_life_in_seconds": 1}
    tick(1)
    assert lives_of(kid)["current"] == 1
    tick(600 * 2 + 100)
    assert lives_of(kid)["current"] == 3
    tick(10 ** 6)
    assert lives_of(kid) == {"current": 5, "max": 5, "next_life_in_seconds": None}
    with db() as conn:
        assert conn.execute("SELECT lives FROM child_game_state").fetchone()[0] == 5


def test_playing_again_after_waiting_works(kid, monkeypatch):
    tick = freeze_clock(monkeypatch)
    burn(kid, 5)
    key = answer_key()
    q, right, _ = key[1][0]
    assert play(kid, 1, q, right).status_code == 409
    tick(600)
    assert play(kid, 1, q, right).status_code == 200


def test_a_loss_does_not_delay_a_life_already_coming(kid, monkeypatch):
    tick = freeze_clock(monkeypatch)
    burn(kid, 3)                                    # 2 lives, regeneration counted from the first loss
    tick(550)
    burn(kid, 1)                                    # 1 life; the next one is still 50 s away, not 600
    assert lives_of(kid) == {"current": 1, "max": 5, "next_life_in_seconds": 50}


def test_clock_going_backwards_cannot_create_lives(kid, monkeypatch):
    tick = freeze_clock(monkeypatch)
    burn(kid, 3)
    tick(-100000)
    assert lives_of(kid)["current"] == 2


@pytest.mark.parametrize("body", [{"question": 0, "choice": 1}, {"question": 1, "choice": 0}, {"question": -1, "choice": 1}, {"question": 1, "choice": 11},
                                  {"question": 101, "choice": 1}, {"question": "a", "choice": 1}, {"question": 1}, {"choice": 1}, {}, {"question": 1.5, "choice": 1},
                                  {"question": 1, "choice": 1, "lives": 5}, {"question": 1, "choice": 1, "correct": True}, {"question": 1, "choice": 1, "user_id": 1}])
def test_invalid_answer_bodies(kid, body):
    assert kid.post("/api/kids/levels/1/answers", json=body).status_code == 422
    assert lives_of(kid)["current"] == 5


def test_question_or_choice_out_of_range_costs_nothing(kid):
    assert play(kid, 1, 50, 1).status_code == 422
    assert play(kid, 1, 1, 9).status_code == 422
    assert lives_of(kid)["current"] == 5
    with db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM listening_attempts").fetchone()[0] == 0


def test_no_way_for_a_client_to_set_lives(kid):
    for method, path in (("put", "/api/kids/adventure"), ("post", "/api/kids/adventure"), ("patch", "/api/kids/adventure"), ("put", "/api/kids/lives"), ("post", "/api/kids/lives")):
        assert call(kid, method, path, {"lives": 99}).status_code in (404, 405)
    assert lives_of(kid)["current"] == 5


# ---------- progression ----------
def test_completing_a_level_unlocks_the_next(kid):
    key = answer_key()
    for q, right, _ in key[1][:-1]:
        play(kid, 1, q, right)
    assert kid.get("/api/kids/adventure").json()["levels"][1]["status"] == "locked"
    q, right, _ = key[1][-1]
    r = play(kid, 1, q, right).json()
    assert r["level_completed"] is True and r["next_level_unlocked"] is True
    levels = kid.get("/api/kids/adventure").json()["levels"]
    assert levels[0]["status"] == "completed" and levels[0]["done"] == levels[0]["total"] and levels[1]["status"] == "open" and levels[2]["status"] == "locked"
    assert kid.get("/api/kids/levels/2").status_code == 200


def test_whole_adventure_can_be_completed(kid):
    key = answer_key()
    for level in key:
        clear_level(kid, level, key)
    levels = kid.get("/api/kids/adventure").json()["levels"]
    assert all(l["status"] == "completed" for l in levels)
    last = play(kid, len(key), 1, key[len(key)][0][1]).json()
    assert last["level_completed"] is True and last["next_level_unlocked"] is False


def test_wrong_answers_do_not_complete_a_level(kid):
    key = answer_key()
    q, _, wrong = key[1][0]
    play(kid, 1, q, wrong)
    assert kid.get("/api/kids/adventure").json()["levels"][0]["done"] == 0


def test_done_flag_in_level(kid):
    key = answer_key()
    q, right, _ = key[1][0]
    play(kid, 1, q, right)
    assert kid.get("/api/kids/levels/1").json()["questions"][0]["done"] is True


# ---------- isolation ----------
def test_two_children_have_independent_state(client, client2):
    make_learner(client, "a@example.com", 6)
    make_learner(client2, "b@example.com", 8)
    burn(client, 3)
    assert lives_of(client)["current"] == 2 and lives_of(client2)["current"] == 5
    clear_level(client2, 1)
    assert client.get("/api/kids/adventure").json()["levels"][0]["done"] == 0
    assert client2.get("/api/kids/adventure").json()["levels"][1]["status"] == "open"
    assert client.get("/api/kids/adventure").json()["levels"][1]["status"] == "locked"


def test_responses_carry_no_other_learner_data(client, client2):
    make_learner(client, "a@example.com", 6)
    make_learner(client2, "b@example.com", 8)
    r = burn(client, 1)
    blob = json.dumps(r.json()) + json.dumps(client.get("/api/kids/adventure").json()) + json.dumps(client.get("/api/kids/levels/1").json())
    for needle in ("b@example.com", "a@example.com", "email", "date_of_birth", "user_id", str(uid("b@example.com")) + '"'):
        assert needle not in blob


def test_the_user_comes_from_the_session(client, client2):
    make_learner(client, "a@example.com", 6)
    make_learner(client2, "b@example.com", 8)
    r = client.post("/api/kids/levels/1/answers", json={"question": 1, "choice": 1, "user_id": uid("b@example.com")})
    assert r.status_code == 422
    with db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM child_game_state WHERE user_id = ?", (uid("b@example.com"),)).fetchone()[0] == 0


def test_state_row_created_lazily_with_full_lives(kid):
    with db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM child_game_state").fetchone()[0] == 0
    kid.get("/api/kids/adventure")
    with db() as conn:
        assert conn.execute("SELECT lives FROM child_game_state").fetchone()[0] == 5


def test_growing_out_of_childhood_stops_the_game(client):
    make_learner(client, "grow@example.com", 7)
    burn(client, 1)
    assert client.put("/api/profile", json={"native_language": "en", "target_language": "hi", "cefr_level": "A1", "date_of_birth": "2000-05-20"}).status_code == 200
    assert client.get("/api/kids/adventure").status_code == 403


# ---------- voice safety ----------
def test_child_cannot_start_voice_practice(kid):
    r = kid.post("/api/speaking/sessions", json={})
    assert r.status_code == 403
    with db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM speaking_sessions").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM audio_sessions WHERE kind='speaking'").fetchone()[0] == 0


@pytest.mark.parametrize("age", [12, 30])
def test_older_learners_keep_voice_practice(client, age):
    make_learner(client, "v@example.com", age)
    assert client.post("/api/speaking/sessions", json={}).status_code in (200, 201)


# ---------- teen ----------
def test_teen_home_composes_existing_systems(client):
    make_learner(client, "t@example.com", 14)
    body = client.get("/api/teen/home").json()
    assert set(body) == {"path", "next_activity", "difficulty", "weaknesses", "daily_plan"}
    assert [l["slug"] for l in body["path"]] == [l["slug"] for l in client.get("/api/lessons").json()["lessons"]]
    assert any(l["slug"] == "college" for l in body["path"])           # teen keeps the college lesson
    assert body["difficulty"] == client.get("/api/difficulty").json()["difficulty"]
    assert body["next_activity"] == client.get("/api/recommendations").json()["next_activity"]
    assert body["daily_plan"] == client.get("/api/daily-plan").json()["plan"]
    assert len(body["weaknesses"]) <= 3


def test_teen_weaknesses_come_from_the_existing_detector(client):
    make_learner(client, "t@example.com", 14)
    from .lis import activities, answer, wrong_options
    for a in [x for x in activities(client) if x["topic"]["slug"] == "greetings"]:
        for w in wrong_options(a["id"])[:2]:
            answer(client, a["id"], w)
    home = client.get("/api/teen/home").json()
    assert home["weaknesses"] == client.get("/api/weaknesses").json()["weaknesses"][:3]


def test_teen_home_only_for_self(client, client2):
    make_learner(client, "t1@example.com", 14)
    make_learner(client2, "t2@example.com", 15)
    a, b = client.get("/api/teen/home").json(), client2.get("/api/teen/home").json()
    assert "t2@example.com" not in json.dumps(a) and "t1@example.com" not in json.dumps(b)


def test_adult_experience_and_endpoints_unchanged(client):
    make_learner(client, "ad@example.com", 30)
    assert client.get("/api/experience").json()["mode"] == "adult"
    for path in ("/api/lessons", "/api/situations", "/api/listening", "/api/recommendations", "/api/daily-plan", "/api/weaknesses", "/api/difficulty"):
        assert client.get(path).status_code == 200
