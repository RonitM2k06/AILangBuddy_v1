"""Helpers for Phase 13 (admin CMS + analytics) tests. Evidence is written with plain SQL so a test controls every column; the answer keys are
read from the database, never from an API response."""
import itertools
import sqlite3

import pytest

from backend.db import connect

HI, EN = "(SELECT id FROM languages WHERE code='hi')", "(SELECT id FROM languages WHERE code='en')"
STAMP = "2026-01-15 10:00:00"
_ids = itertools.count(1)


def one(conn, sql, *args):
    return conn.execute(sql, args).fetchone()[0]


def raises_integrity(db_path, sql, *args):
    """The statement is refused by the database itself, and (because connect() rolls back) leaves nothing behind."""
    with pytest.raises(sqlite3.IntegrityError):
        with connect(db_path) as conn:
            conn.execute(sql, args)


def add_user(conn, role="learner", handle=None, email=None):
    n = next(_ids)
    handle = handle or f"t_user_{n}"
    email = email or f"{handle}@example.com"
    uid = conn.execute("INSERT INTO users(handle, display_name, email, password_hash) VALUES (?, ?, ?, 'x')", (handle, f"User {n}", email)).lastrowid
    conn.execute("INSERT INTO user_roles(user_id, role_id) SELECT ?, id FROM roles WHERE name = ?", (uid, role))
    return uid


def add_profile(conn, uid, target="hi", level="A1", dob="2000-01-01", native="en", updated="2026-01-01 00:00:00"):
    conn.execute(
        "INSERT INTO learner_profiles(user_id, native_language_id, target_language_id, cefr_level, date_of_birth, updated_at) "
        "VALUES (?, (SELECT id FROM languages WHERE code=?), (SELECT id FROM languages WHERE code=?), ?, ?, ?)",
        (uid, native, target, level, dob, updated))


# Slugs are unique per language (Hindi and Marathi share them): these find the seeded Hindi unit unless asked for another language.
_LANG = "(SELECT id FROM languages WHERE code = ?)"


def lesson_id(conn, slug="food", language="hi"):
    return one(conn, f"SELECT id FROM lessons WHERE slug = ? AND language_id = {_LANG}", slug, language)


def situation_id(conn, slug="food", language="hi"):
    return one(conn, f"SELECT id FROM situations WHERE slug = ? AND language_id = {_LANG}", slug, language)


def activity_id(conn, slug="food-meaning", language="hi"):
    return one(conn, f"SELECT id FROM listening_activities WHERE slug = ? AND language_id = {_LANG}", slug, language)


# ---------- learner evidence, one builder per evidence table ----------
def lesson_progress(conn, uid, lid, started=STAMP, completed=None):
    conn.execute("INSERT INTO lesson_progress(user_id, lesson_id, started_at, completed_at) VALUES (?, ?, ?, ?)", (uid, lid, started, completed))


def exercise_attempt(conn, uid, exercise_id, correct=0, at=STAMP):
    return conn.execute("INSERT INTO exercise_attempts(user_id, exercise_id, answer_id, submitted_text, is_correct, attempted_at) VALUES (?, ?, NULL, 'x', ?, ?)",
                        (uid, exercise_id, correct, at)).lastrowid


def first_exercise(conn, lid):
    return one(conn, "SELECT id FROM exercises WHERE lesson_id = ? ORDER BY sort_order LIMIT 1", lid)


def situation_progress(conn, uid, sid, started=STAMP, completed=None):
    conn.execute("INSERT INTO situation_progress(user_id, situation_id, started_at, completed_at) VALUES (?, ?, ?, ?)", (uid, sid, started, completed))


def step_attempt(conn, uid, step_id, correct=0, at=STAMP):
    return conn.execute("INSERT INTO situation_step_attempts(user_id, step_id, answer_id, submitted_text, is_correct, attempted_at) VALUES (?, ?, NULL, 'x', ?, ?)",
                        (uid, step_id, correct, at)).lastrowid


def first_step(conn, sid, kinds=("choose_response", "translate", "fill_blank", "conversation")):
    marks = ",".join("?" * len(kinds))
    return one(conn, f"SELECT id FROM situation_steps WHERE situation_id = ? AND kind IN ({marks}) ORDER BY sort_order LIMIT 1", sid, *kinds)


def daily_task(conn, uid, lid=None, sid=None, tid=None, status="done", day="2026-01-15", priority=1):
    kind = "study_lesson" if lid else "practice_situation" if sid else "confidence_checkin"
    source = {"study_lesson": "next_lesson", "practice_situation": "next_situation", "confidence_checkin": "confidence_checkin"}[kind]
    conn.execute(
        "INSERT INTO daily_tasks(user_id, language_id, plan_date, priority, task_type, source, lesson_id, situation_id, topic_id, status, created_at, completed_at) "
        f"VALUES (?, {HI}, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (uid, day, priority, kind, source, lid, sid, tid, status, STAMP, STAMP if status == "done" else None))


def audio_session(conn, uid, kind="listening", at=STAMP):
    return conn.execute(f"INSERT INTO audio_sessions(user_id, language_id, kind, status, started_at, ended_at, duration_ms) VALUES (?, {HI}, ?, 'completed', ?, ?, 1)",
                        (uid, kind, at, at)).lastrowid


def listening_attempt(conn, uid, aid, option_id, correct=0, at=STAMP):
    return conn.execute("INSERT INTO listening_attempts(user_id, session_id, activity_id, option_id, is_correct, plays, attempted_at) VALUES (?, ?, ?, ?, ?, 1, ?)",
                        (uid, audio_session(conn, uid, "listening", at), aid, option_id, correct, at)).lastrowid


def wrong_option(conn, aid):
    return one(conn, "SELECT o.id FROM listening_options o JOIN listening_activities a ON a.id = o.activity_id WHERE a.id = ? AND o.item_id <> a.item_id ORDER BY o.sort_order LIMIT 1", aid)


def right_option(conn, aid):
    return one(conn, "SELECT o.id FROM listening_options o JOIN listening_activities a ON a.id = o.activity_id WHERE a.id = ? AND o.item_id = a.item_id", aid)


def roleplay_session(conn, uid, sid, status="active", correct=None, missed=None, at=STAMP, mode="adult"):
    total = one(conn, "SELECT COUNT(*) FROM situation_steps WHERE situation_id = ?", sid)
    if status == "completed":
        missed = missed or 0
        correct = total - missed                                                    # the table requires steps_correct + steps_missed = steps_total
    done = at if status == "completed" else None
    return conn.execute(
        f"INSERT INTO roleplay_sessions(user_id, situation_id, language_id, cefr_code, mode, status, steps_total, steps_correct, steps_missed, created_at, completed_at) "
        f"VALUES (?, ?, {HI}, 'A1', ?, ?, ?, ?, ?, ?, ?)", (uid, sid, mode, status, total, correct, missed, at, done)).lastrowid


def roleplay_turn(conn, uid, session_id, sid, step_id, turn_no=1, at=STAMP, text="private roleplay words"):
    return conn.execute(
        "INSERT INTO roleplay_turns(session_id, user_id, situation_id, step_id, turn_no, attempt_no, learner_text, input_mode, verdict, resolved, character_reply, provider, created_at) "
        "VALUES (?, ?, ?, ?, ?, 1, ?, 'text', 'correct', 'correct', 'reply', 'mock', ?)", (session_id, uid, sid, step_id, turn_no, text, at)).lastrowid


def weakness(conn, uid, topic_slug="food", status="active"):
    conn.execute(
        f"INSERT INTO weaknesses(user_id, language_id, rule, topic_id, item_id, severity, attempts, incorrect, last_evidence_at, detected_at, status, resolved_at) "
        f"VALUES (?, {HI}, 'low_topic_accuracy', (SELECT id FROM topics WHERE slug = ?), NULL, 'low', 6, 3, ?, ?, ?, ?)",
        (uid, topic_slug, STAMP, STAMP, status, STAMP if status == "resolved" else None))


def item_weakness(conn, uid, item_id):
    conn.execute(
        f"INSERT INTO weaknesses(user_id, language_id, rule, topic_id, item_id, severity, attempts, incorrect, last_evidence_at, detected_at, status, resolved_at) "
        f"VALUES (?, {HI}, 'repeated_item_errors', NULL, ?, 'low', 6, 3, ?, ?, 'active', NULL)", (uid, item_id, STAMP, STAMP))


def xp(conn, uid, source_id, kind="exercise", amount=5, earned=STAMP):
    conn.execute("INSERT INTO xp_events(user_id, kind, source_id, xp, earned_at, day, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                 (uid, kind, source_id, amount, earned, earned[:10], earned))


# ---------- API helpers ----------
import pytest as _pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from backend import main  # noqa: E402
from backend.auth import service  # noqa: E402
from backend.repositories import sessions  # noqa: E402

from .conftest import PASSWORD  # noqa: E402

CSRF = {"X-Requested-With": "XMLHttpRequest"}


class Api:
    """A browser. Writes carry the admin CSRF header unless csrf=False; the body is always JSON (an empty object when none is given)."""

    def __init__(self, client=None, csrf=True):
        self.c = client or TestClient(main.app)
        self.csrf = csrf

    def _h(self, extra=None):
        return {**(CSRF if self.csrf else {}), **(extra or {})}

    def get(self, url, **kw):
        return self.c.get(url, **kw)

    def post(self, url, json=None, **kw):
        return self.c.post(url, json={} if json is None else json, headers=self._h(kw.pop("headers", None)), **kw)

    def patch(self, url, json=None, **kw):
        return self.c.patch(url, json={} if json is None else json, headers=self._h(kw.pop("headers", None)), **kw)

    def put(self, url, json=None, **kw):
        return self.c.put(url, json={} if json is None else json, headers=self._h(kw.pop("headers", None)), **kw)

    def delete(self, url, **kw):
        # like frontend/admin.js, which sends the JSON content type on every non-GET call
        return self.c.delete(url, headers={"Content-Type": "application/json", **self._h(kw.pop("headers", None))}, **kw)


def _login(email):
    """A signed-in admin whose session passed a second factor (Phase 14D: the admin API requires it). The password still has to be right."""
    c = TestClient(main.app)                                                     # bare: the admin CSRF tests send (or omit) the headers themselves
    r = c.post("/api/auth/login", json={"email": email, "password": PASSWORD}, headers=CSRF)
    assert r.status_code == 200, r.text
    from .conftest import plant_mfa_session
    return plant_mfa_session(c, email)


def admin_browser(make_admin, email="admin@example.com"):
    make_admin(email)
    return Api(_login(email))


def register_browser(role, email):
    from .conftest import register
    c = TestClient(main.app)
    register(c, email, role=role)
    return Api(c)


def demo_browser():
    """A real session for the demo learner (the demo user cannot log in: it has no password), to prove the demo account is refused too."""
    c = TestClient(main.app)
    token, token_hash = service._new_token()
    with connect(main.DB_PATH) as conn:
        uid = conn.execute("SELECT id FROM users WHERE handle = 'demo-alex'").fetchone()[0]
        now = service.utcnow()                                                  # a fresh session: since Phase 14C an idle one would have ended
        sessions.create(conn, uid, token_hash, service._fmt(now), service._fmt(now + service.timedelta(days=1)))
    c.cookies.set("llb_session", token)
    return Api(c)


@_pytest.fixture
def admin(client, make_admin):
    return admin_browser(make_admin)


@_pytest.fixture
def audit_rows(client):
    def read(**where):
        clause = " AND ".join(f"{k} = ?" for k in where) or "1"
        with connect(main.DB_PATH) as conn:
            return [dict(r) for r in conn.execute(f"SELECT * FROM admin_audit_log WHERE {clause} ORDER BY id", tuple(where.values()))]
    return read


# ---------- complete, valid content built with SQL (so a test can break exactly one thing) ----------
def usable_items(conn, n=3):
    """Hindi A1 items that have an English translation (the targets of seeded listening activities)."""
    rows = conn.execute("SELECT DISTINCT a.item_id FROM listening_activities a JOIN vocabulary_translations t ON t.item_id = a.item_id AND t.language_id = 1 "
                        "WHERE a.language_id = 10 ORDER BY a.item_id").fetchall()
    return [r[0] for r in rows][:n]


def next_sort(conn, table, language=10, cefr="A1"):
    return one(conn, f"SELECT COALESCE(MAX(sort_order), 0) + 1 FROM {table} WHERE language_id = ? AND cefr_code = ?", language, cefr)


def make_lesson(conn, slug="zz-lesson", status="draft", exercises=1, title=None):
    item = usable_items(conn, 1)[0]
    published = "'2026-01-01 00:00:00'" if status == "published" else "NULL"
    archived = "'2026-01-01 00:00:00'" if status == "archived" else "NULL"
    lid = conn.execute(
        f"INSERT INTO lessons(language_id, cefr_code, slug, title, description, sort_order, status, published_at, archived_at, updated_at) "
        f"VALUES (10, 'A1', ?, ?, 'd', ?, ?, {published}, {archived}, '2026-01-01 00:00:00')",
        (slug, title or f"Lesson {slug}", next_sort(conn, "lessons"), status)).lastrowid
    conn.execute("INSERT INTO lesson_topics(lesson_id, topic_id) SELECT ?, id FROM topics WHERE slug = 'food'", (lid,))
    conn.execute("INSERT INTO lesson_vocabulary(lesson_id, item_id, language_id, sort_order) VALUES (?, ?, 10, 1)", (lid, item))
    for n in range(1, exercises + 1):
        eid = conn.execute("INSERT INTO exercises(lesson_id, language_id, kind, prompt, item_id, sort_order, difficulty) VALUES (?, 10, 'multiple_choice', ?, ?, ?, 1)",
                           (lid, f"Which is right {slug} {n}?", item, n)).lastrowid
        for k, (text, ok) in enumerate([("right", 1), ("wrong one", 0), ("wrong two", 0)], 1):
            conn.execute("INSERT INTO exercise_answers(exercise_id, answer_text, is_correct, sort_order) VALUES (?, ?, ?, ?)", (eid, f"{text} {n}", ok, k))
    return lid


def make_situation(conn, slug="zz-situation", status="draft", steps=2):
    item = usable_items(conn, 1)[0]
    published = "'2026-01-01 00:00:00'" if status == "published" else "NULL"
    archived = "'2026-01-01 00:00:00'" if status == "archived" else "NULL"
    sid = conn.execute(
        f"INSERT INTO situations(language_id, cefr_code, topic_id, slug, title, description, difficulty, sort_order, status, published_at, archived_at, updated_at) "
        f"VALUES (10, 'A1', (SELECT id FROM topics WHERE slug = 'food'), ?, ?, 'd', 1, ?, ?, {published}, {archived}, '2026-01-01 00:00:00')",
        (slug, f"Situation {slug}", next_sort(conn, "situations"), status)).lastrowid
    conn.execute("INSERT INTO situation_steps(situation_id, language_id, sort_order, kind, item_id) VALUES (?, 10, 1, 'learn_phrase', ?)", (sid, item))
    for n in range(2, steps + 1):
        step = conn.execute("INSERT INTO situation_steps(situation_id, language_id, sort_order, kind, prompt, prompt_meaning) VALUES (?, 10, ?, 'choose_response', ?, 'm')",
                            (sid, n, f"Say something {slug} {n}")).lastrowid
        for k, (text, ok) in enumerate([("good reply", 1), ("bad reply", 0)], 1):
            conn.execute("INSERT INTO situation_step_answers(step_id, answer_text, is_correct, sort_order) VALUES (?, ?, ?, ?)", (step, f"{text} {n}", ok, k))
    return sid


def make_activity(conn, slug="zz-activity", status="draft", mode="choose_meaning"):
    items = usable_items(conn, 3)
    published = "'2026-01-01 00:00:00'" if status == "published" else "NULL"
    archived = "'2026-01-01 00:00:00'" if status == "archived" else "NULL"
    aid = conn.execute(
        f"INSERT INTO listening_activities(language_id, cefr_code, topic_id, item_id, slug, title, mode, prompt, difficulty, sort_order, status, published_at, archived_at, updated_at) "
        f"VALUES (10, 'A1', (SELECT id FROM topics WHERE slug = 'food'), ?, ?, ?, ?, 'Listen', 1, ?, ?, {published}, {archived}, '2026-01-01 00:00:00')",
        (items[0], slug, f"Activity {slug}", mode, next_sort(conn, "listening_activities"), status)).lastrowid
    for k, item in enumerate(items, 1):
        conn.execute("INSERT INTO listening_options(activity_id, language_id, item_id, sort_order) VALUES (?, 10, ?, ?)", (aid, item, k))
    return aid


def table_dump(conn):
    """Every table's rows, for 'this call changed nothing' assertions."""
    names = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name")]
    return {n: [tuple(r) for r in conn.execute(f"SELECT * FROM {n} ORDER BY 1, 2")] for n in names}


# ---------- building content through the admin API ----------
def ok(response, status=200):
    assert response.status_code == status, response.text
    return response.json()


def item_ids(n=3):
    with connect(main.DB_PATH) as conn:
        return usable_items(conn, n)


def mc(prompt="Which one is right?", item_id=None, correct=0, texts=("right one", "wrong one", "wrong two")):
    return {"kind": "multiple_choice", "prompt": prompt, "item_id": item_id, "answers": [{"text": t, "is_correct": i == correct} for i, t in enumerate(texts)]}


def new_lesson(api, slug="api-lesson", exercises=1, **over):
    """A complete, publishable draft lesson made entirely through the API."""
    first = item_ids(1)[0]
    body = {"slug": slug, "language": "hi", "cefr": "A1", "title": f"Lesson {slug}", "description": "A lesson.", "topics": ["food"], **over}
    lesson = ok(api.post("/api/admin/content/lessons", body), 201)
    lesson = ok(api.put(f"/api/admin/content/lessons/{lesson['id']}/vocabulary", {"revision": lesson["revision"], "item_ids": [first]}))
    for n in range(exercises):
        r = ok(api.post(f"/api/admin/content/lessons/{lesson['id']}/exercises", {"revision": lesson["revision"], **mc(f"Prompt {slug} {n}", first)}), 201)
        lesson["revision"] = r["revision"]
    return ok(api.get(f"/api/admin/content/lessons/{lesson['id']}"))


def new_situation(api, slug="api-situation", **over):
    first = item_ids(1)[0]
    body = {"slug": slug, "language": "hi", "cefr": "A1", "topic": "food", "title": f"Situation {slug}", "description": "A situation.", "difficulty": 1, **over}
    s = ok(api.post("/api/admin/content/situations", body), 201)
    r = ok(api.post(f"/api/admin/content/situations/{s['id']}/steps", {"revision": s["revision"], "kind": "learn_phrase", "item_id": first}), 201)
    r = ok(api.post(f"/api/admin/content/situations/{s['id']}/steps", {"revision": r["revision"], "kind": "choose_response", "prompt": f"Say something {slug}",
                                                                        "answers": [{"text": "good reply", "is_correct": True}, {"text": "bad reply", "is_correct": False}]}), 201)
    return ok(api.get(f"/api/admin/content/situations/{s['id']}"))


def new_activity(api, slug="api-activity", mode="choose_meaning", **over):
    items = item_ids(3)
    body = {"slug": slug, "language": "hi", "cefr": "A1", "topic": "food", "item_id": items[0], "title": f"Activity {slug}", "mode": mode, "prompt": "Listen.", "difficulty": 1, **over}
    a = ok(api.post("/api/admin/content/listening", body), 201)
    for it in items:
        r = ok(api.post(f"/api/admin/content/listening/{a['id']}/options", {"revision": a["revision"], "item_id": it}), 201)
        a["revision"] = r["revision"]
    return ok(api.get(f"/api/admin/content/listening/{a['id']}"))


# ---------- learners ----------
def learner_browser(email, dob="1990-01-01", target="hi", level="A1", profile=True):
    """A registered learner (with a profile unless profile=False), as an Api wrapper. Since Phase 14B every write needs the browser-request
    signal (the global CSRF guard), so it is sent here too."""
    from .conftest import register
    c = TestClient(main.app)
    register(c, email)
    if profile:
        r = c.put("/api/profile", json={"native_language": "en", "target_language": target, "cefr_level": level, "date_of_birth": dob}, headers=CSRF)
        assert r.status_code == 200, r.text
    return Api(c)


def learner_slugs(learner, kind):
    """The slugs a learner can list: kind is lessons | situations | listening."""
    key = {"lessons": "lessons", "situations": "situations", "listening": "activities"}[kind]
    return [x["slug"] for x in learner.get(f"/api/{kind}").json()[key]]


def learner_can_open(learner, kind, entity_id):
    return learner.get(f"/api/{kind}/{entity_id}").status_code == 200


def forbidden_keys(obj, names=("is_correct", "correct_answers", "correct_option_id", "answer_key", "accepted", "expected", "expected_answers", "answers", "explanation")):
    """Every place in a JSON document where an answer-key name appears as a key. A bare "correct" counts only when its value is a boolean (a verdict):
    a number under that name is a progress counter (how many of an activity were answered right), not the key."""
    found = []
    def walk(x, where):
        if isinstance(x, dict):
            for k, v in x.items():
                if k in names or (k == "correct" and isinstance(v, bool)):
                    found.append(f"{where}.{k}")
                walk(v, f"{where}.{k}")
        elif isinstance(x, list):
            for i, v in enumerate(x):
                walk(v, f"{where}[{i}]")
    walk(obj, "$")
    return found


# ---------- analytics fixtures: many learners, evidence at exact UTC moments ----------
_seq = itertools.count(1000)


def learners(conn, n, target="hi", level="A1", dob="1990-01-01", created="2026-03-01 00:00:00", profile=True):
    out = []
    for _ in range(n):
        uid = add_user(conn)
        conn.execute("UPDATE users SET created_at = ? WHERE id = ?", (created, uid))
        if profile:
            add_profile(conn, uid, target=target, level=level, dob=dob)
        out.append(uid)
    return out


def speaking_attempt(conn, uid, at, stage="completed"):
    sid = audio_session(conn, uid, "speaking", at)
    item = usable_items(conn, 1)[0]
    recorded = stage not in ("created", "cancelled")
    conn.execute(
        f"INSERT INTO speaking_sessions(session_id, user_id, language_id, item_id, locale, stage, audio_mime, audio_bytes, audio_sha256, recorded_at, created_at, updated_at) "
        f"VALUES (?, ?, 10, ?, 'hi-IN', ?, {'NULL' if not recorded else repr('audio/webm')}, {'NULL' if not recorded else 100}, {'NULL' if not recorded else repr('a' * 64)}, "
        f"{'NULL' if not recorded else repr(at)}, ?, ?)", (sid, uid, item, stage, at, at))
    return sid


def pronunciation(conn, uid, at, status="completed"):
    sid = speaking_attempt(conn, uid, at, stage="completed")
    run = conn.execute("INSERT INTO stt_runs(session_id, user_id, provider, locale, status, started_at, finished_at) VALUES (?, ?, 'mock', 'hi-IN', 'completed', ?, ?)", (sid, uid, at, at)).lastrowid
    tr = conn.execute("INSERT INTO speaking_transcripts(run_id, session_id, user_id, text, locale, created_at) VALUES (?, ?, ?, 'private transcript words', 'hi-IN', ?)", (run, sid, uid, at)).lastrowid
    if status == "completed":
        conn.execute("INSERT INTO pronunciation_assessments(session_id, user_id, transcript_id, provider, method, status, overall_score, words_expected, words_matched, locale, created_at) "
                     "VALUES (?, ?, ?, 'mock', 'mock', 'completed', 80, 2, 2, 'hi-IN', ?)", (sid, uid, tr, at))
    else:
        conn.execute("INSERT INTO pronunciation_assessments(session_id, user_id, transcript_id, provider, method, status, error_code, words_expected, words_matched, locale, created_at) "
                     "VALUES (?, ?, ?, 'mock', NULL, 'failed', 'provider_error', 2, 0, 'hi-IN', ?)", (sid, uid, tr, at))
    return sid


def micro_lesson(conn, uid, created, attempts=(), day=None):
    item = usable_items(conn, 3)[next(_seq) % 3]
    mid = conn.execute(
        "INSERT INTO ai_micro_lessons(user_id, language_id, item_id, kind, difficulty, mode, question, generator, status, validation_note, day, created_at, expires_at) "
        "VALUES (?, 10, ?, 'vocab_choice', 1, 'adult', 'q?', 'template', 'validated', 'ok', ?, ?, '2099-01-01 00:00:00')", (uid, item, day or created[:10], created)).lastrowid
    conn.execute("INSERT INTO ai_micro_lesson_options(micro_lesson_id, user_id, ord, text, is_correct) VALUES (?, ?, 1, 'right', 1)", (mid, uid))
    conn.execute("INSERT INTO ai_micro_lesson_options(micro_lesson_id, user_id, ord, text, is_correct) VALUES (?, ?, 2, 'wrong', 0)", (mid, uid))
    for at, correct in attempts:
        conn.execute("INSERT INTO ai_micro_lesson_attempts(user_id, micro_lesson_id, option_ord, is_correct, attempted_at) VALUES (?, ?, ?, ?, ?)", (uid, mid, 1 if correct else 2, 1 if correct else 0, at))
    return mid


def recommendation(conn, uid, created, status="active", target_id=None):
    n = next(_seq)
    conn.execute(
        "INSERT INTO ai_recommendations(user_id, language_id, plan_date, kind, target_type, target_id, title, reason, rank, source, mode, status, created_at, applied_at) "
        "VALUES (?, 10, ?, 'next_lesson', 'lesson', ?, 't', 'r', 1, 'rules', 'adult', ?, ?, ?)",
        (uid, created[:10], target_id or n, status, created, created if status == "applied" else None))


def streak_day(conn, uid, day):
    conn.execute("INSERT INTO streak_days(user_id, day) VALUES (?, ?)", (uid, day))


def achievement(conn, uid, code_index, at):
    aid = conn.execute("SELECT id FROM achievements ORDER BY sort_order LIMIT 1 OFFSET ?", (code_index,)).fetchone()[0]
    conn.execute("INSERT INTO learner_achievements(user_id, achievement_id, unlocked_at) VALUES (?, ?, ?)", (uid, aid, at))


def challenge(conn, uid, period_start, claimed=False, index=0):
    cid = conn.execute("SELECT id FROM challenges ORDER BY sort_order LIMIT 1 OFFSET ?", (index,)).fetchone()[0]
    conn.execute("INSERT INTO learner_challenges(user_id, challenge_id, period_start, period_end, claimed_at) VALUES (?, ?, ?, ?, ?)",
                 (uid, cid, period_start, period_start, f"{period_start} 12:00:00" if claimed else None))


def self_report(conn, uid, topic_slug, score, at):
    conn.execute(f"INSERT INTO confidence_scores(user_id, language_id, topic_id, score, source, recorded_at) VALUES (?, {HI}, (SELECT id FROM topics WHERE slug = ?), ?, 'self_report', ?)", (uid, topic_slug, score, at))


def lesson_attempts_for(conn, uid, lesson_slug, results, at):
    """results: list of bools, one exercise attempt each (cycling through the lesson's exercises)."""
    exercises = [r[0] for r in conn.execute(f"SELECT e.id FROM exercises e JOIN lessons l ON l.id = e.lesson_id WHERE l.slug = ? AND l.language_id = {HI} ORDER BY e.sort_order", (lesson_slug,))]   # Hindi's: slugs repeat across languages
    for i, ok_ in enumerate(results):
        exercise_attempt(conn, uid, exercises[i % len(exercises)], correct=1 if ok_ else 0, at=at)
