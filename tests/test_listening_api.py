import json

import pytest

from backend import main
from backend.audio.service import AudioService, GeneratedAudio
from backend.listening import service as listening_service
from backend.personalization import clock
from backend.repositories import audio as audio_repo

from .conftest import PASSWORD, register
from .lis import activities, activity_id, answer, answer_right, answer_wrong, correct_option, db, wrong_options
from .pers import uid

PROFILE = {"native_language": "en", "target_language": "hi", "cefr_level": "A1", "date_of_birth": "2000-05-20"}


@pytest.fixture
def learner(client):
    register(client, "l@example.com")
    assert client.put("/api/profile", json=PROFILE).status_code == 200
    return client


def get_activity(c, slug):
    return c.get(f"/api/listening/{activity_id(c, slug)}").json()["activity"]


# ---------- access control ----------
ENDPOINTS = [("get", "/api/listening", None), ("get", "/api/listening/1", None), ("get", "/api/listening/attempts", None),
             ("get", "/api/listening/progress", None), ("post", "/api/listening/1/attempts", {"option_id": 1})]


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
def test_admin_rejected(client, client2, make_admin, method, path, body):
    make_admin()
    client2.post("/api/auth/login", json={"email": "admin@example.com", "password": PASSWORD})
    assert call(client2, method, path, body).status_code == 403


@pytest.mark.parametrize("method,path,body", ENDPOINTS)
def test_profile_required(client, method, path, body):
    register(client, "noprofile@example.com")
    assert call(client, method, path, body).status_code == 409


@pytest.mark.parametrize("method,path,body", ENDPOINTS)
def test_access_ends_at_logout(learner, method, path, body):
    learner.post("/api/auth/logout")
    assert call(learner, method, path, body).status_code == 401


# ---------- listing / retrieval ----------
def test_list_activities(learner):
    acts = activities(learner)
    assert len(acts) == 15 and [a["slug"] for a in acts][:3] == ["greetings-meaning", "greetings-phrase", "transport-meaning"]
    first = acts[0]
    assert set(first) == {"id", "slug", "title", "mode", "prompt", "difficulty", "cefr_level", "topic", "progress"}
    assert first["topic"] == {"slug": "greetings", "name": "Greetings", "icon": "👋"} and first["mode"] == "choose_meaning"
    assert first["progress"] == {"status": "not_started", "attempts": 0, "correct": 0, "last_attempt_at": None}


def test_get_activity_shape_for_browser_tts(learner):
    a = get_activity(learner, "food-meaning")
    assert set(a) == {"id", "slug", "title", "mode", "prompt", "difficulty", "cefr_level", "topic", "audio", "options", "progress"}
    assert a["audio"] == {"kind": "browser_tts", "provider": "browser_tts", "locale": "hi-IN",
                          "speak_text": "कम तीखा बनाना, प्लीज़।", "speak_fallback_text": "Kam teekha banana, please."}
    assert len(a["options"]) == 3 and all(set(o) == {"id", "text"} for o in a["options"])
    assert all(o["text"] for o in a["options"])
    assert any("spicy" in o["text"].lower() for o in a["options"])            # meanings in the learner's native language


def test_choose_phrase_options_show_phrase_and_pronunciation(learner):
    a = get_activity(learner, "food-phrase")
    assert a["mode"] == "choose_phrase" and all(set(o) == {"id", "text", "pronunciation"} for o in a["options"])
    assert sorted(o["pronunciation"] for o in a["options"]) == sorted(["Paani milega?", "Bill de dijiye.", "Ek plate chhole bhature dena."])


def test_a_stored_audio_file_replaces_the_fallback_and_hides_the_spoken_text(learner):
    a = activity_id(learner, "food-meaning")
    with db() as conn:
        item = conn.execute("SELECT item_id FROM listening_activities WHERE id=?", (a,)).fetchone()[0]
        audio_repo.insert_asset(conn, item, conn.execute("SELECT language_id FROM vocabulary_items WHERE id=?", (item,)).fetchone()[0],
                                "static", "hi-IN", "asha", "/static/audio/teekha.mp3", "audio/mpeg", 2100, "2026-01-01 00:00:00")
    audio = get_activity(learner, "food-meaning")["audio"]
    assert audio == {"kind": "url", "provider": "static", "locale": "hi-IN", "url": "/static/audio/teekha.mp3", "mime_type": "audio/mpeg", "duration_ms": 2100, "voice": "asha"}
    assert "कम तीखा" not in json.dumps(learner.get(f"/api/listening/{a}").json(), ensure_ascii=False)     # no text of the phrase anywhere in the response


def test_the_audio_service_in_use_can_be_swapped_without_touching_listening(learner, monkeypatch):
    class Gen:
        provider = "external_tts"

        def synthesize(self, text, locale):
            return GeneratedAudio("https://tts.example.com/x.mp3", "audio/mpeg", 1000, "v")

    monkeypatch.setattr(listening_service, "AUDIO", AudioService(generator=Gen()))
    a = activity_id(learner, "food-meaning")
    with db() as conn:
        listening_service.AUDIO.ensure_asset(conn, conn.execute("SELECT item_id FROM listening_activities WHERE id=?", (a,)).fetchone()[0], "2026-01-01 00:00:00")
    assert get_activity(learner, "food-meaning")["audio"]["provider"] == "external_tts"


def test_unknown_activity_404(learner):
    assert learner.get("/api/listening/9999").status_code == 404
    assert answer(learner, 9999, 1).status_code == 404


def test_unpublished_activities_are_hidden_and_unreachable(learner):
    a = activity_id(learner, "food-meaning")
    opt = correct_option(a)
    with db() as conn:
        conn.execute("UPDATE listening_activities SET status='draft' WHERE id=?", (a,))
    assert "food-meaning" not in [x["slug"] for x in activities(learner)]
    assert learner.get(f"/api/listening/{a}").status_code == 404 and answer(learner, a, opt).status_code == 404


def test_level_filter_includes_lower_levels_only(learner):
    with db() as conn:
        conn.execute("INSERT INTO language_levels(language_id, cefr_code) SELECT id, 'A2' FROM languages WHERE code='hi' AND NOT EXISTS (SELECT 1 FROM language_levels ll WHERE ll.language_id=languages.id AND ll.cefr_code='A2')")
        conn.execute("INSERT INTO listening_activities(language_id, cefr_code, topic_id, item_id, slug, title, mode, prompt, difficulty, sort_order, status) "
                     "SELECT language_id, 'A2', topic_id, item_id, 'a2-one', 'A2', mode, prompt, 2, 1, 'published' FROM listening_activities WHERE slug='food-meaning' AND language_id = (SELECT id FROM languages WHERE code='hi')")
    assert "a2-one" not in [a["slug"] for a in activities(learner)]
    learner.put("/api/profile", json={**PROFILE, "cefr_level": "A2"})
    slugs = [a["slug"] for a in activities(learner)]
    assert slugs[-1] == "a2-one" and len(slugs) == 16


def test_other_target_language_has_no_listening_yet(learner):
    learner.put("/api/profile", json={**PROFILE, "target_language": "hinglish"})
    assert activities(learner) == [] and learner.get("/api/listening/1").status_code == 404
    assert learner.get("/api/listening/progress").json()["progress"]["activities_total"] == 0


# ---------- answer-key protection ----------
def test_answer_keys_never_appear_in_any_get_response(learner):
    leaked = ("is_correct", "correct", "correct_option_id", "answer", "item_id", "heard", "key")
    for a in activities(learner):
        content = learner.get(f"/api/listening/{a['id']}").json()["activity"]
        content.pop("progress")                       # progress legitimately has a "correct" count of the learner's own attempts
        assert not any(f'"{k}"' in json.dumps(content) for k in leaked), (a["slug"], content)
    listing = [{k: v for k, v in a.items() if k != "progress"} for a in activities(learner)]
    assert not any(f'"{k}"' in json.dumps(listing) for k in leaked)
    assert learner.get("/api/listening/attempts").json() == {"attempts": []}


def test_no_field_identifies_the_correct_option(learner):
    """Across every activity the correct option is not distinguishable by position, id order or extra fields."""
    positions, id_ranks = set(), set()
    for a in activities(learner):
        opts = get_activity(learner, a["slug"])["options"]
        right = correct_option(a["id"])
        ids = [o["id"] for o in opts]
        positions.add(ids.index(right))
        id_ranks.add(sorted(ids).index(right))
        assert all(set(o) <= {"id", "text", "pronunciation"} for o in opts)
    assert positions == {0, 1, 2}


def test_correct_answer_is_revealed_only_after_answering(learner):
    a = activity_id(learner, "food-meaning")
    body = answer(learner, a, wrong_options(a)[0]).json()
    assert body["correct"] is False and body["correct_option_id"] == correct_option(a)
    assert body["heard"] == {"text": "कम तीखा बनाना, प्लीज़।", "pronunciation": "Kam teekha banana, please.", "meaning": "Make it less spicy, please.", "natural": "Not too spicy, please."}


# ---------- grading ----------
def test_every_activity_grades_correctly_for_every_option(learner):
    for a in activities(learner):
        right = correct_option(a["id"])
        opts = [o["id"] for o in get_activity(learner, a["slug"])["options"]]
        assert right in opts and len(opts) == 3
        for opt in opts:
            r = answer(learner, a["id"], opt)
            assert r.status_code == 200
            assert r.json()["correct"] is (opt == right), (a["slug"], opt)
            assert r.json()["correct_option_id"] == right


def test_exactly_one_option_is_correct(learner):
    a = activity_id(learner, "directions-phrase")
    results = [answer(learner, a, o["id"]).json()["correct"] for o in get_activity(learner, "directions-phrase")["options"]]
    assert sorted(results) == [False, False, True]


def test_the_client_cannot_assert_its_own_correctness(learner):
    a = activity_id(learner, "food-meaning")
    w = wrong_options(a)[0]
    for extra in ({"correct": True}, {"is_correct": True}, {"user_id": 1}, {"session_id": 1}, {"item_id": 1}):
        assert answer(learner, a, w, **extra).status_code == 422
    assert answer(learner, a, w).json()["correct"] is False


# ---------- submission validation ----------
@pytest.mark.parametrize("body", [{}, {"option_id": 0}, {"option_id": -1}, {"option_id": "x"}, {"option_id": 999999}, {"option_id": 1, "plays": -1},
                                  {"option_id": 1, "plays": 100}, {"option_id": 1, "response_ms": -1}, {"option_id": 1, "response_ms": 3_600_001}])
def test_invalid_submissions_rejected_and_nothing_stored(learner, body):
    a = activity_id(learner, "food-meaning")
    assert learner.post(f"/api/listening/{a}/attempts", json=body).status_code == 422
    with db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM listening_attempts").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM audio_sessions").fetchone()[0] == 0


def test_an_option_of_another_activity_is_rejected(learner):
    a, b = activity_id(learner, "food-meaning"), activity_id(learner, "transport-meaning")
    assert answer(learner, a, correct_option(b)).status_code == 422
    with db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM listening_attempts").fetchone()[0] == 0


# ---------- attempt persistence ----------
def test_an_answer_persists_a_session_and_an_attempt_owned_by_the_learner(learner, monkeypatch):
    monkeypatch.setattr(clock, "now", lambda: "2026-09-30 10:00:10")
    a = activity_id(learner, "food-meaning")
    r = answer(learner, a, wrong_options(a)[1], plays=3, response_ms=4500).json()
    assert r["attempt"] == {"id": r["attempt"]["id"], "plays": 3, "duration_ms": 4500, "attempted_at": "2026-09-30 10:00:10"}
    me = uid("l@example.com")
    with db() as conn:
        att = conn.execute("SELECT user_id, session_id, activity_id, is_correct, plays, attempted_at FROM listening_attempts").fetchone()
        ses = conn.execute("SELECT user_id, language_id, kind, status, started_at, ended_at, duration_ms FROM audio_sessions").fetchone()
        assert att["user_id"] == me and ses["user_id"] == me and (att["activity_id"], att["is_correct"], att["plays"]) == (a, 0, 3)
        assert (ses["kind"], ses["status"], ses["duration_ms"]) == ("listening", "completed", 4500)
        assert (ses["started_at"], ses["ended_at"]) == ("2026-09-30 10:00:05", "2026-09-30 10:00:10")      # started = ended - 4.5 s
        assert conn.execute("SELECT id FROM languages WHERE code='hi'").fetchone()[0] == ses["language_id"]


def test_every_submission_is_a_new_attempt_with_its_own_session(learner):
    a = activity_id(learner, "food-meaning")
    for _ in range(3):
        answer(learner, a, wrong_options(a)[0])
    answer(learner, a, correct_option(a))
    with db() as conn:
        assert conn.execute("SELECT COUNT(*), SUM(is_correct) FROM listening_attempts").fetchone()[:] == (4, 1)
        assert conn.execute("SELECT COUNT(DISTINCT session_id) FROM listening_attempts").fetchone()[0] == 4


def test_a_response_without_timing_still_records_a_session(learner):
    answer_right(learner, "food-meaning")
    with db() as conn:
        s = conn.execute("SELECT started_at, ended_at, duration_ms FROM audio_sessions").fetchone()
        assert s["started_at"] == s["ended_at"] and s["duration_ms"] is None


def test_attempts_listing(learner, monkeypatch):
    stamps = iter(f"2026-09-30 10:0{i}:00" for i in range(6))
    monkeypatch.setattr(clock, "now", lambda: next(stamps))
    answer_wrong(learner, "food-meaning")
    answer_right(learner, "transport-phrase")
    answer_right(learner, "food-meaning")
    rows = learner.get("/api/listening/attempts").json()["attempts"]
    assert [(r["activity"]["title"], r["correct"]) for r in rows] == [("Food: what does it mean?", True), ("Transport: which phrase did you hear?", True), ("Food: what does it mean?", False)]
    assert set(rows[0]) == {"id", "activity", "option_id", "correct", "plays", "duration_ms", "attempted_at"} and rows[0]["activity"]["mode"] == "choose_meaning"
    assert len(learner.get("/api/listening/attempts?limit=2").json()["attempts"]) == 2
    for bad in ("?limit=0", "?limit=201", "?limit=x"):
        assert learner.get("/api/listening/attempts" + bad).status_code == 422


# ---------- progress ----------
def test_progress_calculation(learner, monkeypatch):
    stamps = iter(f"2026-09-30 10:{i:02d}:00" for i in range(20))
    monkeypatch.setattr(clock, "now", lambda: next(stamps))
    p = lambda: learner.get("/api/listening/progress").json()["progress"]
    assert p() == {"activities_total": 15, "activities_attempted": 0, "activities_completed": 0, "attempts": 0, "correct": 0, "accuracy": None, "last_attempt_at": None}
    answer_wrong(learner, "food-meaning")
    assert (p()["activities_attempted"], p()["activities_completed"], p()["accuracy"]) == (1, 0, 0.0)
    assert {a["slug"]: a["progress"]["status"] for a in activities(learner)}["food-meaning"] == "attempted"
    answer_right(learner, "food-meaning")
    answer_right(learner, "transport-meaning")
    answer_wrong(learner, "transport-phrase")
    got = p()
    assert (got["activities_attempted"], got["activities_completed"], got["attempts"], got["correct"], got["accuracy"]) == (3, 2, 4, 2, 0.5)
    assert got["last_attempt_at"] == "2026-09-30 10:03:00"
    statuses = {a["slug"]: a["progress"] for a in activities(learner)}
    assert statuses["food-meaning"]["status"] == "completed" and statuses["food-meaning"]["attempts"] == 2 and statuses["food-meaning"]["correct"] == 1
    assert statuses["transport-phrase"]["status"] == "attempted" and statuses["greetings-meaning"]["status"] == "not_started"
    assert get_activity(learner, "food-meaning")["progress"]["status"] == "completed"


# ---------- learner isolation ----------
def test_attempts_and_progress_belong_to_the_authenticated_learner(learner, client2):
    register(client2, "b@example.com")
    client2.put("/api/profile", json=PROFILE)
    answer_right(learner, "food-meaning")
    answer_wrong(learner, "transport-meaning")
    assert client2.get("/api/listening/attempts").json() == {"attempts": []}
    assert client2.get("/api/listening/progress").json()["progress"]["attempts"] == 0
    assert {a["progress"]["status"] for a in activities(client2)} == {"not_started"}
    answer_wrong(client2, "food-meaning")
    assert [r["correct"] for r in learner.get("/api/listening/attempts").json()["attempts"]] == [False, True]
    assert learner.get("/api/listening/progress").json()["progress"]["attempts"] == 2
    assert client2.get("/api/listening/progress").json()["progress"]["attempts"] == 1
    with db() as conn:
        assert {r[0] for r in conn.execute("SELECT DISTINCT user_id FROM listening_attempts")} == {uid("l@example.com"), uid("b@example.com")}


def test_the_user_cannot_be_chosen_by_the_client(learner):
    a = activity_id(learner, "food-meaning")
    assert learner.post(f"/api/listening/{a}/attempts?user_id=1", json={"option_id": correct_option(a)}).status_code == 200
    assert learner.get("/api/listening/attempts?user_id=1").json()["attempts"][0]["activity"]["id"] == a        # the query param is ignored
    with db() as conn:
        demo = conn.execute("SELECT id FROM users WHERE handle='demo-alex'").fetchone()[0]
        assert conn.execute("SELECT COUNT(*) FROM listening_attempts WHERE user_id=?", (demo,)).fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM audio_sessions WHERE user_id=?", (demo,)).fetchone()[0] == 0


def test_responses_do_not_expose_user_ids(learner):
    answer_right(learner, "food-meaning")
    blob = " ".join(learner.get(p).text for p in ("/api/listening", "/api/listening/attempts", "/api/listening/progress"))
    assert "user_id" not in blob and "session_id" not in blob and "l@example.com" not in blob


# ---------- prototype and earlier phases ----------
def test_prototype_and_earlier_phases_unchanged(client):
    assert client.get("/api/state/demo-alex").status_code == 401          # Phase 14A: no shared demo state
    assert client.put("/api/state/demo-alex", json={"v": 1}).status_code == 401
    assert client.get("/api/cities").json()["cities"][0]["slug"] == "delhi"
    assert client.get("/static/content.js").status_code == 200
    register(client, "l@example.com")
    client.put("/api/profile", json=PROFILE)
    assert (len(client.get("/api/lessons").json()["lessons"]), len(client.get("/api/situations").json()["situations"])) == (7, 8)
    assert client.get("/api/recommendations").status_code == 200 and client.get("/api/daily-plan").status_code == 200
