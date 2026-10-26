"""Phase 13A: migration 0025_admin_cms.sql. The audit table, the publish metadata, archive integrity, delete protection and the indexes."""
import json
import shutil
import sqlite3

import pytest

from backend.db import connect
from backend.db.migrate import MIGRATIONS_DIR, migrate

from . import adm
from .adm import activity_id, add_user, lesson_id, one, raises_integrity, situation_id

LIFECYCLE_TABLES = ["lessons", "situations", "listening_activities"]
EVIDENCE_TABLES = ["users", "user_roles", "learner_profiles", "lesson_progress", "exercise_attempts", "situation_progress", "situation_step_attempts",
                   "listening_attempts", "audio_sessions", "xp_events", "weaknesses", "daily_tasks", "roleplay_sessions", "roleplay_turns", "state"]


def dump(conn, table):
    return [tuple(r) for r in conn.execute(f"SELECT * FROM {table} ORDER BY 1, 2")]


# ---------- the migration itself ----------
def test_phase_13_added_exactly_one_migration_0025():
    """0025 is Phase 13's only migration; the ones after it belong to Phase 14 (0026 session hardening, 0027 two-factor, 0028 security events) and to the city packs (0029 Mumbai, 0030 Marathi, 0031-0035 the Marathi curriculum, 0036 Kannada for Bengaluru, 0037-0038 the Kannada curriculum, 0039-0042 Tamil for Chennai, 0043-0045 Puducherry and French, 0046 Jaipur and Lucknow, 0047-0049 Kolkata and Bengali, 0050-0052 Hyderabad, Telugu and Urdu, 0053 Bhopal, 0054-0056 Jammu & Kashmir, Kashmiri and Dogri)."""
    versions = [f.name.split("_")[0] for f in sorted(MIGRATIONS_DIR.glob("*.sql"))]
    assert versions[23:57] == ["0024", "0025", "0026", "0027", "0028", "0029", "0030", "0031", "0032", "0033", "0034", "0035", "0036", "0037", "0038", "0039", "0040", "0041", "0042", "0043", "0044", "0045", "0046", "0047", "0048", "0049", "0050", "0051", "0052", "0053", "0054", "0055", "0056", "0057"] and len(versions) == 57
    assert (MIGRATIONS_DIR / "0025_admin_cms.sql").exists() and (MIGRATIONS_DIR / "0026_session_hardening.sql").exists()


def test_migration_applies_to_an_empty_database_and_is_idempotent(tmp_path):
    path = tmp_path / "t.db"
    assert migrate(path)[-33:] == ["0025", "0026", "0027", "0028", "0029", "0030", "0031", "0032", "0033", "0034", "0035", "0036", "0037", "0038", "0039", "0040", "0041", "0042", "0043", "0044", "0045", "0046", "0047", "0048", "0049", "0050", "0051", "0052", "0053", "0054", "0055", "0056", "0057"]
    assert migrate(path) == []
    with connect(path) as conn:
        assert one(conn, "SELECT COUNT(*) FROM admin_audit_log") == 0                       # nothing is logged by merely migrating
        assert one(conn, "SELECT COUNT(*) FROM schema_migrations WHERE version = '0025'") == 1


@pytest.fixture
def phase12_dir(tmp_path):
    """Migrations 0001-0024 only: the database exactly as Phase 12 left it."""
    d = tmp_path / "phase12"
    d.mkdir()
    for f in sorted(MIGRATIONS_DIR.glob("*.sql")):
        if f.name < "0025":
            shutil.copy(f, d / f.name)
    return d


def test_the_only_new_table_is_the_audit_log_and_there_are_no_analytics_tables(db_path, tmp_path, phase12_dir):
    old = tmp_path / "old.db"
    migrate(old, phase12_dir)
    names = lambda p: {r[0] for r in sqlite3.connect(p).execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert names(db_path) - names(old) == {"admin_audit_log", "two_factor_credentials", "recovery_codes", "login_challenges", "mfa_failures", "security_events",
                                           "content_reviews"}   # + Phase 14D/E's (0027, 0028) and the content review record (0034)
    assert names(old) - names(db_path) == set()


def test_existing_published_content_stays_published_and_is_backfilled(tmp_path, phase12_dir):
    path = tmp_path / "t.db"
    assert migrate(path, phase12_dir)[-1] == "0024"
    with connect(path) as conn:
        counts = {t: dict(conn.execute(f"SELECT status, COUNT(*) FROM {t} GROUP BY status").fetchall()) for t in LIFECYCLE_TABLES}
        conn.execute("UPDATE lessons SET status = 'draft' WHERE slug = 'food' AND language_id = (SELECT id FROM languages WHERE code='hi')")             # one non-published row, to see the backfill leave it alone
    assert migrate(path) == ["0025", "0026", "0027", "0028", "0029", "0030", "0031", "0032", "0033", "0034", "0035", "0036", "0037", "0038", "0039", "0040", "0041", "0042", "0043", "0044", "0045", "0046", "0047", "0048", "0049", "0050", "0051", "0052", "0053", "0054", "0055", "0056", "0057"]
    with connect(path) as conn:
        hindi = "language_id = (SELECT id FROM languages WHERE code = 'hi')"
        assert one(conn, f"SELECT status FROM lessons WHERE slug = 'food' AND {hindi}") == "draft"
        assert one(conn, f"SELECT published_at FROM lessons WHERE slug = 'food' AND {hindi}") is None
        # the content that existed keeps its status; 0031 adds Marathi's 7 lessons, published with a publish time (and 0037-0038 Kannada's, below)
        assert one(conn, "SELECT COUNT(*) FROM lessons WHERE language_id = (SELECT id FROM languages WHERE code = 'mr') AND status = 'published' AND published_at IS NOT NULL") == 27
        assert one(conn, "SELECT COUNT(*) FROM lessons WHERE language_id = (SELECT id FROM languages WHERE code = 'kn') AND status = 'published' AND published_at IS NOT NULL") == 25
        assert one(conn, "SELECT COUNT(*) FROM lessons WHERE language_id = (SELECT id FROM languages WHERE code = 'ta') AND status = 'published' AND published_at IS NOT NULL") == 28
        assert one(conn, "SELECT COUNT(*) FROM lessons WHERE language_id = (SELECT id FROM languages WHERE code = 'fr') AND status = 'published' AND published_at IS NOT NULL") == 9
        for t in LIFECYCLE_TABLES:
            after = dict(conn.execute(f"SELECT status, COUNT(*) FROM {t} WHERE language_id NOT IN (SELECT id FROM languages WHERE code IN ('mr', 'kn', 'ta', 'fr', 'bn', 'te', 'ur', 'ks', 'doi')) GROUP BY status").fetchall())
            expected = dict(counts[t])
            if t == "lessons":
                expected["published"] -= 1
                expected["draft"] = 1
            assert after == expected
            assert one(conn, f"SELECT COUNT(*) FROM {t} WHERE status = 'published' AND (published_at IS NULL OR archived_at IS NOT NULL)") == 0
            assert one(conn, f"SELECT COUNT(*) FROM {t} WHERE updated_at IS NULL OR revision <> 1") == 0


def test_upgrade_leaves_every_piece_of_learner_evidence_byte_identical(tmp_path, phase12_dir):
    path = tmp_path / "t.db"
    migrate(path, phase12_dir)
    with connect(path) as conn:
        u = add_user(conn)
        adm.add_profile(conn, u)
        lid, sid, aid = lesson_id(conn), situation_id(conn), activity_id(conn)
        adm.lesson_progress(conn, u, lid)
        ex = adm.exercise_attempt(conn, u, adm.first_exercise(conn, lid))
        adm.situation_progress(conn, u, sid)
        step = adm.step_attempt(conn, u, adm.first_step(conn, sid))
        adm.listening_attempt(conn, u, aid, adm.wrong_option(conn, aid))
        adm.xp(conn, u, ex)
        adm.weakness(conn, u)
        adm.daily_task(conn, u, lid=lid)
        conn.execute("INSERT INTO state(user_id, data) VALUES ('demo-alex', '{\"xp\": 5}')")
        rs = adm.roleplay_session(conn, u, sid)
        adm.roleplay_turn(conn, u, rs, sid, adm.first_step(conn, sid))
        assert ex and step
        snapshot = {t: dump(conn, t) for t in EVIDENCE_TABLES}
        for t in EVIDENCE_TABLES:
            assert snapshot[t], f"the fixture must put a row in {t}, or the comparison below proves nothing"
    assert migrate(path) == ["0025", "0026", "0027", "0028", "0029", "0030", "0031", "0032", "0033", "0034", "0035", "0036", "0037", "0038", "0039", "0040", "0041", "0042", "0043", "0044", "0045", "0046", "0047", "0048", "0049", "0050", "0051", "0052", "0053", "0054", "0055", "0056", "0057"]
    with connect(path) as conn:
        for t in EVIDENCE_TABLES:
            assert dump(conn, t) == snapshot[t], t


def test_content_tables_gain_only_additive_columns(db_path):
    with connect(db_path) as conn:
        for t in LIFECYCLE_TABLES:
            cols = {r["name"]: r for r in conn.execute(f"PRAGMA table_info({t})")}
            for c in ("published_at", "archived_at", "updated_at"):
                assert cols[c]["type"] == "TEXT" and cols[c]["notnull"] == 0, (t, c)
            assert cols["revision"]["notnull"] == 1 and cols["revision"]["dflt_value"] == "1"
        # a row inserted the old way (as every earlier phase's tests do) still works and starts at revision 1
        conn.execute("INSERT INTO lessons(language_id, cefr_code, slug, title, description, sort_order) VALUES (10, 'A1', 'old-way', 't', 'd', 99)")
        assert one(conn, "SELECT revision FROM lessons WHERE slug = 'old-way'") == 1
        assert one(conn, "SELECT status FROM lessons WHERE slug = 'old-way'") == "draft"


# ---------- the audit table ----------
AUDIT = "INSERT INTO admin_audit_log(actor_user_id, actor_label, action, entity_type, entity_id, entity_key, outcome, meta_json, request_id) VALUES "


def audit_row(actor="NULL", label="'admin'", action="'publish'", entity="'lesson'", eid="1", key="'food'", outcome="'ok'", meta="'{}'", req="'r1'"):
    return AUDIT + f"({actor}, {label}, {action}, {entity}, {eid}, {key}, {outcome}, {meta}, {req})"


def test_an_audit_event_records_who_what_and_when(db_path):
    with connect(db_path) as conn:
        a = add_user(conn, "admin", "adm1")
        conn.execute(audit_row(actor=a, label="'adm1'"))
        row = conn.execute("SELECT * FROM admin_audit_log").fetchone()
        assert (row["actor_user_id"], row["actor_label"], row["action"], row["entity_type"], row["entity_id"], row["entity_key"], row["outcome"]) == (a, "adm1", "publish", "lesson", 1, "food", "ok")
        assert row["meta_json"] == "{}" and row["request_id"] == "r1"
        assert len(row["occurred_at"]) == 19 and row["occurred_at"][4] == "-"                # UTC 'YYYY-MM-DD HH:MM:SS' like every other timestamp


@pytest.mark.parametrize("action", ["create", "update", "publish", "unpublish", "archive", "restore", "validation_failed", "config_change", "login_denied"])
def test_every_documented_action_is_accepted(db_path, action):
    with connect(db_path) as conn:
        conn.execute(audit_row(action=f"'{action}'"))
        assert one(conn, "SELECT action FROM admin_audit_log") == action


@pytest.mark.parametrize("entity", ["lesson", "exercise", "lesson_vocabulary", "situation", "situation_step", "listening_activity", "listening_option",
                                    "vocabulary", "vocabulary_translation", "topic", "admin_access", "config"])
def test_every_whitelisted_entity_type_is_accepted(db_path, entity):
    with connect(db_path) as conn:
        conn.execute(audit_row(entity=f"'{entity}'"))


@pytest.mark.parametrize("kwargs", [
    {"action": "'delete'"},                                  # the CMS has no delete, so the log has no such action
    {"action": "'remove'"}, {"action": "''"},
    {"entity": "'users'"}, {"entity": "'password'"}, {"entity": "''"},
    {"outcome": "'maybe'"}, {"outcome": "'OK'"},
    {"meta": "'not json'"}, {"meta": "'{\"a\":'"},
    {"meta": "'{\"k\":\"" + "x" * 4090 + "\"}'"},            # over 4096 bytes
    {"label": "''"}, {"label": "'   '"}, {"label": "'" + "x" * 65 + "'"},
    {"key": "'" + "k" * 121 + "'"},
    {"req": "'" + "r" * 65 + "'"},
    {"actor": "99999"},                                      # unknown user
])
def test_audit_constraints_refuse_bad_rows(db_path, kwargs):
    raises_integrity(db_path, audit_row(**kwargs))


def test_meta_limit_counts_bytes_not_characters(db_path):
    ok = json.dumps({"k": "x" * 4000})
    over = json.dumps({"k": "é" * 2100}, ensure_ascii=False)            # 2100 characters but 4200+ bytes
    assert len(over) < 4096 < len(over.encode())
    with connect(db_path) as conn:
        conn.execute(AUDIT + "(NULL, 'a', 'create', 'lesson', 1, NULL, 'ok', ?, NULL)", (ok,))
    with pytest.raises(sqlite3.IntegrityError):
        with connect(db_path) as conn:
            conn.execute(AUDIT + "(NULL, 'a', 'create', 'lesson', 1, NULL, 'ok', ?, NULL)", (over,))


def test_audit_events_cannot_be_updated_or_deleted(db_path):
    with connect(db_path) as conn:
        conn.execute(audit_row())
    for sql in ("UPDATE admin_audit_log SET outcome = 'rejected'", "UPDATE admin_audit_log SET meta_json = '{\"a\":1}'", "UPDATE admin_audit_log SET actor_label = 'someone else'",
                "UPDATE admin_audit_log SET action = 'archive'", "UPDATE admin_audit_log SET entity_id = 2", "UPDATE admin_audit_log SET occurred_at = '2000-01-01 00:00:00'",
                "UPDATE admin_audit_log SET id = 7", "DELETE FROM admin_audit_log"):
        raises_integrity(db_path, sql)
    with connect(db_path) as conn:
        row = conn.execute("SELECT * FROM admin_audit_log").fetchone()
        assert (row["outcome"], row["meta_json"], row["actor_label"], row["action"], row["entity_id"], row["id"]) == ("ok", "{}", "admin", "publish", 1, 1)


def test_deleting_an_account_clears_only_the_actor_link_and_keeps_the_label(db_path):
    with connect(db_path) as conn:
        a = add_user(conn, "admin", "adm1")
        conn.execute(audit_row(actor=a, label="'adm1'", meta="'{\"revision_after\":2}'"))
        before = tuple(conn.execute("SELECT id, occurred_at, actor_label, action, entity_type, entity_id, entity_key, outcome, meta_json, request_id FROM admin_audit_log").fetchone())
        conn.execute("DELETE FROM users WHERE id = ?", (a,))                    # the FK's ON DELETE SET NULL runs through the immutability trigger
        row = conn.execute("SELECT * FROM admin_audit_log").fetchone()
        assert row["actor_user_id"] is None
        assert tuple(row[k] for k in ("id", "occurred_at", "actor_label", "action", "entity_type", "entity_id", "entity_key", "outcome", "meta_json", "request_id")) == before


def test_the_actor_link_cannot_be_pointed_at_someone_else_or_restored(db_path):
    with connect(db_path) as conn:
        a, b = add_user(conn, "admin", "adm1"), add_user(conn, "admin", "adm2")
        conn.execute(audit_row(actor=a, label="'adm1'"))
    raises_integrity(db_path, "UPDATE admin_audit_log SET actor_user_id = ?", b)         # forging the actor
    with connect(db_path) as conn:
        conn.execute("DELETE FROM users WHERE id = ?", (a,))
    raises_integrity(db_path, "UPDATE admin_audit_log SET actor_user_id = ?", b)         # an orphaned event cannot be reattributed


def test_even_a_no_op_update_is_refused_on_a_live_or_an_orphaned_event(db_path):
    with connect(db_path) as conn:
        a = add_user(conn, "admin", "adm1")
        conn.execute(audit_row(actor=a, label="'adm1'"))
    raises_integrity(db_path, "UPDATE admin_audit_log SET outcome = outcome")
    with connect(db_path) as conn:
        conn.execute("DELETE FROM users WHERE id = ?", (a,))
    raises_integrity(db_path, "UPDATE admin_audit_log SET outcome = outcome")


def test_audit_log_has_the_documented_columns_and_indexes(db_path):
    with connect(db_path) as conn:
        cols = [r["name"] for r in conn.execute("PRAGMA table_info(admin_audit_log)")]
        assert cols == ["id", "occurred_at", "actor_user_id", "actor_label", "action", "entity_type", "entity_id", "entity_key", "outcome", "meta_json", "request_id"]
        indexes = {r["name"]: [c["name"] for c in conn.execute(f"PRAGMA index_info({r['name']})")] for r in conn.execute("PRAGMA index_list(admin_audit_log)")}
        assert indexes["idx_admin_audit_time"] == ["occurred_at"]
        assert indexes["idx_admin_audit_entity"] == ["entity_type", "entity_id", "occurred_at"]
        assert indexes["idx_admin_audit_actor"] == ["actor_user_id", "occurred_at"]
        fk = [r for r in conn.execute("PRAGMA foreign_key_list(admin_audit_log)")]
        assert [(r["table"], r["from"], r["on_delete"]) for r in fk] == [("users", "actor_user_id", "SET NULL")]


# ---------- archive integrity ----------
INSERTS = {
    "lessons": "INSERT INTO lessons(language_id, cefr_code, slug, title, description, sort_order, status, archived_at) VALUES (10, 'A1', 'zz', 't', 'd', 98, 'archived', {at})",
    "situations": "INSERT INTO situations(language_id, cefr_code, topic_id, slug, title, description, difficulty, sort_order, status, archived_at) "
                  "VALUES (10, 'A1', 1, 'zz', 't', 'd', 1, 98, 'archived', {at})",
    "listening_activities": "INSERT INTO listening_activities(language_id, cefr_code, topic_id, item_id, slug, title, mode, prompt, difficulty, sort_order, status, archived_at) "
                            "VALUES (10, 'A1', 1, (SELECT id FROM vocabulary_items WHERE language_id = 10 LIMIT 1), 'zz', 't', 'choose_meaning', 'p', 1, 98, 'archived', {at})",
}


STAMP_FORMAT = r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$"


@pytest.mark.parametrize("table", LIFECYCLE_TABLES)
def test_an_archived_row_inserted_without_a_time_is_stamped(db_path, table):
    import re
    with connect(db_path) as conn:
        conn.execute(INSERTS[table].format(at="NULL"))
        stamped = one(conn, f"SELECT archived_at FROM {table} WHERE slug = 'zz'")
    assert stamped is not None and re.match(STAMP_FORMAT, stamped)


@pytest.mark.parametrize("table", LIFECYCLE_TABLES)
def test_an_explicit_archive_time_is_kept_as_given(db_path, table):
    with connect(db_path) as conn:
        conn.execute(INSERTS[table].format(at="'2026-01-01 00:00:00'"))
        assert one(conn, f"SELECT archived_at FROM {table} WHERE slug = 'zz'") == "2026-01-01 00:00:00"
        conn.execute(f"UPDATE {table} SET archived_at = '2026-02-02 02:02:02' WHERE slug = 'zz'")
        assert one(conn, f"SELECT archived_at FROM {table} WHERE slug = 'zz'") == "2026-02-02 02:02:02"


@pytest.mark.parametrize("table", LIFECYCLE_TABLES)
def test_archiving_with_a_bare_status_update_still_works_and_is_stamped(db_path, table):
    """The earlier phases archive with a plain UPDATE (tests/test_adaptive_api.py does): that keeps working, and the row cannot be archived without a time."""
    import re
    with connect(db_path) as conn:
        conn.execute(f"UPDATE {table} SET status = 'archived' WHERE id = (SELECT MIN(id) FROM {table})")
        stamped = one(conn, f"SELECT archived_at FROM {table} WHERE status = 'archived'")
        assert stamped is not None and re.match(STAMP_FORMAT, stamped)
        assert one(conn, f"SELECT COUNT(*) FROM {table} WHERE status = 'archived' AND archived_at IS NULL") == 0


@pytest.mark.parametrize("table", LIFECYCLE_TABLES)
def test_clearing_the_time_of_an_archived_row_cannot_leave_it_empty(db_path, table):
    with connect(db_path) as conn:
        conn.execute(f"UPDATE {table} SET status = 'archived', archived_at = '2026-01-01 00:00:00' WHERE id = (SELECT MIN(id) FROM {table})")
        conn.execute(f"UPDATE {table} SET archived_at = NULL WHERE status = 'archived'")
        assert one(conn, f"SELECT COUNT(*) FROM {table} WHERE status = 'archived' AND archived_at IS NULL") == 0


@pytest.mark.parametrize("table", LIFECYCLE_TABLES)
def test_leaving_the_archive_clears_the_time_freely(db_path, table):
    with connect(db_path) as conn:
        conn.execute(f"UPDATE {table} SET status = 'archived', archived_at = '2026-01-01 00:00:00' WHERE id = (SELECT MIN(id) FROM {table})")
        conn.execute(f"UPDATE {table} SET status = 'draft', archived_at = NULL WHERE status = 'archived'")
        assert one(conn, f"SELECT COUNT(*) FROM {table} WHERE status = 'archived'") == 0 and one(conn, f"SELECT COUNT(*) FROM {table} WHERE archived_at IS NOT NULL") == 0


# ---------- delete protection ----------
PARENTS = ["lessons", "situations", "listening_activities", "exercises", "situation_steps", "vocabulary_items", "topics"]
# Tables that are themselves content (or content links): they cascade with their parent but hold no learner evidence.
STRUCTURAL = {"exercises", "exercise_answers", "situation_steps", "situation_step_answers", "listening_options", "lesson_topics", "lesson_vocabulary", "lesson_grammar",
              "lesson_age_groups", "situation_age_groups", "listening_activity_age_groups", "vocabulary_translations", "vocabulary_examples", "audio_assets",
              "grammar_examples", "grammar_topic_texts"}


def derived_cascade_edges(conn):
    """Every (child, parent) foreign key that cascades from a content table into something that is not content, read from the live schema."""
    edges = set()
    for t in [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")]:
        for fk in conn.execute(f"PRAGMA foreign_key_list({t})"):
            if fk["table"] in PARENTS and fk["on_delete"] == "CASCADE" and t not in STRUCTURAL:
                edges.add((t, fk["table"]))
    return edges


EXPECTED_EDGES = {("lesson_progress", "lessons"), ("daily_tasks", "lessons"), ("exercise_attempts", "exercises"), ("daily_tasks", "situations"),
                  ("situation_progress", "situations"), ("roleplay_sessions", "situations"), ("situation_step_attempts", "situation_steps"),
                  ("roleplay_turns", "situation_steps"), ("listening_attempts", "listening_activities"), ("weaknesses", "vocabulary_items"),
                  ("weaknesses", "topics"), ("daily_tasks", "topics")}


def test_the_cascade_edges_read_from_the_foreign_key_graph_are_the_ones_this_phase_covers(db_path):
    """If a later phase adds a table whose rows would be cascade-deleted with content, this fails until a trigger and a case below cover it."""
    with connect(db_path) as conn:
        assert derived_cascade_edges(conn) == EXPECTED_EDGES


def _evidence(conn, edge):
    """Create one piece of evidence for `edge`; returns the DELETE that would destroy it."""
    u = add_user(conn)
    adm.add_profile(conn, u)
    lid, sid, aid = lesson_id(conn), situation_id(conn), activity_id(conn)
    ex, step = adm.first_exercise(conn, lid), adm.first_step(conn, sid)
    topic = one(conn, "SELECT id FROM topics WHERE slug = 'food'")
    item = one(conn, "SELECT item_id FROM listening_activities WHERE id = ?", aid)
    if edge == ("lesson_progress", "lessons"):
        adm.lesson_progress(conn, u, lid)
        return "DELETE FROM lessons WHERE id = ?", lid
    if edge == ("daily_tasks", "lessons"):
        adm.daily_task(conn, u, lid=lid, status="done")
        return "DELETE FROM lessons WHERE id = ?", lid
    if edge == ("exercise_attempts", "exercises"):
        adm.exercise_attempt(conn, u, ex)
        return "DELETE FROM exercises WHERE id = ?", ex
    if edge == ("daily_tasks", "situations"):
        adm.daily_task(conn, u, sid=sid, status="skipped")
        return "DELETE FROM situations WHERE id = ?", sid
    if edge == ("situation_progress", "situations"):
        adm.situation_progress(conn, u, sid)
        return "DELETE FROM situations WHERE id = ?", sid
    if edge == ("roleplay_sessions", "situations"):
        adm.roleplay_session(conn, u, sid)
        return "DELETE FROM situations WHERE id = ?", sid
    if edge == ("situation_step_attempts", "situation_steps"):
        adm.step_attempt(conn, u, step)
        return "DELETE FROM situation_steps WHERE id = ?", step
    if edge == ("roleplay_turns", "situation_steps"):
        rs = adm.roleplay_session(conn, u, sid)
        adm.roleplay_turn(conn, u, rs, sid, step)
        return "DELETE FROM situation_steps WHERE id = ?", step
    if edge == ("listening_attempts", "listening_activities"):
        adm.listening_attempt(conn, u, aid, adm.wrong_option(conn, aid))
        return "DELETE FROM listening_activities WHERE id = ?", aid
    if edge == ("weaknesses", "vocabulary_items"):
        spare = conn.execute("INSERT INTO vocabulary_items(language_id, cefr_code, kind, text) VALUES (10, 'A1', 'word', 'spare-word')").lastrowid   # unreferenced by content
        adm.item_weakness(conn, u, spare)
        return "DELETE FROM vocabulary_items WHERE id = ?", spare
    if edge == ("weaknesses", "topics"):
        spare = conn.execute("INSERT INTO topics(slug, name, icon) VALUES ('spare-topic', 'Spare', 'x')").lastrowid
        conn.execute("INSERT INTO weaknesses(user_id, language_id, rule, topic_id, item_id, severity, attempts, incorrect, last_evidence_at, detected_at, status) "
                     f"VALUES (?, {adm.HI}, 'low_topic_accuracy', ?, NULL, 'low', 6, 3, ?, ?, 'active')", (u, spare, adm.STAMP, adm.STAMP))
        return "DELETE FROM topics WHERE id = ?", spare
    if edge == ("daily_tasks", "topics"):
        spare = conn.execute("INSERT INTO topics(slug, name, icon) VALUES ('spare-topic', 'Spare', 'x')").lastrowid
        adm.daily_task(conn, u, tid=spare, status="done")
        return "DELETE FROM topics WHERE id = ?", spare
    raise AssertionError(edge)


@pytest.mark.parametrize("edge", sorted(EXPECTED_EDGES))
def test_deleting_content_with_learner_evidence_is_refused_and_destroys_nothing(db_path, edge):
    child, parent = edge
    with connect(db_path) as conn:
        sql, pk = _evidence(conn, edge)
        evidence_before = {t: dump(conn, t) for t in EVIDENCE_TABLES if t != "users"}
        counts_before = {t: one(conn, f"SELECT COUNT(*) FROM {t}") for t in ("lessons", "exercises", "situations", "situation_steps", "listening_activities", "listening_options")}
    with pytest.raises(sqlite3.IntegrityError, match="cannot be deleted"):
        with connect(db_path) as conn:
            conn.execute(sql, (pk,))
    with connect(db_path) as conn:
        assert one(conn, f"SELECT COUNT(*) FROM {parent} WHERE id = ?", pk) == 1
        assert {t: dump(conn, t) for t in EVIDENCE_TABLES if t != "users"} == evidence_before
        assert {t: one(conn, f"SELECT COUNT(*) FROM {t}") for t in counts_before} == counts_before
        assert one(conn, f"SELECT COUNT(*) FROM {child}") >= 1


def test_deleting_a_lesson_is_refused_when_only_an_exercise_attempt_exists(db_path):
    """The attempt hangs off the lesson through its exercise: the lesson trigger has to look through it."""
    with connect(db_path) as conn:
        u = add_user(conn)
        lid = lesson_id(conn)
        adm.exercise_attempt(conn, u, adm.first_exercise(conn, lid))
        assert one(conn, "SELECT COUNT(*) FROM lesson_progress") == 0
    with pytest.raises(sqlite3.IntegrityError, match="a lesson with learner evidence cannot be deleted: archive it"):     # the lesson's own trigger, not only the exercise one it cascades to
        with connect(db_path) as conn:
            conn.execute("DELETE FROM lessons WHERE id = ?", (lid,))


def test_deleting_a_situation_is_refused_when_only_a_step_attempt_exists(db_path):
    with connect(db_path) as conn:
        u = add_user(conn)
        sid = situation_id(conn)
        adm.step_attempt(conn, u, adm.first_step(conn, sid))
        assert one(conn, "SELECT COUNT(*) FROM situation_progress") == 0
    with pytest.raises(sqlite3.IntegrityError, match="a situation with learner evidence cannot be deleted: archive it"):
        with connect(db_path) as conn:
            conn.execute("DELETE FROM situations WHERE id = ?", (sid,))


def test_content_without_evidence_can_still_be_deleted_as_before(db_path):
    """The earlier phases' own contract (a lesson / situation / activity cascades its content links) is untouched."""
    with connect(db_path) as conn:
        lid, sid, aid = lesson_id(conn), situation_id(conn), activity_id(conn)
        conn.execute("DELETE FROM lessons WHERE id = ?", (lid,))
        conn.execute("DELETE FROM situations WHERE id = ?", (sid,))
        conn.execute("DELETE FROM listening_activities WHERE id = ?", (aid,))
        assert one(conn, "SELECT COUNT(*) FROM exercises WHERE lesson_id = ?", lid) == 0
        assert one(conn, "SELECT COUNT(*) FROM situation_steps WHERE situation_id = ?", sid) == 0
        assert one(conn, "SELECT COUNT(*) FROM listening_options WHERE activity_id = ?", aid) == 0


def test_a_pending_daily_task_is_a_plan_row_and_still_cascades(db_path):
    """Documented, deliberate: only completed / skipped tasks are history. Phase 6's tests lock the cascade of a pending one."""
    with connect(db_path) as conn:
        u = add_user(conn)
        lid = lesson_id(conn)
        adm.daily_task(conn, u, lid=lid, status="pending")
        conn.execute("DELETE FROM lessons WHERE id = ?", (lid,))
        assert one(conn, "SELECT COUNT(*) FROM daily_tasks") == 0


def test_a_set_null_context_link_keeps_the_learners_row_as_before(db_path):
    with connect(db_path) as conn:
        u = add_user(conn)
        lid = lesson_id(conn)
        conn.execute(f"INSERT INTO confidence_scores(user_id, language_id, topic_id, score, source, lesson_id, recorded_at) "
                     f"VALUES (?, {adm.HI}, (SELECT id FROM topics WHERE slug='food'), 70, 'lesson', ?, ?)", (u, lid, adm.STAMP))
        conn.execute("DELETE FROM lessons WHERE id = ?", (lid,))
        assert one(conn, "SELECT COUNT(*) FROM confidence_scores") == 1 and one(conn, "SELECT lesson_id FROM confidence_scores") is None


def test_deleting_a_user_still_removes_their_own_evidence(db_path):
    """The protection is on content, not on learners: an account deletion still cascades that learner's own rows."""
    with connect(db_path) as conn:
        u = add_user(conn)
        lid = lesson_id(conn)
        adm.lesson_progress(conn, u, lid)
        adm.exercise_attempt(conn, u, adm.first_exercise(conn, lid))
        conn.execute("DELETE FROM users WHERE id = ?", (u,))
        assert one(conn, "SELECT COUNT(*) FROM lesson_progress") == 0 and one(conn, "SELECT COUNT(*) FROM exercise_attempts") == 0
        assert one(conn, "SELECT COUNT(*) FROM lessons WHERE id = ?", lid) == 1


def test_protection_ends_when_the_evidence_is_gone(db_path):
    with connect(db_path) as conn:
        u = add_user(conn)
        lid = lesson_id(conn)
        adm.lesson_progress(conn, u, lid)
    raises_integrity(db_path, "DELETE FROM lessons WHERE id = ?", lid)
    with connect(db_path) as conn:
        conn.execute("DELETE FROM lesson_progress")
        conn.execute("DELETE FROM lessons WHERE id = ?", (lid,))
        assert one(conn, "SELECT COUNT(*) FROM lessons WHERE id = ?", lid) == 0
