"""Pronunciation results are NOT inputs to the Phase 6 weakness, difficulty or recommendation rules: one poor attempt must not
create a weakness, a transcript mismatch is not a pronunciation weakness, and mock/proxy scores must never silently drive
personalization. The only evidence channel is a separate view that admits real 'model' measurements, and nothing reads it yet."""
import pytest

from .conftest import register
from .spk import PROFILE, assess, db
from .test_pronunciation_api import PStub, assessor, learner, result, tr, use_pron  # noqa: F401  (fixtures and helpers)


def snapshot(c):
    return {"weaknesses": c.get("/api/weaknesses").json(), "difficulty": c.get("/api/difficulty").json(),
            "confidence": c.get("/api/confidence").json(), "recommendations": c.get("/api/recommendations").json()}


def kinds(c):
    return [r["kind"] for r in c.get("/api/recommendations").json()["recommendations"]]


def test_one_poor_pronunciation_attempt_creates_no_weakness(assessor):
    before = snapshot(assessor)
    a = assess(assessor, tr(assessor, "कुछ और", pron={"overall": 3})["id"]).json()["assessment"]
    assert a["pronunciation"]["score"] == 3 and a["content_match"]["words_matched"] == 0              # poor on both counts
    assert snapshot(assessor) == before and before["weaknesses"] == {"weaknesses": []}


def test_many_poor_pronunciation_attempts_still_create_no_weakness(assessor):
    before = snapshot(assessor)
    for _ in range(8):
        assess(assessor, tr(assessor, "कुछ और", pron={"overall": 0, "components": {"fluency": 0}, "words": [("नमस्ते", 0)]})["id"])
    assert snapshot(assessor) == before
    assert not [k for k in kinds(assessor) if k.startswith("review")]


def test_a_transcript_mismatch_is_not_a_pronunciation_weakness_or_any_weakness(assessor):
    for text in ("a", "b", "c", "d", "e", "f", "g"):
        assess(assessor, tr(assessor, text, pron={"overall": 90})["id"])
    assert assessor.get("/api/weaknesses").json() == {"weaknesses": []}


def test_mock_scores_do_not_enter_the_evidence_channel(assessor):
    for score in (5, 95):
        assess(assessor, tr(assessor, "x", pron={"overall": score})["id"])
    with db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM pronunciation_assessments WHERE status='completed'").fetchone()[0] == 2
        assert conn.execute("SELECT COUNT(*) FROM learner_pronunciation_evidence").fetchone()[0] == 0


def test_proxy_scores_do_not_either(assessor, monkeypatch):
    p = PStub(result(overall=10.0))              # method 'proxy'
    use_pron(monkeypatch, p)
    for _ in range(3):
        assess(assessor, tr(assessor, "x")["id"])
    with db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM learner_pronunciation_evidence").fetchone()[0] == 0


def test_a_real_model_measurement_is_visible_as_evidence_but_does_not_move_the_phase6_rules_yet(assessor, monkeypatch):
    before = snapshot(assessor)
    p = PStub(result(overall=12.0))
    p.method = "model"
    use_pron(monkeypatch, p)
    for _ in range(4):
        assess(assessor, tr(assessor, "x")["id"])
    with db() as conn:
        rows = conn.execute("SELECT method, overall_score FROM learner_pronunciation_evidence").fetchall()
    assert [tuple(r) for r in rows] == [("model", 12)] * 4                         # it is recorded as pronunciation evidence...
    assert snapshot(assessor) == before                                            # ...and no existing rule reads it (a later phase must opt in)


def test_the_phase6_evidence_views_are_unchanged(assessor):
    assess(assessor, tr(assessor, "x", pron={"overall": 1})["id"])
    with db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM learner_attempts").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM learner_attempt_topics").fetchone()[0] == 0
        assert {r[0] for r in conn.execute("SELECT DISTINCT source FROM learner_attempts")} <= {"lesson", "situation", "listening"}


def test_pronunciation_does_not_disturb_listening_evidence(assessor):
    from .lis import activity_id, answer, wrong_options
    a = activity_id(assessor, "transport-meaning")
    for _ in range(3):
        answer(assessor, a, wrong_options(a)[0])
    assess(assessor, tr(assessor, "x", pron={"overall": 95})["id"])
    assert [w["rule"] for w in assessor.get("/api/weaknesses").json()["weaknesses"]] == ["repeated_item_errors"]
