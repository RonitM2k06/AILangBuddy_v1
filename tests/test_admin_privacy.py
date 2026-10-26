"""Phase 13: privacy canaries. Everything private a learner, parent or deployment holds is seeded with a marker string; then EVERY admin GET endpoint is requested
(and the responses of the writes are scanned too). No marker may appear, no response may carry a forbidden key, and none may carry a filesystem path.
The test does not rely on remembering which fields are sensitive: it plants the values and looks for them."""
import json
import re
from datetime import datetime, timezone

import pytest
from fastapi.routing import APIRoute

from backend import main
from backend.admin import analytics
from backend.db import connect

from . import adm
from .adm import admin, learners, new_activity, new_lesson, new_situation, ok  # noqa: F401
from .test_admin_security import admin_routes

CANARY = {
    "tutor_message": "CANARY-TUTOR-MESSAGE-7f3a", "tutor_fact": "CANARY-TUTOR-FACT-1b2c", "transcript": "CANARY-TRANSCRIPT-9d8e", "email": "canary.person@private-canary.example",
    "name": "Canary Personname", "password_hash": "CANARY-PASSWORD-HASH-4c4c", "session_hash": "CANARY-SESSION-HASH-5d5d", "recording": "canaryrecording5e5e.webm",
    "api_key": "CANARY-API-KEY-6f6f", "ollama": "http://canary-ollama-host.internal:11434", "roleplay": "CANARY-ROLEPLAY-TEXT-8a8a", "roleplay_reply": "CANARY-CHARACTER-REPLY-9b9b",
    "parent_email": "canary.parent@private-canary.example", "dob": "1987-06-05", "micro_question": "CANARY-MICRO-QUESTION-aa11", "recommendation": "CANARY-RECOMMENDATION-TEXT-bb22",
    "handle": "canary_handle_cc33", "feedback": "CANARY-FEEDBACK-dd44", "insight": "CANARY-INSIGHT-ee55", "friend_code": "CANARYFRIEND1", "lesson_edit": "CANARY-ADMIN-TYPED-TITLE-ff66",
}
FORBIDDEN_KEYS = {"password", "password_hash", "hash", "token", "token_hash", "session", "session_id", "email", "display_name", "handle", "date_of_birth", "dob", "audio_ref", "audio_path",
                  "transcript", "recording", "api_key", "secret", "user_id", "learner_id", "parent_id", "parent", "url", "hostname", "friend_code"}


@pytest.fixture
def seeded(admin, monkeypatch, tmp_path):
    monkeypatch.setattr(analytics, "utcnow", lambda: datetime(2026, 3, 15, 12, 0, 0, tzinfo=timezone.utc))
    monkeypatch.setenv("GROQ_API_KEY", CANARY["api_key"])
    monkeypatch.setenv("OLLAMA_URL", CANARY["ollama"])
    monkeypatch.setenv("RECORDINGS_DIR", str(tmp_path / "canary-recordings-dir"))
    monkeypatch.setenv("ADMIN_REF_SECRET", "canary-reference-secret")
    at = "2026-03-10 10:00:00"
    with connect(main.DB_PATH) as conn:
        people = learners(conn, 7, dob=CANARY["dob"], created="2026-03-01 00:00:00")
        sid, lid = adm.situation_id(conn), adm.lesson_id(conn)
        for n, u in enumerate(people):
            conn.execute("UPDATE users SET email = ?, display_name = ?, password_hash = ?, handle = ? WHERE id = ?",
                         (f"{n}.{CANARY['email']}", f"{CANARY['name']} {n}", CANARY["password_hash"], f"{CANARY['handle']}{n}", u))
            adm.sessions.create(conn, u, f"{CANARY['session_hash']}{n}", at, "2099-01-01 00:00:00")
            conn.execute("INSERT INTO learner_gamification(user_id, friend_code, created_at) VALUES (?, ?, ?)", (u, f"{CANARY['friend_code']}"[:9] + str(n), at))
            adm.lesson_progress(conn, u, lid, started=at, completed=at)
            adm.exercise_attempt(conn, u, adm.first_exercise(conn, lid), correct=n % 2, at=at)
            adm.situation_progress(conn, u, sid, started=at, completed=at)
            adm.step_attempt(conn, u, adm.first_step(conn, sid), at=at)
            adm.weakness(conn, u)
            adm.self_report(conn, u, "food", 50 + n, at)
            adm.achievement(conn, u, 0, at)
            adm.xp(conn, u, 1200 + n, earned=at)
            adm.recommendation(conn, u, at)
            conn.execute("UPDATE ai_recommendations SET title = ?, reason = ?, note = ? WHERE user_id = ?", (CANARY["recommendation"], CANARY["recommendation"], CANARY["recommendation"], u))
            ml = adm.micro_lesson(conn, u, at, attempts=[(at, True)])
            conn.execute("UPDATE ai_micro_lessons SET question = ? WHERE id = ?", (CANARY["micro_question"], ml))
            conn.execute("INSERT INTO ai_learning_insights(user_id, language_id, day, kind, subject, text, source, created_at) VALUES (?, 10, '2026-03-10', 'accuracy_trend', '', ?, 'rules', ?)",
                         (u, CANARY["insight"], at))
            cid = conn.execute("INSERT INTO tutor_conversations(user_id, language_id, cefr_code, mode, title, status, message_count, created_at, updated_at) VALUES (?, 10, 'A1', 'adult', 'Chat', 'active', 2, ?, ?)", (u, at, at)).lastrowid
            m1 = conn.execute("INSERT INTO tutor_messages(conversation_id, user_id, seq, role, content, created_at) VALUES (?, ?, 1, 'learner', ?, ?)", (cid, u, CANARY["tutor_message"], at)).lastrowid
            conn.execute("INSERT INTO tutor_messages(conversation_id, user_id, seq, role, content, provider, created_at) VALUES (?, ?, 2, 'tutor', ?, 'mock', ?)", (cid, u, CANARY["tutor_message"], at))
            conn.execute("INSERT INTO tutor_message_facts(message_id, ord, kind, text) VALUES (?, 1, 'context', ?)", (m1, CANARY["tutor_fact"]))
            rs = adm.roleplay_session(conn, u, sid, status="completed", missed=0, at=at)
            tid = adm.roleplay_turn(conn, u, rs, sid, adm.first_step(conn, sid), at=at, text=CANARY["roleplay"])
            conn.execute("UPDATE roleplay_turns SET character_reply = ?, hint = ? WHERE id = ?", (CANARY["roleplay_reply"], CANARY["feedback"], tid))
            conn.execute("INSERT INTO roleplay_feedback(session_id, user_id, steps_total, steps_correct, steps_missed, first_try_correct, voice_turns, correctness_text, vocabulary_feedback, "
                         "grammar_feedback, hint, encouragement, next_step, pronunciation_note, provider, created_at) VALUES (?, ?, (SELECT steps_total FROM roleplay_sessions WHERE id = ?), "
                         "(SELECT steps_total FROM roleplay_sessions WHERE id = ?), 0, 1, 0, ?, ?, ?, ?, ?, ?, ?, 'mock', ?)", (rs, u, rs, rs, CANARY["feedback"], CANARY["feedback"], CANARY["feedback"],
                                                                                                                             CANARY["feedback"], CANARY["feedback"], CANARY["feedback"], CANARY["feedback"], at))
            spk = adm.pronunciation(conn, u, at)
            conn.execute("UPDATE speaking_transcripts SET text = ? WHERE session_id = ?", (CANARY["transcript"], spk))
            conn.execute("UPDATE speaking_sessions SET audio_ref = ? WHERE session_id = ?", (CANARY["recording"], spk))
        parent = adm.add_user(conn, "parent", email=CANARY["parent_email"])
        conn.execute("INSERT INTO parent_links(parent_id, learner_id, created_at) VALUES (?, ?, ?)", (parent, people[0], at))
    return people


def fill(path, refs):
    values = {"lesson_id": 1, "situation_id": 1, "activity_id": 1, "exercise_id": 1, "step_id": 1, "option_id": 1, "item_id": 1, "topic_id": 1, "event_id": 1, "entity_id": 1,
              "ref": refs[0], "language_code": "en", "entity_type": "lesson"}
    return re.sub(r"\{(\w+)\}", lambda m: str(values[m.group(1)]), path)


def walk_keys(obj, found):
    if isinstance(obj, dict):
        for k, v in obj.items():
            found.add(k.lower())
            walk_keys(v, found)
    elif isinstance(obj, list):
        for v in obj:
            walk_keys(v, found)


# Until Phase 14E, GET /api/admin/users (Phase 2) was the one admin route excluded from the scan: it returned every account's e-mail, handle and name. Phase 14E narrowed
# it to opaque references, roles, creation dates and two-factor status, so it is scanned like every other admin route and no exception remains.
LEGACY_UNSCANNED = set()


def get_endpoints():
    return sorted({r.path for r in admin_routes() if "GET" in r.methods} - LEGACY_UNSCANNED)


def refs_of(admin):
    return [i["ref"] for i in admin.get("/api/admin/learners").json()["items"]]


def scan(label, text, tmp_path):
    for name, value in CANARY.items():
        assert value not in text and value.lower() not in text.lower(), f"{label} leaked the {name} canary"
    for frag in (str(tmp_path), "canary-recordings-dir", "buddy.db", "/Users/", "/private/", "/var/folders", "canary-reference-secret"):
        assert frag not in text, f"{label} leaked a path or secret fragment: {frag}"
    try:
        doc = json.loads(text)
    except ValueError:
        return
    keys = set()
    walk_keys(doc, keys)
    assert not (keys & FORBIDDEN_KEYS), f"{label} carries forbidden keys: {sorted(keys & FORBIDDEN_KEYS)}"


def test_the_canaries_really_are_in_the_database(seeded):
    """Guard against a vacuous scan: every planted value exists in the database the endpoints read."""
    with connect(main.DB_PATH) as conn:
        dump = " ".join(str(tuple(r)) for t in ("users", "sessions", "tutor_messages", "tutor_message_facts", "speaking_transcripts", "speaking_sessions", "roleplay_turns", "roleplay_feedback",
                                                  "ai_recommendations", "ai_micro_lessons", "ai_learning_insights", "learner_gamification", "learner_profiles")
                        for r in conn.execute(f"SELECT * FROM {t}"))
    for name in ("tutor_message", "tutor_fact", "transcript", "email", "name", "password_hash", "session_hash", "recording", "roleplay", "roleplay_reply", "parent_email", "dob", "micro_question",
                 "recommendation", "handle", "feedback", "insight"):
        assert CANARY[name] in dump, name


def test_every_get_endpoint_is_free_of_every_canary(seeded, admin, tmp_path):
    refs = refs_of(admin)
    assert len(refs) == 7
    # a few writes first, so the audit log and the lifecycle have content too (typed values here are marked as well)
    lesson = new_lesson(admin, "privacy-lesson", title=CANARY["lesson_edit"])
    ok(admin.patch(f"/api/admin/content/lessons/{lesson['id']}", {"revision": lesson["revision"], "title": CANARY["lesson_edit"] + " v2"}))
    ok(admin.post(f"/api/admin/publish/lesson/{lesson['id']}", {"revision": lesson["revision"] + 1}))
    checked = []
    for template in get_endpoints():
        url = fill(template, refs)
        r = admin.get(url)
        assert r.status_code in (200, 404), (url, r.status_code, r.text[:200])
        text = r.text
        if template != "/api/admin/content/lessons/{lesson_id}" and "content/lessons" not in template and "audit" not in template and "validate" not in template:
            scan(url, text, tmp_path)
        else:
            # content the admin typed is the admin's own: only the learner-private markers must be absent there
            for name, value in CANARY.items():
                if name != "lesson_edit":
                    assert value not in text, f"{url} leaked the {name} canary"
            keys = set()
            walk_keys(json.loads(text), keys)
            assert not keys & FORBIDDEN_KEYS, (url, keys & FORBIDDEN_KEYS)
        checked.append(template)
    assert len(checked) >= 25 and "/api/admin/learners/{ref}" in checked and "/api/admin/audit" in checked


def test_the_audit_log_never_holds_what_the_admin_typed_or_what_learners_hold(seeded, admin, tmp_path):
    lesson = new_lesson(admin, "audit-privacy", title=CANARY["lesson_edit"], description=CANARY["lesson_edit"])
    ok(admin.patch(f"/api/admin/content/lessons/{lesson['id']}", {"revision": lesson["revision"], "title": CANARY["lesson_edit"] + "2", "tip": CANARY["lesson_edit"]}))
    with connect(main.DB_PATH) as conn:
        dump = " ".join(str(tuple(r)) for r in conn.execute("SELECT * FROM admin_audit_log"))
    assert dump and not any(v.lower() in dump.lower() for v in CANARY.values())
    text = admin.get("/api/admin/audit?limit=100").text
    assert not any(v.lower() in text.lower() for v in CANARY.values()) and "@" not in text


def test_every_analytics_view_over_every_window_is_free_of_canaries(seeded, admin, tmp_path):
    for window in ("7d", "30d", "90d"):
        for name in ("learning", "speaking", "confidence-weakness", "engagement", "adaptive", "content-performance", "activity"):
            r = admin.get(f"/api/admin/analytics/{name}?window={window}")
            assert r.status_code == 200
            scan(f"{name}?{window}", r.text, tmp_path)
        scan(f"dashboard?{window}", admin.get(f"/api/admin/dashboard?window={window}").text, tmp_path)
    for kind in ("lesson", "situation", "listening"):
        scan(kind, admin.get(f"/api/admin/analytics/content-performance?kind={kind}&window=90d").text, tmp_path)


def test_the_learner_list_and_detail_expose_no_identity_at_all(seeded, admin, tmp_path):
    page = admin.get("/api/admin/learners?limit=100").json()
    assert page["total"] == 7
    for item in page["items"]:
        assert set(item) == {"ref", "language", "cefr", "age_group", "joined", "last_active", "lessons_completed", "situations_completed", "exercise_attempts"}
        detail = admin.get(f"/api/admin/learners/{item['ref']}")
        assert detail.status_code == 200
        scan("learner detail", detail.text, tmp_path)
    scan("learner list", admin.get("/api/admin/learners?limit=100").text, tmp_path)


def test_content_write_responses_are_free_of_learner_data(seeded, admin, tmp_path):
    lesson = new_lesson(admin, "write-privacy")
    sit = new_situation(admin, "write-privacy-s")
    act = new_activity(admin, "write-privacy-a")
    for body in (lesson, sit, act):
        scan("create response", json.dumps(body), tmp_path)
    for url, payload in ((f"/api/admin/publish/lesson/{lesson['id']}", {"revision": lesson["revision"]}), (f"/api/admin/validate/situation/{sit['id']}", {}),
                         (f"/api/admin/archive/listening_activity/{act['id']}", {"revision": act["revision"]})):
        scan(url, admin.post(url, payload).text, tmp_path)


def test_the_health_page_shows_booleans_not_the_planted_secrets(seeded, admin, tmp_path):
    r = admin.get("/api/admin/health")
    assert r.json()["providers"]["llm_configured"] is True
    scan("health", r.text, tmp_path)
    assert "canary" not in r.text.lower()


def test_forbidden_response_keys_are_checked_against_a_real_example(seeded, admin):
    """The key scan can fail: a document that does carry one is caught (so a passing scan means something)."""
    found = set()
    walk_keys({"items": [{"ref": "x", "email": "a@b"}], "nested": {"Password": "p"}}, found)
    assert found & FORBIDDEN_KEYS == {"email", "password"}


def test_the_account_listing_no_longer_exposes_identity(seeded, admin):
    """Phase 14E: GET /api/admin/users returns references, roles, creation dates and two-factor status only, and is in the canary scan above."""
    assert "/api/admin/users" in get_endpoints() and not LEGACY_UNSCANNED
    r = admin.get("/api/admin/users?limit=100")
    assert r.status_code == 200
    items = r.json()["items"]
    assert items and {frozenset(u) for u in items} == {frozenset({"ref", "roles", "created", "two_factor"})}
    text = r.text
    for secret in (CANARY["email"], CANARY["name"], CANARY["handle"], CANARY["password_hash"], CANARY["session_hash"], CANARY["api_key"], CANARY["transcript"],
                   CANARY["tutor_message"], CANARY["recording"], CANARY["roleplay"], CANARY["dob"], "@example.com", "password", "token", "hash", "demo-alex"):
        assert secret not in text, secret
