"""Phase 13G: the learner overview (aggregate, opaque references, small cells, no impersonation) and the health / integrity endpoints."""
import hashlib
import hmac
import re
from datetime import datetime, timezone

import pytest

from backend import main, settings
from backend.admin import analytics, learners as learners_service
from backend.db import connect
from backend.repositories import admin_content

from . import adm
from .adm import Api, admin, audit_rows, demo_browser, learners, ok, register_browser  # noqa: F401

LL = "/api/admin/learners"
SECRET = "test-reference-key"


@pytest.fixture(autouse=True)
def fixed(monkeypatch):
    monkeypatch.setenv("ADMIN_REF_SECRET", SECRET)
    monkeypatch.setattr(analytics, "utcnow", lambda: datetime(2026, 3, 15, 12, 0, 0, tzinfo=timezone.utc))


def expected_ref(user_id, secret=SECRET):
    return hmac.new(secret.encode(), f"learner:{user_id}".encode(), hashlib.sha256).hexdigest()[:32]


def get(api, url, status=200):
    r = api.get(url)
    assert r.status_code == status, r.text
    return r.json()


def world(conn):
    """Six adults learning Hindi at A1, two teens learning Hindi at A1, one lone adult at A2; plus staff and the demo account."""
    a = learners(conn, 6, created="2026-03-01 08:30:00")
    t = learners(conn, 2, dob="2012-01-01", created="2026-03-02 08:30:00")
    lone = learners(conn, 1, level="A2", created="2026-03-03 08:30:00")
    adm.add_user(conn, "admin")
    adm.add_user(conn, "parent")
    return a, t, lone


# ---------- references ----------
def test_a_reference_is_an_hmac_of_the_id_under_the_servers_key(admin):
    with connect(main.DB_PATH) as conn:
        a, t, lone = world(conn)
    page = get(admin, LL)
    refs = {i["ref"] for i in page["items"]}
    assert refs == {expected_ref(u) for u in a + t + lone} and all(re.fullmatch(r"[0-9a-f]{32}", r) for r in refs)
    assert len(refs) == 9


def test_references_change_with_the_key_and_cannot_be_read_back_as_ids(admin, monkeypatch):
    with connect(main.DB_PATH) as conn:
        a, t, lone = world(conn)
    first = {i["ref"] for i in get(admin, LL)["items"]}
    monkeypatch.setenv("ADMIN_REF_SECRET", "another-key")
    second = {i["ref"] for i in get(admin, LL)["items"]}
    assert first.isdisjoint(second) and second == {expected_ref(u, "another-key") for u in a + t + lone}
    assert not any(r in (str(u), f"{u:032x}") for u in a + t + lone for r in first)


def test_without_a_configured_key_the_process_key_is_stable_and_random(admin, monkeypatch):
    monkeypatch.delenv("ADMIN_REF_SECRET")
    with connect(main.DB_PATH) as conn:
        a, _, _ = world(conn)
    one = {i["ref"] for i in get(admin, LL)["items"]}
    two = {i["ref"] for i in get(admin, LL)["items"]}
    assert one == two and len(settings.admin_ref_secret()) == 32 and settings.admin_ref_secret() == settings.admin_ref_secret()
    assert one.isdisjoint({expected_ref(u) for u in a})


# ---------- the list ----------
def test_the_list_shows_aggregate_rows_only(admin):
    with connect(main.DB_PATH) as conn:
        a, t, lone = world(conn)
        adm.lesson_progress(conn, a[0], adm.lesson_id(conn), started="2026-03-05 10:00:00", completed="2026-03-06 10:00:00")
        adm.situation_progress(conn, a[0], adm.situation_id(conn), started="2026-03-05 10:00:00", completed="2026-03-06 10:00:00")
        for _ in range(3):
            adm.exercise_attempt(conn, a[0], adm.first_exercise(conn, adm.lesson_id(conn)), at="2026-03-10 14:45:12")
    page = get(admin, LL)
    assert (page["suppressed"], page["total"], page["limit"], page["offset"]) == (False, 9, 25, 0)
    row = next(i for i in page["items"] if i["ref"] == expected_ref(a[0]))
    assert row == {"ref": expected_ref(a[0]), "language": "hi", "cefr": "A1", "age_group": "adult", "joined": "2026-03-01", "last_active": "2026-03-10", "lessons_completed": 1,
                   "situations_completed": 1, "exercise_attempts": 3}
    assert set(page["items"][0]) == {"ref", "language", "cefr", "age_group", "joined", "last_active", "lessons_completed", "situations_completed", "exercise_attempts"}
    never_active = next(i for i in page["items"] if i["ref"] == expected_ref(a[1]))
    assert never_active["last_active"] is None and never_active["exercise_attempts"] == 0
    assert [i["ref"] for i in page["items"]][0] == expected_ref(lone[0])                 # newest first


def test_the_list_never_contains_staff_the_demo_account_or_identifying_data(admin):
    with connect(main.DB_PATH) as conn:
        a, t, lone = world(conn)
        emails = [r[0] for r in conn.execute("SELECT email FROM users WHERE email IS NOT NULL")]
        names = [r[0] for r in conn.execute("SELECT display_name FROM users")]
        handles = [r[0] for r in conn.execute("SELECT handle FROM users")]
        raw = [str(u) for u in a + t + lone]
    text = admin.get(LL).text
    assert not any(x in text for x in emails + names + handles) and "@" not in text
    assert '"id"' not in text and "user_id" not in text and "password" not in text and "token" not in text and "date_of_birth" not in text
    assert len(get(admin, LL)["items"]) == 9


def test_a_filtered_group_smaller_than_five_is_withheld_even_though_the_platform_is_bigger(admin):
    with connect(main.DB_PATH) as conn:
        world(conn)
    assert get(admin, LL + "?age_group=teen") == {"suppressed": True, "total": None, "items": [], "limit": 25, "offset": 0}
    assert get(admin, LL + "?cefr=A2")["suppressed"] is True
    ok_page = get(admin, LL + "?age_group=adult")
    assert ok_page["suppressed"] is False and ok_page["total"] == 7                       # six adults at A1 and the lone adult at A2


def test_the_whole_list_is_withheld_below_five_learners(admin):
    with connect(main.DB_PATH) as conn:
        learners(conn, 4)
    assert get(admin, LL)["suppressed"] is True
    with connect(main.DB_PATH) as conn:
        learners(conn, 1)
    assert get(admin, LL)["suppressed"] is False


def test_filters_pagination_and_active_since(admin):
    with connect(main.DB_PATH) as conn:
        a, t, lone = world(conn)
        for u in a[:2]:
            adm.exercise_attempt(conn, u, adm.first_exercise(conn, adm.lesson_id(conn)), at="2026-03-12 09:00:00")
        for u in a[2:5]:
            adm.exercise_attempt(conn, u, adm.first_exercise(conn, adm.lesson_id(conn)), at="2026-03-01 09:00:00")
        adm.xp(conn, a[5], 800, earned="2026-03-14 23:59:59")
    assert get(admin, LL + "?language=hi")["total"] == 9 and get(admin, LL + "?language=es")["suppressed"] is True
    assert get(admin, LL + "?cefr=A1")["total"] == 8 and get(admin, LL + "?age_group=adult&cefr=A1")["total"] == 6
    assert get(admin, LL + "?active_since=2026-03-01")["suppressed"] is False and get(admin, LL + "?active_since=2026-03-01")["total"] == 6
    assert get(admin, LL + "?active_since=2026-03-02")["suppressed"] is True                  # only 3 were active since then
    assert get(admin, LL + "?active_since=2026-03-12")["suppressed"] is True
    p1, p2 = get(admin, LL + "?limit=4&offset=0"), get(admin, LL + "?limit=4&offset=4")
    assert len(p1["items"]) == 4 and len(p2["items"]) == 4 and not {i["ref"] for i in p1["items"]} & {i["ref"] for i in p2["items"]} and p1["total"] == 9 and p2["offset"] == 4
    assert len(get(admin, LL + "?limit=4&offset=8")["items"]) == 1 and get(admin, LL + "?offset=50")["items"] == []


@pytest.mark.parametrize("query", ["limit=0", "limit=101", "offset=-1", "age_group=senior", "active_since=yesterday", "active_since=2026-13-40", "cefr=" + "x" * 5, "language=" + "x" * 17])
def test_list_rejects_bad_parameters(admin, query):
    assert admin.get(f"{LL}?{query}").status_code == 422


def test_a_learner_in_a_cell_of_fewer_than_five_has_their_attributes_hidden(admin):
    with connect(main.DB_PATH) as conn:
        a, t, lone = world(conn)
    page = get(admin, LL)
    by_ref = {i["ref"]: i for i in page["items"]}
    for u in t + lone:                                                                    # two teens and one A2 adult: cells of 2 and 1
        r = by_ref[expected_ref(u)]
        assert (r["language"], r["cefr"], r["age_group"]) == (None, None, None) and r["joined"]
    for u in a:
        assert (by_ref[expected_ref(u)]["language"], by_ref[expected_ref(u)]["cefr"], by_ref[expected_ref(u)]["age_group"]) == ("hi", "A1", "adult")


def test_a_learner_without_a_profile_has_no_attributes(admin):
    with connect(main.DB_PATH) as conn:
        learners(conn, 5, profile=False)
    page = get(admin, LL)
    assert page["total"] == 5 and all((i["language"], i["cefr"], i["age_group"]) == (None, None, None) for i in page["items"])


# ---------- the detail ----------
def test_the_detail_is_numbers_only(admin):
    with connect(main.DB_PATH) as conn:
        a, t, lone = world(conn)
        u = a[0]
        lid, sid, aid = adm.lesson_id(conn), adm.situation_id(conn), adm.activity_id(conn)
        adm.lesson_progress(conn, u, lid, started="2026-03-05 10:00:00", completed="2026-03-06 10:00:00")
        adm.situation_progress(conn, u, sid, started="2026-03-05 10:00:00")
        for k in range(4):
            adm.exercise_attempt(conn, u, adm.first_exercise(conn, lid), correct=1 if k < 3 else 0, at=f"2026-03-1{k} 09:00:00")
        adm.listening_attempt(conn, u, aid, adm.right_option(conn, aid), correct=1, at="2026-03-12 10:00:00")
        adm.listening_attempt(conn, u, aid, adm.wrong_option(conn, aid), correct=0, at="2026-03-12 10:05:00")
        adm.speaking_attempt(conn, u, "2026-03-13 10:00:00")
        adm.speaking_attempt(conn, u, "2026-03-13 11:00:00", stage="cancelled")
        adm.roleplay_session(conn, u, sid, status="completed", missed=0, at="2026-03-14 10:00:00")
        adm.xp(conn, u, 901, amount=7, earned="2026-03-10 09:00:00")
        adm.xp(conn, u, 902, kind="lesson", amount=20, earned="2026-03-11 09:00:00")
        adm.achievement(conn, u, 0, "2026-03-10 12:00:00")
        adm.exercise_attempt(conn, u, adm.first_exercise(conn, lid), at="2026-02-10 09:00:00")          # older than 30 days: counted as an attempt, not as an active day in the last 30
    ref = expected_ref(u)
    d = get(admin, f"{LL}/{ref}")
    assert d == {"suppressed": False, "ref": ref, "language": "hi", "cefr": "A1", "age_group": "adult", "joined": "2026-03-01", "last_active": "2026-03-13",
                 "totals": {"lessons_started": 1, "lessons_completed": 1, "situations_started": 1, "situations_completed": 0, "exercise_attempts": 5, "exercise_correct": 3,
                            "listening_attempts": 2, "listening_correct": 1, "speaking_attempts": 1, "roleplay_sessions_started": 1, "roleplay_sessions_completed": 1,
                            "xp_total": 27, "achievements_unlocked": 1, "active_days_30": 4}}      # a session or a progress row is not evidence: last active is the 13th, over four days
    assert get(admin, f"{LL}/{ref}") == d


def test_detail_is_withheld_while_fewer_than_five_learners_exist(admin):
    with connect(main.DB_PATH) as conn:
        one = learners(conn, 4)
    assert get(admin, f"{LL}/{expected_ref(one[0])}") == {"suppressed": True, "ref": expected_ref(one[0]), "language": None, "cefr": None, "age_group": None, "joined": None,
                                                         "last_active": None, "totals": None}
    with connect(main.DB_PATH) as conn:
        learners(conn, 1)
    assert get(admin, f"{LL}/{expected_ref(one[0])}")["suppressed"] is False


def test_detail_hides_the_attributes_of_a_learner_in_a_small_cell(admin):
    with connect(main.DB_PATH) as conn:
        a, t, lone = world(conn)
    d = get(admin, f"{LL}/{expected_ref(lone[0])}")
    assert (d["language"], d["cefr"], d["age_group"]) == (None, None, None) and d["totals"]["lessons_started"] == 0


def test_unknown_or_malformed_references_are_refused_not_guessed(admin):
    with connect(main.DB_PATH) as conn:
        a, _, _ = world(conn)
    assert admin.get(f"{LL}/{'0' * 32}").status_code == 404
    real = expected_ref(a[0])
    assert admin.get(f"{LL}/{real[:-1] + ('0' if real[-1] != '0' else '1')}").status_code == 404                     # one character off
    for bad in ("1", str(a[0]), "x" * 32, expected_ref(a[0]).upper(), expected_ref(a[0]) + "0", "../etc/passwd"):
        assert admin.get(f"{LL}/{bad}").status_code in (404, 422), bad


def test_references_only_resolve_learners_never_staff_parents_or_the_demo_account(admin):
    with connect(main.DB_PATH) as conn:
        world(conn)
        parent, staff = adm.add_user(conn, "parent"), adm.add_user(conn, "admin")
        demo = conn.execute("SELECT id FROM users WHERE handle = 'demo-alex'").fetchone()[0]
    for uid in (parent, staff, demo):
        assert admin.get(f"{LL}/{expected_ref(uid)}").status_code == 404


def test_reading_the_overview_writes_no_audit_event_and_issues_no_session(admin, audit_rows):
    with connect(main.DB_PATH) as conn:
        a, _, _ = world(conn)
        before = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
    for url in (LL, f"{LL}/{expected_ref(a[0])}"):
        r = admin.get(url)
        assert r.status_code == 200 and "set-cookie" not in r.headers
    with connect(main.DB_PATH) as conn:
        assert conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == before
    assert audit_rows() == []
    assert admin.get("/api/auth/me").json()["user"]["roles"] == ["admin"]


@pytest.mark.parametrize("url", [LL, f"{LL}/{'a' * 32}"])
def test_overview_refuses_everyone_but_admins(client, admin, url):
    for who in (Api(), register_browser("learner", "l@example.com"), register_browser("parent", "p@example.com"), demo_browser()):
        assert who.get(url).status_code in (401, 403)


def test_the_service_never_returns_a_raw_id():
    import inspect
    assert "user_id" not in inspect.getsource(learners_service.list_learners).replace("repo.list_ids", "")
    assert learners_service.ref_for(7) == expected_ref(7)


# ---------- health ----------
H = "/api/admin/health"


def test_health_reports_safe_facts(admin, monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "1")
    h = get(admin, H)
    assert set(h) == {"app_version", "last_migration", "database", "content", "demo_mode", "providers", "security"}
    assert h["app_version"] == settings.APP_VERSION and h["last_migration"]["version"] == "0056" and h["last_migration"]["name"] == "dogri_a1" and h["last_migration"]["applied_at"]
    assert h["database"] == {"integrity": "ok", "foreign_keys": "ok"} and h["demo_mode"] is True
    assert h["content"] == {"lessons": {"draft": 0, "published": 157, "archived": 0}, "situations": {"draft": 0, "published": 111, "archived": 0}, "listening_activities": {"draft": 0, "published": 315, "archived": 0}}


def test_health_counts_follow_the_lifecycle(admin):
    with connect(main.DB_PATH) as conn:
        adm.make_lesson(conn, "d1")
        adm.make_lesson(conn, "d2")
        adm.make_lesson(conn, "a1", status="archived")
        adm.make_situation(conn, "d3")
        adm.make_activity(conn, "d4", status="archived")
    c = get(admin, H)["content"]
    assert c["lessons"] == {"draft": 2, "published": 157, "archived": 1} and c["situations"] == {"draft": 1, "published": 111, "archived": 0} and c["listening_activities"] == {"draft": 0, "published": 315, "archived": 1}


def test_demo_mode_is_reported_as_it_is(admin, monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "0")
    assert get(admin, H)["demo_mode"] is False
    monkeypatch.setenv("DEMO_MODE", "1")
    assert get(admin, H)["demo_mode"] is True


def test_providers_are_booleans_and_secrets_never_appear(admin, monkeypatch, tmp_path):
    for k in ("GROQ_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OLLAMA_URL"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.delenv("AI_PROVIDER", raising=False)
    assert get(admin, H)["providers"] == {"llm_configured": False, "speech_to_text_configured": False, "pronunciation_configured": False, "tutor_uses_llm": False}
    monkeypatch.setenv("GROQ_API_KEY", "gsk_SECRET_KEY_VALUE")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-SECRET")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-SECRET")
    monkeypatch.setenv("OLLAMA_URL", "http://secret-host.internal:11434")
    monkeypatch.setenv("STT_PROVIDER", "mock")
    monkeypatch.setenv("PRONUNCIATION_PROVIDER", "mock")
    monkeypatch.setenv("AI_PROVIDER", "llm")
    r = admin.get(H)
    assert r.json()["providers"] == {"llm_configured": True, "speech_to_text_configured": True, "pronunciation_configured": True, "tutor_uses_llm": True}
    assert not any(s in r.text for s in ("SECRET", "secret-host", "gsk_", "sk-", "http", ".internal", str(tmp_path), "buddy.db", "/Users", "/private", "RECORDINGS"))


@pytest.mark.parametrize("key", ["GROQ_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OLLAMA_URL"])
def test_any_one_llm_credential_counts_as_configured(admin, monkeypatch, key):
    for k in ("GROQ_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OLLAMA_URL"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv(key, "x")
    assert get(admin, H)["providers"]["llm_configured"] is True
    monkeypatch.setenv(key, "   ")
    assert get(admin, H)["providers"]["llm_configured"] is False


def test_database_problems_are_reported_without_sqlites_message(admin, monkeypatch):
    calls = []
    real = admin_content.integrity_check
    monkeypatch.setattr(admin_content, "integrity_check", lambda conn: calls.append(1) or ["*** in database main *** Page 3: btree problem"])
    r = admin.get(H)
    assert calls and r.json()["database"]["integrity"] == "failed" and "btree" not in r.text and "Page 3" not in r.text
    monkeypatch.setattr(admin_content, "integrity_check", real)
    with connect(main.DB_PATH) as conn:
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute("INSERT INTO lesson_topics(lesson_id, topic_id) VALUES (99999, 1)")
        conn.commit()
    assert get(admin, H)["database"] == {"integrity": "ok", "foreign_keys": "violations"}


def test_health_refuses_everyone_but_admins(client, admin):
    for who in (Api(), register_browser("learner", "l@example.com"), register_browser("parent", "p@example.com"), demo_browser()):
        assert who.get(H).status_code in (401, 403) and who.get(H + "/integrity").status_code in (401, 403)


# ---------- integrity ----------
def test_the_integrity_endpoint_is_the_same_sweep_as_validate_all(admin):
    with connect(main.DB_PATH) as conn:
        lid = adm.make_lesson(conn, "broken")
        conn.execute("DELETE FROM exercises WHERE lesson_id = ?", (lid,))
        adm.make_activity(conn, "short", status="published")
        conn.execute("DELETE FROM listening_options WHERE id = (SELECT MAX(id) FROM listening_options WHERE activity_id = (SELECT id FROM listening_activities WHERE slug = 'short'))")
    a, b = get(admin, H + "/integrity"), get(admin, "/api/admin/validate/all")
    assert a == b and a["ok"] is False and a["published_errors"] == 1
    assert sorted((f["code"], f["entity_status"]) for f in a["findings"] if f["severity"] == "error") == [("lesson_no_exercises", "draft"), ("listening_option_count", "published")]


def test_integrity_covers_every_check_the_design_lists(admin):
    """Orphans, broken references, incomplete content, invalid lifecycle state, curriculum invariants: each is produced by real rows."""
    with connect(main.DB_PATH) as conn:
        lid = adm.make_lesson(conn, "lifecycle-bad", status="archived")
        conn.execute("DROP TRIGGER lessons_archived_stamp_update")
        conn.execute("UPDATE lessons SET archived_at = NULL WHERE id = ?", (lid,))
        conn.execute("INSERT INTO vocabulary_items(language_id, cefr_code, kind, text) VALUES (10, 'A1', 'word', 'orphan-one')")
        conn.execute("INSERT INTO topics(slug, name, icon) VALUES ('orphan-topic', 'O', 'o')")
        conn.commit()
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute("INSERT INTO lesson_topics(lesson_id, topic_id) VALUES (99999, 1)")
        empty = conn.execute("INSERT INTO lessons(language_id, cefr_code, slug, title, description, sort_order) VALUES (10, 'A1', 'empty-lesson', 'E', 'd', 97)").lastrowid
        conn.commit()
    codes = {f["code"] for f in get(admin, H + "/integrity")["findings"]}
    assert {"lifecycle_archived_without_time", "integrity_orphan_vocabulary", "integrity_orphan_topic", "integrity_foreign_key", "lesson_no_exercises", "lesson_no_topics",
            "lesson_no_vocabulary"} <= codes and empty


def test_a_cell_of_exactly_five_shows_its_attributes_and_four_hides_them(admin):
    with connect(main.DB_PATH) as conn:
        five = learners(conn, 5, level="A1")
        four = learners(conn, 4, level="A2")
    by_ref = {i["ref"]: i for i in get(admin, LL + "?limit=100")["items"]}
    assert all(by_ref[expected_ref(u)]["cefr"] == "A1" for u in five) and all(by_ref[expected_ref(u)]["cefr"] is None for u in four)


@pytest.mark.parametrize("day,counted", [("2026-02-14", True), ("2026-02-13", False)])
def test_active_days_look_back_exactly_thirty_days_including_today(admin, day, counted):
    with connect(main.DB_PATH) as conn:
        a, _, _ = world(conn)
        adm.exercise_attempt(conn, a[0], adm.first_exercise(conn, adm.lesson_id(conn)), at=f"{day} 12:00:00")
    assert get(admin, f"{LL}/{expected_ref(a[0])}")["totals"]["active_days_30"] == (1 if counted else 0)
