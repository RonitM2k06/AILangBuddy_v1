import json
import threading
import time

import pytest

from backend import main
from backend.personalization import clock
from backend.speaking import pron_providers, service as speaking_service
from backend.speaking.pron_providers import COMPONENTS, PronError, PronunciationCapabilities, PronunciationResult

from .conftest import PASSWORD, register
from .spk import PROFILE, assess, audio, cancel, create, db, get, pronunciation, recordings, transcribe, transcribed, upload

ASKED = "नमस्ते, आप कैसे हैं?"           # the first speaking prompt


def first_item(client):
    return client.get("/api/speaking/prompts").json()["prompts"][0]["item"]["id"]


def tr(client, text=ASKED, pron=None, **kw):
    """A transcribed session ALWAYS on the first prompt, so results of different sessions are comparable."""
    return transcribed(client, text, pron=pron, item_id=first_item(client), **kw)


@pytest.fixture
def learner(client, monkeypatch):
    """A learner with speech recognition (mock) but NO pronunciation provider, the default configuration."""
    monkeypatch.setenv("STT_PROVIDER", "mock")
    register(client, "l@example.com")
    assert client.put("/api/profile", json=PROFILE).status_code == 200
    return client


@pytest.fixture
def assessor(learner, monkeypatch):
    monkeypatch.setenv("PRONUNCIATION_PROVIDER", "mock")
    return learner


class PStub:
    name, method = "stub", "proxy"

    def __init__(self, fn, languages=None, components=frozenset(COMPONENTS), requires_audio=False, word_scores=True):
        self.fn = fn
        self.calls = []
        self.capabilities = PronunciationCapabilities(components=frozenset(components), requires_audio=requires_audio, languages=languages, word_scores=word_scores)

    def assess(self, inp):
        self.calls.append(inp)
        return self.fn(inp)


def use_pron(monkeypatch, provider):
    monkeypatch.setattr(pron_providers, "_factory", lambda: provider)


def result(**kw):
    return lambda inp: PronunciationResult(**kw)


def raising(exc):
    def fn(inp):
        raise exc
    return fn


def rows(sql):
    with db() as conn:
        return [tuple(r) for r in conn.execute(sql)]


# ---------- access control ----------
ENDPOINTS = [("post", "/api/speaking/sessions/1/assess-pronunciation"), ("get", "/api/speaking/sessions/1/pronunciation"),
             ("get", "/api/speaking/pronunciation/history"), ("get", "/api/speaking/pronunciation/progress")]


@pytest.mark.parametrize("method,path", ENDPOINTS)
def test_anonymous_rejected_even_in_demo_mode(client, method, path):
    assert getattr(client, method)(path).status_code == 401


@pytest.mark.parametrize("method,path", ENDPOINTS)
def test_parent_rejected(client, method, path):
    register(client, "p@example.com", role="parent")
    assert getattr(client, method)(path).status_code == 403


@pytest.mark.parametrize("method,path", ENDPOINTS)
def test_admin_rejected(client, client2, make_admin, method, path):
    make_admin()
    client2.post("/api/auth/login", json={"email": "admin@example.com", "password": PASSWORD})
    assert getattr(client2, method)(path).status_code == 403


@pytest.mark.parametrize("method,path", ENDPOINTS)
def test_profile_required(client, method, path):
    register(client, "noprofile@example.com")
    assert getattr(client, method)(path).status_code == 409


@pytest.mark.parametrize("method,path", ENDPOINTS)
def test_access_ends_at_logout(learner, method, path):
    learner.post("/api/auth/logout")
    assert getattr(learner, method)(path).status_code == 401


# ---------- the assessment: two separate measurements ----------
def test_full_assessment_with_the_mock_provider(assessor, tmp_path):
    s = tr(assessor, ASKED, pron={"overall": 82, "components": {"fluency": 70, "prosody": 55}, "words": [("नमस्ते", 90), ("आप", 48), ("कैसे", 85), ("हैं", 88)]})
    r = assess(assessor, s["id"])
    assert r.status_code == 200
    a = r.json()["assessment"]
    assert a["status"] == "completed" and a["session_id"] == s["id"]
    assert a["target"] == {"text": ASKED, "pronunciation": "Namaste, aap kaise hain?", "meaning": "Hello, how are you?"}
    assert a["heard"] == {"text": ASKED, "confidence": None}
    assert a["content_match"]["words_expected"] == 4 and a["content_match"]["words_matched"] == 4 and a["content_match"]["missing"] == []
    p = a["pronunciation"]
    assert p["available"] is True and p["score"] == 82 and p["scale"] == "0-100" and p["method"] == "mock" and p["is_measurement"] is False
    assert p["components"] == {"fluency": 70, "prosody": 55} and [w["word"] for w in p["word_scores"]] == ["नमस्ते", "आप", "कैसे", "हैं"] and p["error"] is None
    assert set(a) == {"session_id", "status", "target", "heard", "content_match", "pronunciation", "feedback", "created_at"}
    assert get(assessor, s["id"]).json()["session"]["stage"] == "completed"                 # the STT session is untouched


def test_the_two_measurements_are_never_combined_into_one_number(assessor):
    s = tr(assessor, "नमस्ते आप", pron={"overall": 64})
    a = assess(assessor, s["id"]).json()["assessment"]
    assert a["content_match"]["words_matched"] == 2 and a["pronunciation"]["score"] == 64
    flat = json.dumps(a, ensure_ascii=False)
    for forbidden in ('"overall"', '"total"', '"combined"', '"accuracy"', '"final_score"', '"grade"'):
        assert forbidden not in flat


def test_a_perfect_transcript_does_not_mean_good_pronunciation(assessor):
    s = tr(assessor, ASKED, pron={"overall": 18})
    a = assess(assessor, s["id"]).json()["assessment"]
    assert a["content_match"]["words_matched"] == a["content_match"]["words_expected"] == 4          # every word was heard...
    assert a["pronunciation"]["score"] == 18                                                           # ...and the pronunciation score is still low


def test_a_poor_transcript_does_not_mean_poor_pronunciation(assessor):
    s = tr(assessor, "कुछ और", pron={"overall": 95})
    a = assess(assessor, s["id"]).json()["assessment"]
    assert a["content_match"]["words_matched"] == 0 and a["pronunciation"]["score"] == 95


def test_the_transcript_never_changes_the_pronunciation_score(assessor):
    first = assess(assessor, tr(assessor, ASKED, pron={"overall": 47})["id"]).json()["assessment"]
    second = assess(assessor, tr(assessor, "totally different words", pron={"overall": 47})["id"]).json()["assessment"]
    assert first["pronunciation"]["score"] == second["pronunciation"]["score"] == 47
    assert first["content_match"]["words_matched"] != second["content_match"]["words_matched"]


def test_the_pronunciation_signal_never_changes_the_content_match(assessor):
    low = assess(assessor, tr(assessor, "नमस्ते आप", pron={"overall": 5})["id"]).json()["assessment"]
    high = assess(assessor, tr(assessor, "नमस्ते आप", pron={"overall": 99})["id"]).json()["assessment"]
    assert low["content_match"] == high["content_match"] and low["pronunciation"]["score"] != high["pronunciation"]["score"]


def test_components_and_word_scores_exist_only_if_the_provider_reported_them(assessor):
    a = assess(assessor, tr(assessor, ASKED, pron={"overall": 70})["id"]).json()["assessment"]
    assert a["pronunciation"]["components"] == {} and a["pronunciation"]["word_scores"] == []
    assert rows("SELECT COUNT(*) FROM pronunciation_components") == [(0,)] and rows("SELECT COUNT(*) FROM pronunciation_word_scores") == [(0,)]
    assert "only an overall score" in json.dumps(a["feedback"])


def test_no_overall_from_the_provider_uses_the_mean_of_its_components(assessor):
    a = assess(assessor, tr(assessor, ASKED, pron={"components": {"fluency": 80, "prosody": 61}})["id"]).json()["assessment"]
    assert a["pronunciation"]["score"] == 71 and a["pronunciation"]["components"] == {"fluency": 80, "prosody": 61}      # mean 70.5 rounds half up


def test_no_phoneme_information_is_invented(assessor):
    a = assess(assessor, tr(assessor, "कुछ और", pron={"overall": 30})["id"]).json()["assessment"]
    text = json.dumps(a, ensure_ascii=False).lower()
    assert "phoneme" not in text and "phoneme_accuracy" not in a["pronunciation"]["components"]
    for banned in ("vowel", "consonant", "your pronunciation of", "mispronounced", "pronounced incorrectly"):
        assert banned not in text


def test_feedback_for_a_partial_transcript_says_what_the_recogniser_heard(assessor):
    a = assess(assessor, tr(assessor, "नमस्ते कैसे", pron={"overall": 75})["id"]).json()["assessment"]
    texts = [f["text"] for f in a["feedback"]]
    assert texts[0] == "Speech recognition picked up 2 of the 4 words of the phrase."
    assert any("did not pick up: आप, हैं" in t for t in texts)
    assert any("does not by itself show a pronunciation problem" in t for t in texts)


def test_a_mock_score_is_labelled_so_it_cannot_be_mistaken_for_a_measurement(assessor):
    a = assess(assessor, tr(assessor, ASKED, pron={"overall": 90})["id"]).json()["assessment"]
    assert a["pronunciation"]["method"] == "mock" and a["pronunciation"]["method_label"] == "test provider (mock)" and a["pronunciation"]["is_measurement"] is False
    assert any("controlled test values, not a measurement" in f["text"] for f in a["feedback"])


def test_a_real_model_would_be_labelled_as_a_measurement(assessor, monkeypatch):
    p = PStub(result(overall=77.0, components={"phoneme_accuracy": 70.0}, word_scores=[("आप", 40.0)]))
    p.method = "model"
    use_pron(monkeypatch, p)
    a = assess(assessor, tr(assessor, ASKED)["id"]).json()["assessment"]
    assert a["pronunciation"]["is_measurement"] is True and a["pronunciation"]["method"] == "model"
    assert a["pronunciation"]["components"] == {"phoneme_accuracy": 70} and any("Words to practise" in f["text"] and "आप (40)" in f["text"] for f in a["feedback"])
    assert any("not a human teacher" in f["text"] for f in a["feedback"])


def test_provider_names_are_not_exposed(assessor):
    a = assess(assessor, tr(assessor, ASKED, pron={"overall": 70})["id"]).json()["assessment"]
    flat = json.dumps(a)
    assert '"provider"' not in flat and "stub" not in flat


# ---------- persistence and idempotency ----------
def test_the_assessment_is_persisted_against_the_session_and_its_transcript(assessor):
    s = tr(assessor, "नमस्ते आप", pron={"overall": 66, "components": {"fluency": 70}, "words": [("आप", 50)]})
    assess(assessor, s["id"])
    (a,) = rows("SELECT session_id, transcript_id, provider, method, status, overall_score, words_expected, words_matched, locale FROM pronunciation_assessments")
    assert a[0] == s["id"] and a[2:] == ("mock", "mock", "completed", 66, 4, 2, "hi-IN")
    assert rows("SELECT t.text FROM speaking_transcripts t JOIN pronunciation_assessments p ON p.transcript_id = t.id") == [("नमस्ते आप",)]
    assert rows("SELECT component, score FROM pronunciation_components") == [("fluency", 70)] and rows("SELECT position, word, score FROM pronunciation_word_scores") == [(1, "आप", 50)]


def test_reading_it_back_returns_the_stored_assessment(assessor):
    s = tr(assessor, ASKED, pron={"overall": 71})
    first = assess(assessor, s["id"]).json()["assessment"]
    assert pronunciation(assessor, s["id"]).json() == {"assessment": first}


def test_repeating_the_assessment_is_idempotent_and_does_not_ask_the_provider_again(assessor, monkeypatch):
    p = PStub(result(overall=70.0))
    use_pron(monkeypatch, p)
    s = tr(assessor, ASKED)
    first = assess(assessor, s["id"]).json()
    for _ in range(4):
        assert assess(assessor, s["id"]).json() == first
    assert len(p.calls) == 1
    assert rows("SELECT COUNT(*) FROM pronunciation_assessments") == [(1,)]


def test_repeating_with_the_mock_gives_identical_numbers(assessor):
    s = tr(assessor, ASKED, pron={"overall": 58, "components": {"fluency": 61}})
    assert [assess(assessor, s["id"]).json()["assessment"]["pronunciation"] for _ in range(3)] == [assess(assessor, s["id"]).json()["assessment"]["pronunciation"]] * 3


def test_a_concurrent_completion_is_returned_instead_of_a_duplicate_or_an_error(assessor, monkeypatch):
    """Another request finishes the same assessment while this one is waiting on the provider."""
    s = tr(assessor, ASKED)

    def sneaky(inp):
        with db() as conn:
            tid = conn.execute("SELECT id FROM speaking_transcripts").fetchone()[0]
            conn.execute("INSERT INTO pronunciation_assessments(session_id, user_id, transcript_id, provider, method, status, overall_score, words_expected, words_matched, locale, created_at) "
                         "SELECT session_id, user_id, ?, 'other', 'mock', 'completed', 11, 4, 4, 'hi-IN', 't' FROM speaking_sessions", (tid,))
        return PronunciationResult(overall=99.0)

    use_pron(monkeypatch, PStub(sneaky))
    r = assess(assessor, s["id"])
    assert r.status_code == 200 and r.json()["assessment"]["pronunciation"]["score"] == 11 and rows("SELECT COUNT(*) FROM pronunciation_assessments") == [(1,)]


# ---------- session state ----------
def test_unknown_sessions_are_not_found(assessor):
    assert assess(assessor, 99999).status_code == 404 and pronunciation(assessor, 99999).status_code == 404


@pytest.mark.parametrize("stage", ["created", "recorded", "failed", "cancelled"])
def test_a_session_without_a_transcript_cannot_be_assessed(assessor, monkeypatch, stage):
    s = create(assessor)
    if stage != "created":
        upload(assessor, s["id"], audio("x"))
    if stage == "failed":
        monkeypatch.setenv("STT_PROVIDER", "none")
        transcribe(assessor, s["id"])
    if stage == "cancelled":
        cancel(assessor, s["id"])
    assert get(assessor, s["id"]).json()["session"]["stage"] == stage
    r = assess(assessor, s["id"])
    assert r.status_code == 409 and "transcript" in r.json()["detail"]
    assert rows("SELECT COUNT(*) FROM pronunciation_assessments") == [(0,)]


def test_a_session_being_processed_cannot_be_assessed(assessor):
    s = create(assessor)
    upload(assessor, s["id"])
    with db() as conn:
        conn.execute("UPDATE speaking_sessions SET stage='processing'")
    assert assess(assessor, s["id"]).status_code == 409


def test_getting_the_assessment_of_an_unassessed_session_is_empty_not_an_error(assessor):
    s = tr(assessor, ASKED, pron={"overall": 50})
    assert pronunciation(assessor, s["id"]).json() == {"assessment": None}


# ---------- no pronunciation provider ----------
def test_without_a_provider_the_word_check_still_works_and_pronunciation_is_unavailable(learner):
    s = tr(learner, "नमस्ते कैसे")
    a = assess(learner, s["id"]).json()["assessment"]
    assert a["status"] == "failed" and a["content_match"]["words_matched"] == 2 and a["content_match"]["words_expected"] == 4
    p = a["pronunciation"]
    assert p["available"] is False and p["score"] is None and p["method"] is None and p["components"] == {} and p["word_scores"] == []
    assert p["error"] == {"code": "provider_unavailable", "message": "Pronunciation analysis isn't available on this server."}
    assert any("does not measure pronunciation" in f["text"] for f in a["feedback"])
    assert rows("SELECT provider, method, status, error_code, overall_score FROM pronunciation_assessments") == [("none", None, "failed", "provider_unavailable", None)]


def test_a_good_transcript_without_a_provider_still_gets_no_pronunciation_score(learner):
    a = assess(learner, tr(learner, ASKED)["id"]).json()["assessment"]
    assert a["content_match"]["words_matched"] == 4 and a["pronunciation"]["score"] is None


def test_the_availability_is_reported_with_the_prompts(learner, monkeypatch):
    assert learner.get("/api/speaking/prompts").json()["pronunciation"] == {"available": False, "method": None}
    monkeypatch.setenv("PRONUNCIATION_PROVIDER", "mock")
    assert learner.get("/api/speaking/prompts").json()["pronunciation"] == {"available": True, "method": "mock"}


def test_a_recording_deleted_before_the_provider_was_configured_cannot_be_analysed(learner, monkeypatch):
    s = tr(learner, ASKED, pron={"overall": 80})                         # default config: the recording is deleted at transcription
    assert recordings_empty(learner)
    monkeypatch.setenv("PRONUNCIATION_PROVIDER", "mock")
    a = assess(learner, s["id"]).json()["assessment"]
    assert a["status"] == "failed" and a["pronunciation"]["error"]["code"] == "recording_unavailable" and a["content_match"]["words_matched"] == 4


def recordings_empty(client):
    return recordings(main.DB_PATH.parent) == []


# ---------- provider failures ----------
def failed(assessor, monkeypatch, provider, **kw):
    use_pron(monkeypatch, provider)
    r = assess(assessor, tr(assessor, ASKED, **kw)["id"])
    assert r.status_code == 200, r.text                                          # a provider failure is a stored outcome, never a 500
    return r.json()["assessment"]


def test_a_failing_provider_is_handled_safely(assessor, monkeypatch):
    a = failed(assessor, monkeypatch, PStub(raising(PronError("provider_error", "boom"))))
    assert a["status"] == "failed" and a["pronunciation"]["score"] is None and a["pronunciation"]["error"]["code"] == "provider_error"
    assert a["content_match"]["words_matched"] == 4                               # the word check is unaffected
    assert rows("SELECT status, error_code, overall_score FROM pronunciation_assessments") == [("failed", "provider_error", None)]
    assert rows("SELECT COUNT(*) FROM pronunciation_components") == [(0,)]


def test_an_unexpected_provider_exception_never_leaks(assessor, monkeypatch):
    a = failed(assessor, monkeypatch, PStub(raising(RuntimeError("SECRET-INTERNAL sk-9"))))
    assert a["pronunciation"]["error"]["code"] == "provider_error" and "SECRET" not in json.dumps(a) and "sk-9" not in json.dumps(a)


def test_the_provider_call_is_time_limited(assessor, monkeypatch):
    monkeypatch.setenv("PRONUNCIATION_TIMEOUT_SECONDS", "0.1")
    t = time.monotonic()
    a = failed(assessor, monkeypatch, PStub(lambda i: (time.sleep(1.0), PronunciationResult(overall=50.0))[1]))
    assert time.monotonic() - t < 0.9 and a["pronunciation"]["error"]["code"] == "provider_timeout"


@pytest.mark.parametrize("bad", [
    PronunciationResult(overall=150.0), PronunciationResult(overall=-1.0), PronunciationResult(overall=float("nan")), PronunciationResult(overall="80"),
    PronunciationResult(overall=True), PronunciationResult(overall=80.0, components={"fluency": 101.0}), PronunciationResult(overall=80.0, components={"charisma": 70.0}),
    PronunciationResult(overall=80.0, word_scores=[("w", 200.0)]), PronunciationResult(overall=80.0, word_scores=[("", 50.0)]),
    {"overall": 80}, None, "80",
])
def test_malformed_provider_output_is_rejected_and_nothing_partial_is_stored(assessor, monkeypatch, bad):
    a = failed(assessor, monkeypatch, PStub(lambda i, b=bad: b))
    assert a["status"] == "failed" and a["pronunciation"]["error"]["code"] == "malformed_output" and a["pronunciation"]["score"] is None
    assert rows("SELECT COUNT(*) FROM pronunciation_components") == [(0,)] and rows("SELECT COUNT(*) FROM pronunciation_word_scores") == [(0,)]
    assert rows("SELECT status, overall_score FROM pronunciation_assessments") == [("failed", None)]


def test_a_result_with_nothing_in_it_is_no_signal(assessor, monkeypatch):
    assert failed(assessor, monkeypatch, PStub(result()))["pronunciation"]["error"]["code"] == "no_signal"


def test_the_mock_without_markers_is_no_signal_never_an_invented_score(assessor):
    a = assess(assessor, tr(assessor, ASKED)["id"]).json()["assessment"]               # audio carries no pronunciation marker
    assert a["pronunciation"]["error"]["code"] == "no_signal" and a["pronunciation"]["score"] is None


def test_the_mock_can_be_made_to_fail(assessor):
    a = assess(assessor, tr(assessor, ASKED, pron={"fail": True, "overall": 90})["id"]).json()["assessment"]
    assert a["pronunciation"]["error"]["code"] == "provider_error" and a["pronunciation"]["score"] is None


def test_an_unsupported_language_fails_before_the_provider_is_called(assessor, monkeypatch):
    p = PStub(result(overall=50.0), languages=frozenset({"fr"}))
    a = failed(assessor, monkeypatch, p)
    assert a["pronunciation"]["error"]["code"] == "unsupported_language" and p.calls == []


def test_a_failed_assessment_can_be_retried_and_the_history_is_kept(assessor, monkeypatch):
    s = tr(assessor, ASKED, pron={"overall": 70})
    use_pron(monkeypatch, PStub(raising(PronError("provider_timeout"))))
    assert assess(assessor, s["id"]).json()["assessment"]["status"] == "failed"
    assert pronunciation(assessor, s["id"]).json()["assessment"]["status"] == "failed"
    use_pron(monkeypatch, PStub(result(overall=64.0)))
    assert assess(assessor, s["id"]).json()["assessment"]["pronunciation"]["score"] == 64
    assert pronunciation(assessor, s["id"]).json()["assessment"]["status"] == "completed"       # the completed one wins over earlier failures
    assert rows("SELECT status FROM pronunciation_assessments ORDER BY id") == [("failed",), ("completed",)]


def test_failed_attempts_are_capped_per_session(assessor, monkeypatch):
    s = tr(assessor, ASKED)
    use_pron(monkeypatch, PStub(raising(PronError("provider_error"))))
    for _ in range(5):
        assert assess(assessor, s["id"]).status_code == 200
    r = assess(assessor, s["id"])
    assert r.status_code == 409 and "Too many" in r.json()["detail"]
    assert rows("SELECT COUNT(*) FROM pronunciation_assessments") == [(5,)]


# ---------- score bounds, end to end ----------
@pytest.mark.parametrize("score", [0, 1, 50, 99, 100])
def test_scores_at_the_edges_of_the_scale_are_stored_and_returned(assessor, score):
    a = assess(assessor, tr(assessor, ASKED, pron={"overall": score})["id"]).json()["assessment"]
    assert a["pronunciation"]["score"] == score and 0 <= rows("SELECT overall_score FROM pronunciation_assessments")[0][0] <= 100


@pytest.mark.parametrize("score", [-1, 100.5, 101, 1000])
def test_scores_outside_the_scale_never_reach_the_database_or_the_learner(assessor, score):
    a = assess(assessor, tr(assessor, ASKED, pron={"overall": score})["id"]).json()["assessment"]
    assert a["status"] == "failed" and a["pronunciation"]["score"] is None and a["pronunciation"]["error"]["code"] == "malformed_output"
    assert rows("SELECT overall_score FROM pronunciation_assessments") == [(None,)]


# ---------- learner isolation and ownership ----------
@pytest.fixture
def two(assessor, client2):
    register(client2, "b@example.com")
    client2.put("/api/profile", json=PROFILE)
    return assessor, client2


def test_another_learner_cannot_assess_or_read_my_session(two):
    a, b = two
    s = tr(a, ASKED, pron={"overall": 61})
    assert assess(b, s["id"]).status_code == 404 and pronunciation(b, s["id"]).status_code == 404
    assert rows("SELECT COUNT(*) FROM pronunciation_assessments") == [(0,)]                 # nothing was written on my behalf
    mine = assess(a, s["id"]).json()["assessment"]
    assert assess(b, s["id"]).status_code == 404 and pronunciation(b, s["id"]).status_code == 404
    assert pronunciation(a, s["id"]).json()["assessment"] == mine


def test_assessments_transcripts_history_and_progress_are_per_learner(two):
    a, b = two
    mine = assess(a, tr(a, "alpha private transcript", pron={"overall": 11})["id"]).json()["assessment"]
    theirs = assess(b, tr(b, "beta own transcript", pron={"overall": 99})["id"]).json()["assessment"]
    assert mine["pronunciation"]["score"] == 11 and theirs["pronunciation"]["score"] == 99
    ha, hb = a.get("/api/speaking/pronunciation/history").json()["history"], b.get("/api/speaking/pronunciation/history").json()["history"]
    assert [h["pronunciation_score"] for h in ha] == [11] and [h["pronunciation_score"] for h in hb] == [99]       # each sees only their own rows
    assert {h["session_id"] for h in ha}.isdisjoint({h["session_id"] for h in hb})
    assert a.get("/api/speaking/pronunciation/progress").json()["progress"]["assessed_sessions"] == 1
    assert b.get("/api/speaking/pronunciation/progress").json()["progress"]["pronunciation"][0]["average_score"] == 99.0
    assert rows("SELECT COUNT(DISTINCT user_id) FROM pronunciation_assessments") == [(2,)]


def test_the_client_cannot_choose_the_owner(two):
    a, b = two
    s = tr(a, ASKED, pron={"overall": 61})
    a_id = rows("SELECT id FROM users WHERE email='l@example.com'")[0][0]
    assert b.post(f"/api/speaking/sessions/{s['id']}/assess-pronunciation?user_id={a_id}").status_code == 404      # the parameter is ignored
    own = tr(b, ASKED, pron={"overall": 40})
    assert b.post(f"/api/speaking/sessions/{own['id']}/assess-pronunciation?user_id={a_id}").status_code == 200
    assert rows(f"SELECT COUNT(*) FROM pronunciation_assessments WHERE user_id={a_id}") == [(0,)]


# ---------- history and progress ----------
def test_history_is_newest_first_and_lists_summaries(assessor):
    for score, text in ((40, "नमस्ते"), (88, ASKED)):
        assess(assessor, tr(assessor, text, pron={"overall": score})["id"])
    h = assessor.get("/api/speaking/pronunciation/history").json()["history"]
    assert [x["pronunciation_score"] for x in h] == [88, 40] and h[0]["method"] == "mock" and h[0]["status"] == "completed"
    assert set(h[0]) == {"session_id", "prompt", "status", "pronunciation_score", "method", "words_expected", "words_matched", "created_at"}
    assert (h[1]["words_matched"], h[1]["words_expected"]) == (1, 4)
    assert len(assessor.get("/api/speaking/pronunciation/history?limit=1").json()["history"]) == 1
    for bad in ("?limit=0", "?limit=101", "?limit=x"):
        assert assessor.get("/api/speaking/pronunciation/history" + bad).status_code == 422


def test_progress_keeps_methods_apart_and_never_blends_test_scores_into_a_measurement(assessor, monkeypatch):
    assess(assessor, tr(assessor, ASKED, pron={"overall": 50})["id"])
    assess(assessor, tr(assessor, ASKED, pron={"overall": 70})["id"])
    p = PStub(result(overall=90.0))
    p.method = "model"
    use_pron(monkeypatch, p)
    assess(assessor, tr(assessor, "नमस्ते आप")["id"])
    prog = assessor.get("/api/speaking/pronunciation/progress").json()["progress"]
    by = {m["method"]: m for m in prog["pronunciation"]}
    assert by["mock"]["average_score"] == 60.0 and by["mock"]["assessments"] == 2 and by["mock"]["is_measurement"] is False
    assert by["model"]["average_score"] == 90.0 and by["model"]["is_measurement"] is True
    assert prog["assessed_sessions"] == 3 and prog["content_match"] == {"words_expected": 12, "words_matched": 10}
    assert "average_score" not in {k for k in prog}                                          # there is no single blended average


def test_failed_attempts_are_counted_but_do_not_add_scores(learner):
    assess(learner, tr(learner, ASKED)["id"])
    prog = learner.get("/api/speaking/pronunciation/progress").json()["progress"]
    assert prog["attempts"] == 1 and prog["failed"] == 1 and prog["assessed_sessions"] == 0 and prog["pronunciation"] == []


# ---------- privacy and retention ----------
def test_responses_never_expose_paths_hashes_identities_or_audio(assessor, tmp_path):
    s = tr(assessor, ASKED, pron={"overall": 70})
    assess(assessor, s["id"])
    blob = json.dumps([pronunciation(assessor, s["id"]).json(), assessor.get("/api/speaking/pronunciation/history").json(), assessor.get("/api/speaking/pronunciation/progress").json()], ensure_ascii=False)
    for forbidden in ("audio_ref", "rec_", str(tmp_path), "recordings", "sha256", "user_id", "l@example.com", ".webm", "/Users/", "MOCKPRON", "MOCKSTT"):
        assert forbidden not in blob, forbidden


def test_no_raw_audio_reaches_sqlite(assessor, monkeypatch):
    marker = b"UNIQUE-PRONUNCIATION-AUDIO-MARKER-5c1e"
    s = create(assessor)
    upload(assessor, s["id"], audio("x", pron={"overall": 70}, extra=marker * 20))
    transcribe(assessor, s["id"])
    assess(assessor, s["id"])
    assert marker not in main.DB_PATH.read_bytes()


def test_a_recording_is_kept_only_until_it_has_been_assessed(assessor, tmp_path):
    s = create(assessor)
    upload(assessor, s["id"], audio(ASKED, pron={"overall": 70}))
    transcribe(assessor, s["id"])
    assert len(recordings(tmp_path)) == 1                                                    # kept: the pronunciation provider needs the audio
    assess(assessor, s["id"])
    assert recordings(tmp_path) == []                                                        # gone as soon as the assessment is stored
    assert rows("SELECT audio_ref IS NULL, audio_deleted_at IS NOT NULL FROM speaking_sessions") == [(1, 1)]


def test_without_a_pronunciation_provider_the_recording_is_deleted_at_transcription(learner, tmp_path):
    s = create(learner)
    upload(learner, s["id"], audio(ASKED))
    transcribe(learner, s["id"])
    assert recordings(tmp_path) == []


def test_a_failed_assessment_keeps_the_recording_for_a_retry_until_the_sweep(assessor, monkeypatch, tmp_path):
    s = create(assessor)
    upload(assessor, s["id"], audio(ASKED, pron={"overall": 70}))
    transcribe(assessor, s["id"])
    use_pron(monkeypatch, PStub(raising(PronError("provider_error")), requires_audio=True))
    assess(assessor, s["id"])
    assert len(recordings(tmp_path)) == 1


def test_keeping_recordings_stays_opt_in_and_survives_assessment(assessor, monkeypatch, tmp_path):
    monkeypatch.setenv("SPEAKING_KEEP_AUDIO", "1")
    s = create(assessor)
    upload(assessor, s["id"], audio(ASKED, pron={"overall": 70}))
    transcribe(assessor, s["id"])
    assess(assessor, s["id"])
    assert len(recordings(tmp_path)) == 1


def test_the_sweep_removes_unassessed_recordings_after_the_grace_period_only(assessor, tmp_path, monkeypatch):
    s = create(assessor)
    upload(assessor, s["id"], audio(ASKED, pron={"overall": 70}))
    monkeypatch.setattr(clock, "now", lambda: "2026-01-01 10:00:00")
    transcribe(assessor, s["id"])
    assert len(recordings(tmp_path)) == 1
    monkeypatch.setattr(clock, "now", lambda: "2026-01-01 10:05:00")                         # 5 minutes: still inside the 10-minute grace
    assert speaking_service.sweep_expired(main.DB_PATH) == 0 and len(recordings(tmp_path)) == 1
    monkeypatch.setattr(clock, "now", lambda: "2026-01-01 10:11:00")
    assert speaking_service.sweep_expired(main.DB_PATH) == 1 and recordings(tmp_path) == []
    assert speaking_service.sweep_expired(main.DB_PATH) == 0                                  # idempotent
    a = assess(assessor, s["id"]).json()["assessment"]
    assert a["pronunciation"]["error"]["code"] == "recording_unavailable"                      # and the learner is told why


def test_the_sweep_removes_old_failed_sessions_recordings_too(assessor, tmp_path, monkeypatch):
    monkeypatch.setenv("STT_PROVIDER", "none")
    s = create(assessor)
    monkeypatch.setattr(clock, "now", lambda: "2026-01-01 10:00:00")
    upload(assessor, s["id"], audio("x"))
    transcribe(assessor, s["id"])
    assert get(assessor, s["id"]).json()["session"]["stage"] == "failed" and len(recordings(tmp_path)) == 1
    monkeypatch.setattr(clock, "now", lambda: "2026-01-02 09:00:00")                         # 23 hours later
    assert speaking_service.sweep_expired(main.DB_PATH) == 0
    monkeypatch.setattr(clock, "now", lambda: "2026-01-02 11:00:00")                         # 25 hours later
    assert speaking_service.sweep_expired(main.DB_PATH) == 1 and recordings(tmp_path) == []


def test_the_sweep_does_nothing_when_recordings_are_kept_on_purpose(assessor, tmp_path, monkeypatch):
    monkeypatch.setenv("SPEAKING_KEEP_AUDIO", "1")
    s = create(assessor)
    upload(assessor, s["id"], audio(ASKED, pron={"overall": 70}))
    transcribe(assessor, s["id"])
    monkeypatch.setattr(clock, "now", lambda: "2999-01-01 00:00:00")
    assert speaking_service.sweep_expired(main.DB_PATH) == 0 and len(recordings(tmp_path)) == 1


def test_creating_a_session_runs_the_sweep(assessor, tmp_path, monkeypatch):
    s = create(assessor)
    upload(assessor, s["id"], audio(ASKED, pron={"overall": 70}))
    monkeypatch.setattr(clock, "now", lambda: "2026-01-01 10:00:00")
    transcribe(assessor, s["id"])
    monkeypatch.setattr(clock, "now", lambda: "2026-01-01 12:00:00")
    create(assessor)
    assert recordings(tmp_path) == []


@pytest.mark.parametrize("request_that_sweeps", ["prompts", "assess"])
def test_ordinary_requests_also_run_the_sweep_so_an_idle_server_does_not_keep_audio(assessor, tmp_path, monkeypatch, request_that_sweeps):
    s = create(assessor)
    upload(assessor, s["id"], audio(ASKED, pron={"overall": 70}))
    monkeypatch.setattr(clock, "now", lambda: "2026-01-01 10:00:00")
    transcribe(assessor, s["id"])
    assert len(recordings(tmp_path)) == 1
    monkeypatch.setattr(clock, "now", lambda: "2026-01-01 10:30:00")                         # long past the 10-minute grace
    if request_that_sweeps == "prompts":
        assert assessor.get("/api/speaking/prompts").status_code == 200
    else:
        a = assess(assessor, s["id"]).json()["assessment"]
        assert a["pronunciation"]["error"]["code"] == "recording_unavailable"               # swept before the provider looked for it
    assert recordings(tmp_path) == []


def test_a_corrupt_reference_in_the_sweep_is_ignored_not_fatal(assessor, monkeypatch):
    s = create(assessor)
    upload(assessor, s["id"], audio(ASKED, pron={"overall": 70}))
    monkeypatch.setattr(clock, "now", lambda: "2026-01-01 10:00:00")
    transcribe(assessor, s["id"])
    with db() as conn:
        conn.execute("PRAGMA ignore_check_constraints = ON")
        conn.execute("UPDATE speaking_sessions SET audio_ref = '../outside.webm'")
    monkeypatch.setattr(clock, "now", lambda: "2026-01-01 12:00:00")
    assert speaking_service.sweep_expired(main.DB_PATH) == 1


# ---------- earlier phases unaffected ----------
def test_earlier_phases_are_unchanged(client):
    assert client.get("/api/state/demo-alex").status_code == 401          # Phase 14A: no shared demo state
    register(client, "l@example.com")
    client.put("/api/profile", json=PROFILE)
    assert (len(client.get("/api/lessons").json()["lessons"]), len(client.get("/api/situations").json()["situations"]), len(client.get("/api/listening").json()["activities"])) == (7, 8, 15)
    assert client.get("/api/speaking/prompts").status_code == 200 and client.get("/api/recommendations").status_code == 200


# ---------- repository-level scoping: every query is bound to the learner, independently of the API's own checks ----------
def test_every_repository_query_is_scoped_to_the_learner(two):
    from backend.db import connect
    from backend.repositories import pronunciation as prepo
    a, b = two
    s = tr(a, "नमस्ते आप", pron={"overall": 61})
    assess(a, s["id"])
    a_id = rows("SELECT id FROM users WHERE email='l@example.com'")[0][0]
    b_id = rows("SELECT id FROM users WHERE email='b@example.com'")[0][0]
    tid = rows("SELECT id FROM speaking_transcripts")[0][0]
    aid = rows("SELECT id FROM pronunciation_assessments")[0][0]
    with connect(main.DB_PATH) as conn:
        assert prepo.completed_assessment(conn, a_id, s["id"])["id"] == aid and prepo.latest_assessment(conn, a_id, s["id"])["id"] == aid
        assert prepo.best_transcript(conn, a_id, s["id"])["id"] == tid and prepo.transcript_by_id(conn, a_id, s["id"], tid)["id"] == tid
        assert prepo.attempt_count(conn, a_id, s["id"]) == 1
        # the same session id asked for as someone else finds nothing
        assert prepo.completed_assessment(conn, b_id, s["id"]) is None and prepo.latest_assessment(conn, b_id, s["id"]) is None
        assert prepo.best_transcript(conn, b_id, s["id"]) is None and prepo.transcript_by_id(conn, b_id, s["id"], tid) is None
        assert prepo.attempt_count(conn, b_id, s["id"]) == 0
        lang = conn.execute("SELECT id FROM languages WHERE code='hi'").fetchone()[0]
        assert prepo.history(conn, b_id, lang, 10) == []
        totals, by_method = prepo.stats(conn, b_id, lang)
        assert totals["attempts"] == 0 and by_method == []
