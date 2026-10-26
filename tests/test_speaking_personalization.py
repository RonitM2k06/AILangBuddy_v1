"""Speaking attempts are deliberately NOT performance evidence in Phase 7B: a transcript that differs from the prompt is not a
learner error (recognisers mis-hear; Hindi may come back in either script), so counting it would invent weaknesses. These tests
pin that decision so a later phase has to change it on purpose."""
import pytest

from backend.personalization import clock
from backend.speaking.stt import SttError

from .conftest import register
from .spk import PROFILE, create, db, run_flow, transcribe, upload
from .test_speaking_api import Stub, raising, use


@pytest.fixture
def speaker(client, monkeypatch):
    monkeypatch.setenv("STT_PROVIDER", "mock")
    register(client, "l@example.com")
    client.put("/api/profile", json=PROFILE)
    return client


def snapshot(c):
    return {"weaknesses": c.get("/api/weaknesses").json(), "difficulty": c.get("/api/difficulty").json(),
            "confidence": c.get("/api/confidence").json(), "recommendations": c.get("/api/recommendations").json()}


def test_the_performance_views_do_not_read_speaking_tables(db_path):
    from backend.db import connect
    with connect(db_path) as conn:
        sql = " ".join(r["sql"] for r in conn.execute("SELECT sql FROM sqlite_master WHERE type='view' AND name IN ('learner_attempts', 'learner_attempt_topics')"))   # the Phase 6 performance views
    assert "speaking" not in sql and "stt_" not in sql and "audio_sessions" not in sql


def test_speaking_sessions_add_no_performance_evidence(speaker):
    before = snapshot(speaker)
    for _ in range(3):
        run_flow(speaker, "a transcript nothing like the prompt")            # completed sessions with mismatching text
    with db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM learner_attempts").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM learner_attempt_topics").fetchone()[0] == 0
    after = snapshot(speaker)
    assert after["weaknesses"] == before["weaknesses"] == {"weaknesses": []}
    assert after["difficulty"] == before["difficulty"] and after["confidence"] == before["confidence"]


def test_many_mismatching_or_failed_sessions_never_create_a_weakness(speaker, monkeypatch):
    for i in range(8):
        run_flow(speaker, f"wrong words {i}")
    use(monkeypatch, Stub(raising(SttError("provider_error", "x"))))
    for _ in range(4):
        s = create(speaker)
        upload(speaker, s["id"])
        transcribe(speaker, s["id"])
    assert speaker.get("/api/weaknesses").json() == {"weaknesses": []}
    assert not [r for r in speaker.get("/api/recommendations").json()["recommendations"] if r["kind"].startswith("review")]


def test_a_transcript_equal_to_the_prompt_is_not_labelled_correct_either(speaker):
    prompt = speaker.get("/api/speaking/prompts").json()["prompts"][0]["item"]
    done = run_flow(speaker, prompt["text"])
    assert done["transcript"]["text"] == prompt["text"]
    assert all(k not in done for k in ("correct", "match", "score", "accuracy"))
    with db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM learner_attempts").fetchone()[0] == 0


def test_listening_and_lesson_evidence_still_flows_as_before(speaker):
    from .lis import activity_id, answer, wrong_options
    a = activity_id(speaker, "transport-meaning")
    for _ in range(3):
        answer(speaker, a, wrong_options(a)[0])
    run_flow(speaker, "unrelated")
    w = speaker.get("/api/weaknesses").json()["weaknesses"]
    assert [x["rule"] for x in w] == ["repeated_item_errors"]                # from listening only; the speaking session added nothing
