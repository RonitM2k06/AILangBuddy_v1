"""Age-aware selection: classification, deterministic filtering across every learner-facing selection path, adult unchanged."""
import json
import sqlite3

import pytest

from backend import main
from backend.db import connect

from .agekids import db, dob_for_age, make_learner, profile
from .conftest import register


def slugs(client, path, key):
    return [x["slug"] for x in client.get(path).json()[key]]


# ---------- classification (Phase 3 groups, no new categories) ----------
@pytest.mark.parametrize("age,mode", [(5, "child"), (9, "child"), (10, "teen"), (14, "teen"), (17, "teen"), (18, "adult"), (40, "adult")])
def test_experience_mode_follows_age_group(client, age, mode):
    make_learner(client, f"a{age}@example.com", age)
    body = client.get("/api/experience").json()
    assert body["mode"] == mode and body["age_group"]["code"] == mode
    assert "date_of_birth" not in json.dumps(body) and "dob" not in json.dumps(body).lower()


def test_experience_features(client):
    make_learner(client, "k@example.com", 7)
    f = client.get("/api/experience").json()["features"]
    assert f == {"adventure": True, "lives": True, "voice_practice": False, "path": False}


def test_experience_needs_profile_and_login(client, lockdown):
    assert client.get("/api/experience").status_code == 401
    register(client, "np@example.com")
    assert client.get("/api/experience").status_code == 409


def test_age_group_changes_when_profile_changes(client):
    make_learner(client, "grow@example.com", 8)
    assert client.get("/api/experience").json()["mode"] == "child"
    assert client.put("/api/profile", json=profile(30)).status_code == 200
    assert client.get("/api/experience").json()["mode"] == "adult"


# ---------- filtering ----------
@pytest.mark.parametrize("age,sees", [(6, False), (9, False), (10, True), (16, True), (18, True), (35, True)])
def test_college_content_is_restricted_to_teen_and_adult(client, age, sees):
    make_learner(client, "c@example.com", age)
    lessons = slugs(client, "/api/lessons", "lessons")
    sits = slugs(client, "/api/situations", "situations")
    acts = slugs(client, "/api/listening", "activities")
    assert ("college" in lessons) is sees
    assert ("college" in sits) is sees
    assert ({"college-meaning", "college-phrase"} <= set(acts)) is sees


def test_adult_content_is_unchanged(client):
    """An adult sees exactly what is published at their level: nothing is hidden by age targeting."""
    make_learner(client, "adult@example.com", 30)
    with db() as conn:
        want_lessons = {r[0] for r in conn.execute("SELECT slug FROM lessons WHERE status='published' AND language_id=(SELECT id FROM languages WHERE code='hi') AND cefr_code='A1'")}
        want_acts = {r[0] for r in conn.execute("SELECT slug FROM listening_activities WHERE status='published' AND cefr_code='A1' AND language_id = (SELECT id FROM languages WHERE code='hi')")}
    assert set(slugs(client, "/api/lessons", "lessons")) == want_lessons
    assert set(slugs(client, "/api/listening", "activities")) == want_acts


def test_child_sees_only_unrestricted_or_child_targeted_content(client):
    make_learner(client, "kid@example.com", 7)
    with db() as conn:
        restricted = {r[0] for r in conn.execute("SELECT DISTINCT l.slug FROM lessons l JOIN lesson_age_groups x ON x.lesson_id = l.id")}
    assert restricted and not (restricted & set(slugs(client, "/api/lessons", "lessons")))
    assert len(slugs(client, "/api/lessons", "lessons")) >= 1


def test_restricted_item_cannot_be_fetched_by_id_as_child(client, client2):
    make_learner(client, "kid@example.com", 7)
    make_learner(client2, "adult@example.com", 30)
    lesson = next(l["id"] for l in client2.get("/api/lessons").json()["lessons"] if l["slug"] == "college")
    sit = next(s["id"] for s in client2.get("/api/situations").json()["situations"] if s["slug"] == "college")
    act = next(a["id"] for a in client2.get("/api/listening").json()["activities"] if a["slug"] == "college-meaning")
    assert client2.get(f"/api/lessons/{lesson}").status_code == 200
    assert client.get(f"/api/lessons/{lesson}").status_code == 404
    assert client2.get(f"/api/situations/{sit}").status_code == 200
    assert client.get(f"/api/situations/{sit}").status_code == 404
    assert client2.get(f"/api/listening/{act}").status_code == 200
    assert client.get(f"/api/listening/{act}").status_code == 404
    assert client.post(f"/api/listening/{act}/attempts", json={"option_id": 1}).status_code == 404


def test_child_cannot_submit_exercise_of_restricted_lesson(client):
    make_learner(client, "kid@example.com", 7)
    with db() as conn:
        ex = conn.execute("SELECT e.id FROM exercises e JOIN lessons l ON l.id = e.lesson_id WHERE l.slug='college' AND l.language_id = (SELECT id FROM languages WHERE code='hi') LIMIT 1").fetchone()[0]
    assert client.post(f"/api/exercises/{ex}/attempts", json={"text": "x"}).status_code == 404


def test_recommendations_for_child_exclude_restricted_content(client):
    make_learner(client, "kid@example.com", 7)
    body = client.get("/api/recommendations").json()
    assert "college" not in json.dumps(body).lower().replace("collegefoo", "")
    topics = client.get("/api/confidence").json()
    assert "college" not in json.dumps(topics)


def test_confidence_rejects_restricted_topic_for_child(client, client2):
    make_learner(client, "kid@example.com", 7)
    make_learner(client2, "teen@example.com", 14)
    body = {"topic": "college", "score": 50, "source": "self_report"}
    assert client.post("/api/confidence", json=body).status_code == 422
    assert client2.post("/api/confidence", json=body).status_code == 201


def test_speaking_filter_respects_age_groups(client):
    from backend.repositories import speaking as repo
    make_learner(client, "t@example.com", 14)
    with db() as conn:
        ids = {r["code"]: r["id"] for r in conn.execute("SELECT id, code FROM age_groups")}
        hi = conn.execute("SELECT id FROM languages WHERE code='hi'").fetchone()[0]
        teen = set(repo.available_prompts(conn, hi, 1, ids["teen"]))
        child = set(repo.available_prompts(conn, hi, 1, ids["child"]))
        assert child and child <= teen
        item = sorted(teen)[0]
        assert repo.is_available_prompt(conn, item, hi, 1, ids["teen"])
        # restrict every lesson and situation to adults: nothing is left for the other groups, adults keep everything
        conn.execute("DELETE FROM lesson_age_groups")
        conn.execute("DELETE FROM situation_age_groups")
        conn.execute("INSERT INTO lesson_age_groups SELECT id, ? FROM lessons", (ids["adult"],))
        conn.execute("INSERT INTO situation_age_groups SELECT id, ? FROM situations", (ids["adult"],))
        assert repo.available_prompts(conn, hi, 1, ids["teen"]) == []
        assert repo.available_prompts(conn, hi, 1, ids["child"]) == []
        assert not repo.is_available_prompt(conn, item, hi, 1, ids["teen"])
        assert set(repo.available_prompts(conn, hi, 1, ids["adult"])) == teen | child


def test_unrestricted_means_universal_in_the_selection_functions(client):
    from backend.repositories import curriculum, listening, situations
    make_learner(client, "x@example.com", 30)
    with db() as conn:
        groups = [r["id"] for r in conn.execute("SELECT id FROM age_groups")]
        hi = conn.execute("SELECT id FROM languages WHERE code='hi'").fetchone()[0]
        for g in groups:
            assert {l["slug"] for l in curriculum.list_available_lessons(conn, hi, 1, g)} >= {"greetings"}
        # a lesson restricted to teens only is hidden from the others, shown to teens
        lid = conn.execute("SELECT id FROM lessons WHERE slug='greetings' AND language_id = (SELECT id FROM languages WHERE code = 'hi')").fetchone()[0]
        teen = conn.execute("SELECT id FROM age_groups WHERE code='teen'").fetchone()[0]
        conn.execute("INSERT INTO lesson_age_groups VALUES (?, ?)", (lid, teen))
        seen = {code: "greetings" in {l["slug"] for l in curriculum.list_available_lessons(conn, hi, 1, gid)}
                for code, gid in [(r["code"], r["id"]) for r in conn.execute("SELECT id, code FROM age_groups")]}
        assert seen == {"child": False, "teen": True, "adult": False}
        assert curriculum.get_available_lesson(conn, lid, hi, 1, teen) is not None
        assert listening.list_available(conn, hi, 1, groups[0]) is not None and situations.list_available(conn, hi, 1, groups[0]) is not None


def test_multiple_targets_are_a_union(client):
    from backend.repositories import curriculum
    make_learner(client, "x@example.com", 30)
    with db() as conn:
        hi = conn.execute("SELECT id FROM languages WHERE code='hi'").fetchone()[0]
        ids = {r["code"]: r["id"] for r in conn.execute("SELECT id, code FROM age_groups")}
        lid = conn.execute("SELECT id FROM lessons WHERE slug='greetings' AND language_id = (SELECT id FROM languages WHERE code = 'hi')").fetchone()[0]
        conn.executemany("INSERT INTO lesson_age_groups VALUES (?, ?)", [(lid, ids["child"]), (lid, ids["adult"])])
        got = {c: "greetings" in {l["slug"] for l in curriculum.list_available_lessons(conn, hi, 1, i)} for c, i in ids.items()}
    assert got == {"child": True, "teen": False, "adult": True}


# ---------- schema ----------
def test_age_target_constraints(db_path):
    with connect(db_path) as conn:
        lid = conn.execute("SELECT id FROM lessons LIMIT 1").fetchone()[0]
        g = conn.execute("SELECT id FROM age_groups WHERE code='child'").fetchone()[0]
        conn.execute("INSERT INTO lesson_age_groups VALUES (?, ?)", (lid, g))
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO lesson_age_groups VALUES (?, ?)", (lid, g))          # no duplicate target
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO lesson_age_groups VALUES (?, 999)", (lid,))          # real age group
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO lesson_age_groups VALUES (99999, ?)", (g,))          # real lesson
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("DELETE FROM age_groups WHERE id = ?", (g,))                      # RESTRICT


def test_target_rows_go_with_their_content(db_path):
    with connect(db_path) as conn:
        a = conn.execute("SELECT activity_id FROM listening_activity_age_groups LIMIT 1").fetchone()[0]
        conn.execute("DELETE FROM listening_attempts WHERE activity_id = ?", (a,))
        conn.execute("DELETE FROM listening_activities WHERE id = ?", (a,))
        assert conn.execute("SELECT COUNT(*) FROM listening_activity_age_groups WHERE activity_id = ?", (a,)).fetchone()[0] == 0


def test_no_age_group_is_invented(db_path):
    with connect(db_path) as conn:
        assert [r[0] for r in conn.execute("SELECT code FROM age_groups ORDER BY min_age")] == ["child", "teen", "adult"]


def test_recommendation_lookup_by_item_respects_age(client):
    from backend.repositories import personalization as repo
    make_learner(client, "x@example.com", 30)
    with db() as conn:
        ids = {r["code"]: r["id"] for r in conn.execute("SELECT id, code FROM age_groups")}
        hi = conn.execute("SELECT id FROM languages WHERE code='hi'").fetchone()[0]
        lid, item = conn.execute("SELECT l.id, lv.item_id FROM lessons l JOIN lesson_vocabulary lv ON lv.lesson_id = l.id WHERE l.slug='greetings' AND l.language_id = (SELECT id FROM languages WHERE code='hi') LIMIT 1").fetchone()
        everyone = {g: lid in repo.lessons_containing_item(conn, item, hi, 1, i) for g, i in ids.items()}
        assert everyone == {"child": True, "teen": True, "adult": True}
        conn.execute("INSERT INTO lesson_age_groups VALUES (?, ?)", (lid, ids["teen"]))
        restricted = {g: lid in repo.lessons_containing_item(conn, item, hi, 1, i) for g, i in ids.items()}
    assert restricted == {"child": False, "teen": True, "adult": False}
