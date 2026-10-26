"""Helpers for Phase 11 tests: injectable providers (nothing here calls a real model) and answer keys read from the database."""
import time

from backend import main
from backend.ai import registry
from backend.ai.base import AiError, Provider
from backend.ai.mock import MockProvider
from backend.db import connect

from .agekids import make_learner


def db():
    return connect(main.DB_PATH)


class Recorder(Provider):
    """Wraps the built-in provider and records every request it is sent."""
    name = "recorder"

    def __init__(self):
        self.tutor, self.turns, self.feedback = [], [], []
        self.grades, self.micros, self.rewrites, self.ranks = [], [], [], []
        self.inner = MockProvider()

    def tutor_reply(self, req):
        self.tutor.append(req)
        return self.inner.tutor_reply(req)

    def roleplay_reply(self, req):
        self.turns.append(req)
        return self.inner.roleplay_reply(req)

    def roleplay_feedback(self, req):
        self.feedback.append(req)
        return self.inner.roleplay_feedback(req)

    def semantic_grade(self, req):
        self.grades.append(req)
        return self.inner.semantic_grade(req)

    def generate_micro_lesson(self, req):
        self.micros.append(req)
        return self.inner.generate_micro_lesson(req)

    def rewrite_insight(self, req):
        self.rewrites.append(req)
        return self.inner.rewrite_insight(req)

    def rank_recommendations(self, req):
        self.ranks.append(req)
        return self.inner.rank_recommendations(req)

    @property
    def calls(self):
        return len(self.tutor) + len(self.turns) + len(self.feedback)


class Failing(Provider):
    name = "failing"

    def __init__(self, error=AiError("provider_error")):
        self.error, self.calls = error, 0

    def tutor_reply(self, req):
        self.calls += 1
        raise self.error

    roleplay_reply = tutor_reply

    def roleplay_feedback(self, req):
        self.calls += 1
        raise self.error


class Fixed(Provider):
    """Returns whatever it is given for every call (to test validation of provider output)."""
    name = "fixed"

    def __init__(self, value):
        self.value = value

    def tutor_reply(self, req):
        return self.value

    roleplay_reply = tutor_reply

    def roleplay_feedback(self, req):
        return self.value

    # the Phase 12 capabilities return the same scripted value, so "malformed output" tests really reach the validators
    semantic_grade = generate_micro_lesson = rewrite_insight = rank_recommendations = tutor_reply


class Slow(Provider):
    name = "slow"

    def tutor_reply(self, req):
        time.sleep(3)
        return "late"

    roleplay_reply = tutor_reply


def use(monkeypatch, provider):
    monkeypatch.setattr(registry, "FACTORY", lambda: provider)
    return provider


def teen(client, email="teen@example.com"):
    return make_learner(client, email, 14)


def child(client, email="kid@example.com"):
    return make_learner(client, email, 7)


def situation_id(c, slug, language="hi"):
    """A seeded situation's id. Slugs are unique per language (Hindi and Marathi share them): Hindi unless asked."""
    with db() as conn:
        return conn.execute("SELECT id FROM situations WHERE slug = ? AND language_id = (SELECT id FROM languages WHERE code = ?)", (slug, language)).fetchone()[0]


def script(slug):
    """[(step_id, kind, expected_texts)] for a situation, read from the database (the answer key; never from an API response)."""
    with db() as conn:
        sid = conn.execute("SELECT id FROM situations WHERE slug = ? AND language_id = (SELECT id FROM languages WHERE code = 'hi')", (slug,)).fetchone()[0]
        out = []
        for st in conn.execute("SELECT id, kind, item_id FROM situation_steps WHERE situation_id = ? ORDER BY sort_order", (sid,)).fetchall():
            if st["kind"] == "learn_phrase":
                it = conn.execute("SELECT text, pronunciation FROM vocabulary_items WHERE id = ?", (st["item_id"],)).fetchone()
                out.append((st["id"], st["kind"], [it["pronunciation"], it["text"]]))
            else:
                out.append((st["id"], st["kind"], [r[0] for r in conn.execute("SELECT answer_text FROM situation_step_answers WHERE step_id = ? AND is_correct = 1", (st["id"],))]))
        return out


def all_answers(slug):
    return [t for _, _, texts in script(slug) for t in texts if t]


def start(c, slug):
    r = c.post("/api/roleplay/sessions", json={"situation_id": situation_id(c, slug)})
    assert r.status_code in (200, 201), r.text
    return r.json()["session"]


def say(c, session_id, text, **extra):
    return c.post(f"/api/roleplay/sessions/{session_id}/turns", json={"text": text, **extra})


def solve(c, session_id, slug, n=None):
    """Answers the first n steps (default: all) correctly, using the database key."""
    for i, (_, _, texts) in enumerate(script(slug)):
        if n is not None and i >= n:
            break
        r = say(c, session_id, texts[0])
        assert r.status_code == 200 and r.json()["turn"]["verdict"] == "correct", r.text


def fail_step(c, session_id):
    last = None
    for _ in range(3):
        last = say(c, session_id, "zzz wrong zzz")
        assert last.status_code == 200
    return last.json()


# ---------- Phase 12 helpers ----------
class FakeLLM(Provider):
    """Stands in for a real model: returns exactly what the test scripts. name == 'llm', so the services treat it as an external provider."""
    name = "llm"

    def __init__(self, grade=None, micro=None, rewrite=None, rank=None, error=None, tutor="ok"):
        self.grade, self.micro, self.rewrite, self.rank, self.error, self.tutor = grade, micro, rewrite, rank, error, tutor
        self.grades, self.micros, self.rewrites, self.ranks = [], [], [], []

    def _out(self, value, req):
        if self.error is not None:
            raise self.error
        return value(req) if callable(value) else value

    def semantic_grade(self, req):
        self.grades.append(req)
        return self._out(self.grade, req)

    def generate_micro_lesson(self, req):
        self.micros.append(req)
        return self._out(self.micro, req)

    def rewrite_insight(self, req):
        self.rewrites.append(req)
        return self._out(self.rewrite, req)

    def rank_recommendations(self, req):
        self.ranks.append(req)
        return self._out(self.rank, req)

    def tutor_reply(self, req):
        return self.tutor

    def roleplay_reply(self, req):
        return "In character."

    def roleplay_feedback(self, req):
        return {"vocabulary_feedback": "v", "grammar_feedback": "g", "hint": "h", "encouragement": "e", "next_step": "n"}


def grade_json(match=True, confidence=0.95, explanation="Same meaning.", missing="", grammar=""):
    return {"semantic_match": match, "confidence": confidence, "explanation": explanation, "missing_objective": missing, "grammar_feedback": grammar}
