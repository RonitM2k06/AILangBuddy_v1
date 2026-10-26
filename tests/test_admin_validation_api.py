"""Phase 13C: validation through the database and the API. The seeded curriculum passes; each rule fires for real content; the dry run, the sweep and
(later) the publish gate return the same findings; and validating writes nothing."""
import pytest

from backend import main
from backend.admin import validation
from backend.db import connect

from . import adm
from .adm import Api, admin, audit_rows, demo_browser, make_activity, make_lesson, make_situation, one, register_browser, table_dump  # noqa: F401

TYPES = {"lesson": "lessons", "situation": "situations", "listening_activity": "listening_activities"}


def ids(table):
    with connect(main.DB_PATH) as conn:
        return [r[0] for r in conn.execute(f"SELECT id FROM {table} ORDER BY id")]


def codes_of(response):
    assert response.status_code == 200, response.text
    return sorted(f["code"] for f in response.json()["findings"])


# ---------- the seeded curriculum ----------
@pytest.mark.parametrize("etype", TYPES)
def test_every_seeded_entity_validates_clean(admin, etype):
    entity_ids = ids(TYPES[etype])
    assert entity_ids
    for i in entity_ids:
        r = admin.post(f"/api/admin/validate/{etype}/{i}")
        assert r.status_code == 200 and r.json() == {"ok": True, "findings": []}, (etype, i, r.json())


def test_the_seeded_curriculum_passes_the_whole_sweep(admin):
    body = admin.get("/api/admin/validate/all").json()
    assert body["ok"] is True and body["errors"] == 0 and body["published_errors"] == 0
    assert body["checked"] == {"lesson": 157, "situation": 111, "listening_activity": 315}            # Hindi 7/8/15, Marathi 27/14/54, Kannada 25/14/50, Tamil 28/21/56, French 9/8/18, Bengali 25/14/50, Telugu 9/8/18, Urdu 9/8/18, Kashmiri 9/8/18, Dogri 9/8/18
    assert not [f for f in body["findings"] if f["severity"] == "error"]
    assert not [f for f in body["findings"] if f["entity_status"] is not None]               # nothing is wrong with any lesson, situation or activity
    assert {f["code"] for f in body["findings"]} <= {"integrity_orphan_vocabulary"}            # the only observation: some bank vocabulary is not used by any content yet


# ---------- real broken content, one rule at a time ----------
def break_lesson(case, conn, lid):
    if case == "no_exercises":
        conn.execute("DELETE FROM exercises WHERE lesson_id = ?", (lid,))
        return ["lesson_no_exercises"]
    if case == "no_topics":
        conn.execute("DELETE FROM lesson_topics WHERE lesson_id = ?", (lid,))
        return ["lesson_no_topics"]
    if case == "no_vocabulary":
        conn.execute("DELETE FROM lesson_vocabulary WHERE lesson_id = ?", (lid,))
        return ["exercise_item_not_in_lesson", "lesson_no_vocabulary"]
    if case == "two_correct":
        conn.execute("UPDATE exercise_answers SET is_correct = 1 WHERE exercise_id = (SELECT id FROM exercises WHERE lesson_id = ?)", (lid,))
        return ["exercise_mc_correct_count"]
    if case == "no_correct":
        conn.execute("UPDATE exercise_answers SET is_correct = 0 WHERE exercise_id = (SELECT id FROM exercises WHERE lesson_id = ?)", (lid,))
        return ["exercise_mc_correct_count"]
    if case == "one_answer":
        conn.execute("DELETE FROM exercise_answers WHERE exercise_id = (SELECT id FROM exercises WHERE lesson_id = ?) AND is_correct = 0", (lid,))
        return ["exercise_mc_too_few_answers"]
    if case == "dup_answers":
        conn.execute("UPDATE exercise_answers SET answer_text = 'Same.' WHERE exercise_id = (SELECT id FROM exercises WHERE lesson_id = ?) AND sort_order = 2", (lid,))
        conn.execute("UPDATE exercise_answers SET answer_text = 'same' WHERE exercise_id = (SELECT id FROM exercises WHERE lesson_id = ?) AND sort_order = 3", (lid,))
        return ["exercise_duplicate_answers"]
    if case == "typed_incorrect_row":
        eid = adm.one(conn, "SELECT id FROM exercises WHERE lesson_id = ?", lid)
        conn.execute("UPDATE exercises SET kind = 'translation' WHERE id = ?", (eid,))
        return ["exercise_typed_incorrect_row"]
    if case == "typed_no_accepted":
        eid = adm.one(conn, "SELECT id FROM exercises WHERE lesson_id = ?", lid)
        conn.execute("UPDATE exercises SET kind = 'fill_blank' WHERE id = ?", (eid,))
        conn.execute("DELETE FROM exercise_answers WHERE exercise_id = ?", (eid,))
        return ["exercise_typed_no_accepted_answer"]
    if case == "dup_prompt":
        eid = conn.execute("INSERT INTO exercises(lesson_id, language_id, kind, prompt, item_id, sort_order, difficulty) "
                           "SELECT lesson_id, language_id, kind, UPPER(prompt), item_id, 2, difficulty FROM exercises WHERE lesson_id = ?", (lid,)).lastrowid
        for k, (t, ok) in enumerate([("r", 1), ("w1", 0)], 1):
            conn.execute("INSERT INTO exercise_answers(exercise_id, answer_text, is_correct, sort_order) VALUES (?, ?, ?, ?)", (eid, t, ok, k))
        return ["exercise_duplicate_prompt"]
    if case == "no_item":
        conn.execute("UPDATE exercises SET item_id = NULL WHERE lesson_id = ?", (lid,))
        return ["exercise_item_missing"]
    if case == "no_english":
        item = adm.one(conn, "SELECT item_id FROM lesson_vocabulary WHERE lesson_id = ?", lid)
        conn.execute("DELETE FROM vocabulary_translations WHERE item_id = ? AND language_id = 1", (item,))
        return ["vocabulary_missing_english"]
    if case == "cefr_above":
        conn.execute("INSERT INTO language_levels(language_id, cefr_code) VALUES (10, 'A2') ON CONFLICT DO NOTHING")
        item = adm.one(conn, "SELECT item_id FROM lesson_vocabulary WHERE lesson_id = ?", lid)
        conn.execute("UPDATE vocabulary_items SET cefr_code = 'A2' WHERE id = ?", (item,))
        return ["vocabulary_cefr_above_unit"]
    if case == "dup_title":
        conn.execute("UPDATE lessons SET title = 'Dup Title' WHERE id = ?", (lid,))
        conn.execute("UPDATE lessons SET title = 'dup title ' WHERE slug = 'food' AND language_id = (SELECT id FROM languages WHERE code='hi')")
        return ["lesson_duplicate_title"]
    if case == "control_char":
        conn.execute("UPDATE lessons SET title = ? WHERE id = ?", ("bad\x07title", lid))
        return ["text_control_characters"]
    if case == "bad_slug":
        conn.execute("UPDATE lessons SET slug = 'Bad_Slug' WHERE id = ?", (lid,))
        return ["slug_invalid"]
    raise AssertionError(case)


LESSON_CASES = ["no_exercises", "no_topics", "no_vocabulary", "two_correct", "no_correct", "one_answer", "dup_answers", "typed_incorrect_row", "typed_no_accepted", "dup_prompt",
                "no_item", "no_english", "cefr_above", "dup_title", "control_char", "bad_slug"]


@pytest.mark.parametrize("case", LESSON_CASES)
def test_a_broken_lesson_reports_exactly_its_rule(admin, case):
    with connect(main.DB_PATH) as conn:
        lid = make_lesson(conn)
    assert codes_of(admin.post(f"/api/admin/validate/lesson/{lid}")) == []                 # the builder's lesson is valid before it is broken
    with connect(main.DB_PATH) as conn:
        expected = break_lesson(case, conn, lid)
    assert codes_of(admin.post(f"/api/admin/validate/lesson/{lid}")) == sorted(expected)


def test_a_new_empty_draft_lesson_is_reported_as_incomplete(admin):
    with connect(main.DB_PATH) as conn:
        lid = conn.execute("INSERT INTO lessons(language_id, cefr_code, slug, title, description, sort_order) VALUES (10, 'A1', 'empty-one', 'Empty', 'd', 90)").lastrowid
    r = admin.post(f"/api/admin/validate/lesson/{lid}").json()
    assert r["ok"] is False and sorted(f["code"] for f in r["findings"]) == ["lesson_no_exercises", "lesson_no_topics", "lesson_no_vocabulary"]
    assert {f["severity"] for f in r["findings"]} == {"error"}


def test_situation_rules_on_real_rows(admin):
    with connect(main.DB_PATH) as conn:
        a, b, c, d = make_situation(conn, "s-a"), make_situation(conn, "s-b"), make_situation(conn, "s-c"), make_situation(conn, "s-d")
        conn.execute("DELETE FROM situation_steps WHERE situation_id = ?", (a,))
        conn.execute("UPDATE situation_step_answers SET is_correct = 0 WHERE step_id IN (SELECT id FROM situation_steps WHERE situation_id = ?)", (b,))
        conn.execute("DELETE FROM situation_step_answers WHERE step_id IN (SELECT id FROM situation_steps WHERE situation_id = ?) AND is_correct = 0", (c,))
        step = adm.one(conn, "SELECT id FROM situation_steps WHERE situation_id = ? AND kind = 'choose_response'", d)
        conn.execute("UPDATE situation_steps SET kind = 'translate' WHERE id = ?", (step,))
    assert codes_of(admin.post(f"/api/admin/validate/situation/{a}")) == ["situation_no_steps"]
    assert codes_of(admin.post(f"/api/admin/validate/situation/{b}")) == ["step_choose_correct_count"]
    assert codes_of(admin.post(f"/api/admin/validate/situation/{c}")) == ["step_choose_too_few_answers"]
    assert codes_of(admin.post(f"/api/admin/validate/situation/{d}")) == ["step_typed_incorrect_row"]


def test_listening_rules_on_real_rows(admin):
    with connect(main.DB_PATH) as conn:
        a, b, c = make_activity(conn, "l-a"), make_activity(conn, "l-b"), make_activity(conn, "l-c", mode="choose_phrase")
        conn.execute("DELETE FROM listening_options WHERE id = (SELECT MAX(id) FROM listening_options WHERE activity_id = ?)", (a,))
        extra = adm.one(conn, "SELECT id FROM vocabulary_items WHERE language_id = 10 AND id NOT IN (SELECT item_id FROM listening_options WHERE activity_id = ?) ORDER BY id LIMIT 1", b)
        conn.execute("UPDATE listening_options SET item_id = ? WHERE activity_id = ? AND item_id = (SELECT item_id FROM listening_activities WHERE id = ?)", (extra, b, b))
        conn.execute("UPDATE vocabulary_translations SET meaning = (SELECT meaning FROM vocabulary_translations WHERE item_id = (SELECT item_id FROM listening_options WHERE activity_id = ? AND sort_order = 2) AND language_id = 1) "
                     "WHERE language_id = 1 AND item_id = (SELECT item_id FROM listening_options WHERE activity_id = ? AND sort_order = 3)", (c, c))
    assert codes_of(admin.post(f"/api/admin/validate/listening_activity/{a}")) == ["listening_option_count"]
    assert "listening_target_not_in_options" in codes_of(admin.post(f"/api/admin/validate/listening_activity/{b}"))
    assert codes_of(admin.post(f"/api/admin/validate/listening_activity/{c}")) == []               # the same meaning is fine when the learner reads phrases
    with connect(main.DB_PATH) as conn:
        conn.execute("UPDATE listening_activities SET mode = 'choose_meaning' WHERE id = ?", (c,))
    assert codes_of(admin.post(f"/api/admin/validate/listening_activity/{c}")) == ["listening_duplicate_option_text"]


# ---------- the same rules everywhere ----------
def test_dry_run_and_sweep_never_disagree(admin):
    with connect(main.DB_PATH) as conn:
        a, b = make_lesson(conn, "x-1"), make_lesson(conn, "x-2")
        conn.execute("DELETE FROM exercises WHERE lesson_id = ?", (a,))
        s = make_situation(conn, "x-s")
        conn.execute("DELETE FROM situation_step_answers WHERE step_id IN (SELECT id FROM situation_steps WHERE situation_id = ?)", (s,))
        t = make_activity(conn, "x-l")
        conn.execute("DELETE FROM listening_options WHERE activity_id = ?", (t,))
        conn.execute("UPDATE lessons SET title = 'Same' WHERE id IN (?, ?)", (a, b))
    sweep = admin.get("/api/admin/validate/all").json()
    assert sweep["errors"] >= 3
    flat_dry = []
    for etype, table in TYPES.items():
        for i in ids(table):
            flat_dry += admin.post(f"/api/admin/validate/{etype}/{i}").json()["findings"]
    flat_sweep = [{k: f[k] for k in ("code", "severity", "entity", "message")} for f in sweep["findings"] if f["entity_status"] is not None]
    assert flat_sweep == flat_dry


def test_sweep_ok_depends_on_published_content_and_global_checks_only(admin):
    with connect(main.DB_PATH) as conn:
        draft = make_lesson(conn, "only-draft")
        conn.execute("DELETE FROM exercises WHERE lesson_id = ?", (draft,))
    body = admin.get("/api/admin/validate/all").json()
    assert body["ok"] is True and body["errors"] == 1 and body["published_errors"] == 0
    assert [f["entity_status"] for f in body["findings"] if f["severity"] == "error"] == ["draft"]
    with connect(main.DB_PATH) as conn:
        conn.execute("UPDATE lessons SET status = 'published', published_at = '2026-01-01 00:00:00' WHERE id = ?", (draft,))
    body = admin.get("/api/admin/validate/all").json()
    assert body["ok"] is False and body["published_errors"] == 1
    assert [f["entity_status"] for f in body["findings"] if f["severity"] == "error"] == ["published"]


def test_archived_content_is_still_validated_and_reported_with_its_status(admin):
    with connect(main.DB_PATH) as conn:
        lid = make_lesson(conn, "old-one", status="archived")
        conn.execute("DELETE FROM exercises WHERE lesson_id = ?", (lid,))
    body = admin.get("/api/admin/validate/all").json()
    assert body["ok"] is True
    assert [(f["code"], f["entity_status"]) for f in body["findings"] if f["severity"] == "error"] == [("lesson_no_exercises", "archived")]


# ---------- the dry run writes nothing ----------
def test_validating_changes_no_row_and_writes_no_audit_event(admin, audit_rows):
    with connect(main.DB_PATH) as conn:
        lid = make_lesson(conn, "dry")
        conn.execute("DELETE FROM exercises WHERE lesson_id = ?", (lid,))
        before = table_dump(conn)
    for _ in range(2):
        assert admin.post(f"/api/admin/validate/lesson/{lid}").json()["ok"] is False
        assert admin.get("/api/admin/validate/all").status_code == 200
    with connect(main.DB_PATH) as conn:
        assert table_dump(conn) == before
    assert audit_rows() == []


@pytest.mark.parametrize("path,status", [("/api/admin/validate/lesson/99999", 404), ("/api/admin/validate/situation/99999", 404), ("/api/admin/validate/listening_activity/99999", 404),
                                         ("/api/admin/validate/vocabulary/1", 422), ("/api/admin/validate/lessons/1", 422), ("/api/admin/validate/lesson/abc", 422),
                                         ("/api/admin/validate/lesson/0", 404)])
def test_validate_errors(admin, path, status):
    assert admin.post(path).status_code == status


# ---------- the sweep's whole-database checks ----------
def test_a_dangling_reference_is_reported_by_the_sweep(admin):
    with connect(main.DB_PATH) as conn:
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute("INSERT INTO lesson_topics(lesson_id, topic_id) VALUES (99999, 1)")
        conn.commit()
    body = admin.get("/api/admin/validate/all").json()
    hits = [f for f in body["findings"] if f["code"] == "integrity_foreign_key"]
    assert body["ok"] is False and [(f["entity"], f["severity"], f["entity_status"]) for f in hits] == [("table:lesson_topics", "error", None)]


def test_unused_vocabulary_and_topics_are_reported_as_warnings(admin):
    with connect(main.DB_PATH) as conn:
        item = conn.execute("INSERT INTO vocabulary_items(language_id, cefr_code, kind, text) VALUES (10, 'A1', 'word', 'lonely-word')").lastrowid
        topic = conn.execute("INSERT INTO topics(slug, name, icon) VALUES ('lonely', 'Lonely', 'x')").lastrowid
    body = admin.get("/api/admin/validate/all").json()
    found = {(f["code"], f["entity"], f["severity"]) for f in body["findings"]}
    assert ("integrity_orphan_vocabulary", f"vocabulary:{item}", "warning") in found and ("integrity_orphan_topic", f"topic:{topic}", "warning") in found
    assert body["ok"] is True
    with connect(main.DB_PATH) as conn:
        conn.execute("INSERT INTO lesson_vocabulary(lesson_id, item_id, language_id, sort_order) VALUES ((SELECT id FROM lessons WHERE slug = 'food' AND language_id = (SELECT id FROM languages WHERE code='hi')), ?, 10, 99)", (item,))
        conn.execute("UPDATE situations SET topic_id = ? WHERE slug = 'food' AND language_id = (SELECT id FROM languages WHERE code='hi')", (topic,))
    found = {(f["code"], f["entity"]) for f in admin.get("/api/admin/validate/all").json()["findings"]}
    assert ("integrity_orphan_vocabulary", f"vocabulary:{item}") not in found and ("integrity_orphan_topic", f"topic:{topic}") not in found


def test_a_failed_database_integrity_check_is_an_error(admin, monkeypatch):
    calls = []
    monkeypatch.setattr(validation.repo, "integrity_check", lambda conn: calls.append(1) or ["row 5 missing from index idx_x"])
    body = admin.get("/api/admin/validate/all").json()
    assert calls and body["ok"] is False
    assert [(f["code"], f["entity"], f["entity_status"]) for f in body["findings"] if f["severity"] == "error"] == [("integrity_database", "database", None)]
    assert "idx_x" not in str(body)                                                                      # SQLite's own message is never passed through


def test_the_real_integrity_check_passes_on_a_healthy_database(admin):
    with connect(main.DB_PATH) as conn:
        from backend.repositories import admin_content
        assert admin_content.integrity_check(conn) == ["ok"] and admin_content.foreign_key_violations(conn) == []


# ---------- access ----------
def test_validation_endpoints_refuse_everyone_but_admins(client, admin):
    for who in (Api(), register_browser("learner", "l@example.com"), register_browser("parent", "p@example.com"), demo_browser()):
        assert who.post("/api/admin/validate/lesson/1").status_code in (401, 403)
        assert who.get("/api/admin/validate/all").status_code in (401, 403)
    assert admin.post("/api/admin/validate/lesson/1").status_code == 200


ORPHAN_REFERENCES = {
    "lesson_vocabulary": "INSERT INTO lesson_vocabulary(lesson_id, item_id, language_id, sort_order) VALUES ((SELECT id FROM lessons WHERE slug = 'food' AND language_id = (SELECT id FROM languages WHERE code='hi')), {item}, 10, 98)",
    "exercise": "INSERT INTO exercises(lesson_id, language_id, kind, prompt, item_id, sort_order, difficulty) VALUES ((SELECT id FROM lessons WHERE slug = 'food' AND language_id = (SELECT id FROM languages WHERE code='hi')), 10, 'translation', 'orphan probe', {item}, 98, 1)",
    "situation_step": "INSERT INTO situation_steps(situation_id, language_id, sort_order, kind, item_id) VALUES ((SELECT id FROM situations WHERE slug = 'food' AND language_id = (SELECT id FROM languages WHERE code='hi')), 10, 98, 'learn_phrase', {item})",
    "listening_activity": "INSERT INTO listening_activities(language_id, cefr_code, topic_id, item_id, slug, title, mode, prompt, difficulty, sort_order) "
                          "VALUES (10, 'A1', 1, {item}, 'orphan-probe', 'Orphan probe', 'choose_phrase', 'p', 1, 98)",
    "listening_option": "INSERT INTO listening_options(activity_id, language_id, item_id, sort_order) VALUES ((SELECT id FROM listening_activities WHERE slug = 'food-meaning' AND language_id = (SELECT id FROM languages WHERE code='hi')), 10, {item}, 98)",
    "grammar_example": "INSERT INTO grammar_examples(grammar_topic_id, item_id, language_id, sort_order) VALUES ((SELECT id FROM grammar_topics ORDER BY id LIMIT 1), {item}, 10, 98)",
    "vocabulary_example_as_item": "INSERT INTO vocabulary_examples(item_id, example_item_id, language_id) VALUES ({item}, (SELECT id FROM vocabulary_items WHERE language_id = 10 ORDER BY id LIMIT 1), 10)",
    "vocabulary_example_as_example": "INSERT INTO vocabulary_examples(item_id, example_item_id, language_id) VALUES ((SELECT id FROM vocabulary_items WHERE language_id = 10 ORDER BY id LIMIT 1), {item}, 10)",
    "ai_micro_lesson": "INSERT INTO ai_micro_lessons(user_id, language_id, item_id, kind, difficulty, mode, question, generator, status, validation_note, day, created_at, expires_at) "
                       "VALUES ({user}, 10, {item}, 'vocab_choice', 1, 'adult', 'q', 'template', 'validated', 'n', '2026-01-01', '2026-01-01 00:00:00', '2026-01-08 00:00:00')",
    "speaking_session": "INSERT INTO speaking_sessions(session_id, user_id, language_id, item_id, locale, created_at, updated_at) VALUES ({session}, {user}, 10, {item}, 'hi-IN', 't', 't')",
}


@pytest.mark.parametrize("kind", sorted(ORPHAN_REFERENCES))
def test_an_orphan_vocabulary_item_stops_being_one_the_moment_anything_refers_to_it(admin, kind):
    with connect(main.DB_PATH) as conn:
        item = conn.execute("INSERT INTO vocabulary_items(language_id, cefr_code, kind, text) VALUES (10, 'A1', 'word', 'probe-word')").lastrowid
        conn.execute("INSERT INTO vocabulary_translations(item_id, language_id, meaning) VALUES (?, 1, 'probe')", (item,))
        user = adm.add_user(conn)
        session = adm.audio_session(conn, user, "speaking") if kind == "speaking_session" else None
    assert ("integrity_orphan_vocabulary", f"vocabulary:{item}") in {(f["code"], f["entity"]) for f in admin.get("/api/admin/validate/all").json()["findings"]}
    with connect(main.DB_PATH) as conn:
        conn.execute(ORPHAN_REFERENCES[kind].format(item=item, user=user, session=session))
    assert ("integrity_orphan_vocabulary", f"vocabulary:{item}") not in {(f["code"], f["entity"]) for f in admin.get("/api/admin/validate/all").json()["findings"]}


def test_the_foreign_key_finding_counts_every_dangling_row(admin):
    with connect(main.DB_PATH) as conn:
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute("INSERT INTO lesson_topics(lesson_id, topic_id) VALUES (99998, 1)")
        conn.execute("INSERT INTO lesson_topics(lesson_id, topic_id) VALUES (99999, 1)")
        conn.execute("INSERT INTO lesson_topics(lesson_id, topic_id) VALUES (99999, 2)")
        conn.commit()
    hits = [f for f in admin.get("/api/admin/validate/all").json()["findings"] if f["code"] == "integrity_foreign_key"]
    assert [f["message"] for f in hits] == ["3 row(s) point at something that does not exist."]
