import sqlite3

import pytest

from backend.db import connect

HI = "(SELECT id FROM languages WHERE code='hi')"
FOOD = "(SELECT id FROM topics WHERE slug='food')"
ITEM = "(SELECT id FROM vocabulary_items WHERE pronunciation='Paani milega?')"
OTHER_ITEM = "(SELECT id FROM vocabulary_items WHERE pronunciation='Bill de dijiye.')"
DEMO = "(SELECT id FROM users WHERE handle='demo-alex')"


def one(conn, sql, *args):
    return conn.execute(sql, args).fetchone()[0]


def fails(db_path, sql, *args):
    with pytest.raises(sqlite3.IntegrityError):
        with connect(db_path) as conn:
            conn.execute(sql, args)


# ---------- audio_assets ----------
ASSET = "INSERT INTO audio_assets(item_id, language_id, provider, locale, voice, source_url, mime_type, duration_ms, is_active, created_at) VALUES "


def asset(provider="static", url="'/static/audio/x.mp3'", mime="audio/mpeg", dur="1200", active="1", item=ITEM):
    return ASSET + f"({item}, {HI}, '{provider}', 'hi-IN', NULL, {url}, '{mime}', {dur}, {active}, '2026-01-01 00:00:00')"


def test_assets_accept_each_provider(db_path):
    with connect(db_path) as conn:
        conn.execute(asset("static", "'/static/audio/a.mp3'"))
        conn.execute(asset("generated", "'/generated/a.ogg'", "audio/ogg"))
        conn.execute(asset("external_tts", "'https://tts.example.com/a.wav'", "audio/wav"))
        assert one(conn, "SELECT COUNT(DISTINCT provider) FROM audio_assets") == 3


@pytest.mark.parametrize("kwargs", [
    {"provider": "browser_tts"},                              # the fallback is runtime-only, never a stored source
    {"provider": "magic"},
    {"mime": "text/html"}, {"mime": "audio/midi"},
    {"dur": "0"}, {"dur": "-5"},
    {"active": "2"},
    {"url": "'javascript:alert(1)'"}, {"url": "'file:///etc/passwd'"}, {"url": "'http://insecure.example.com/a.mp3'"},
    {"url": "'//evil.example.com/a.mp3'"},                    # protocol-relative
    {"url": "'/static/../../etc/passwd'"},                    # path traversal
    {"url": "'/static/a b.mp3'"},
    {"url": "'relative/a.mp3'"},
    {"url": "NULL"},
])
def test_asset_constraints(db_path, kwargs):
    fails(db_path, asset(**kwargs))


def test_asset_uniqueness_and_item_integrity(db_path):
    with connect(db_path) as conn:
        conn.execute(asset())
        conn.execute(asset(url="'/static/audio/other.mp3'"))            # another file for the same item is fine
        conn.execute(asset(item=OTHER_ITEM))                             # the same file for another item is fine
    fails(db_path, asset())                                             # same item + same source twice
    fails(db_path, ASSET + f"(99999, {HI}, 'static', 'hi-IN', NULL, '/a.mp3', 'audio/mpeg', 1, 1, 'c')")            # unknown item
    fails(db_path, ASSET + f"({ITEM}, (SELECT id FROM languages WHERE code='en'), 'static', 'en-IN', NULL, '/b.mp3', 'audio/mpeg', 1, 1, 'c')")  # language disagrees with the item


def test_asset_deleted_with_its_item(db_path):
    with connect(db_path) as conn:
        conn.execute(asset())
        conn.execute("DELETE FROM listening_attempts")
        conn.execute("DELETE FROM listening_options WHERE item_id = " + ITEM)
        conn.execute("DELETE FROM listening_activities WHERE item_id = " + ITEM)
        conn.execute("DELETE FROM situation_steps WHERE item_id = " + ITEM)
        conn.execute("DELETE FROM exercises WHERE item_id = " + ITEM)
        conn.execute("DELETE FROM lesson_vocabulary WHERE item_id = " + ITEM)
        conn.execute("DELETE FROM vocabulary_items WHERE id = " + ITEM)
        assert one(conn, "SELECT COUNT(*) FROM audio_assets") == 0


def test_no_binary_audio_is_stored_in_the_database(db_path):
    with connect(db_path) as conn:
        for table in ("audio_assets", "listening_activities", "listening_options", "audio_sessions", "listening_attempts"):
            types = {r["type"].upper() for r in conn.execute(f"PRAGMA table_info({table})")}
            assert "BLOB" not in types, table


# ---------- listening_activities ----------
ACT = ("INSERT INTO listening_activities(language_id, cefr_code, topic_id, item_id, slug, title, mode, prompt, difficulty, sort_order, status) VALUES "
       "({lang}, '{cefr}', {topic}, {item}, '{slug}', 't', '{mode}', '{prompt}', {difficulty}, {order}, '{status}')")


def act(**kw):
    base = {"lang": HI, "cefr": "A1", "topic": FOOD, "item": ITEM, "slug": "extra", "mode": "choose_meaning", "prompt": "p", "difficulty": 1, "order": 50, "status": "published"}
    return ACT.format(**{**base, **kw})


def test_activity_accepts_a_valid_row(db_path):
    with connect(db_path) as conn:
        conn.execute(act())
        assert one(conn, "SELECT COUNT(*) FROM listening_activities WHERE language_id = (SELECT id FROM languages WHERE code='hi')") == 16


@pytest.mark.parametrize("kw", [
    {"cefr": "B1"},                                   # unsupported language/level combination
    {"lang": "(SELECT id FROM languages WHERE code='es')"},
    {"mode": "dictation"}, {"difficulty": 0}, {"difficulty": 4}, {"status": "live"},
    {"order": 0}, {"order": 1},                       # sort_order >= 1 and unique within language+level
    {"slug": "food-meaning"},                         # slug unique within the language
    {"prompt": "  "},
    {"topic": "(SELECT 999)"}, {"item": "(SELECT 999)"},
])
def test_activity_constraints(db_path, kw):
    fails(db_path, act(**kw))


def test_activity_item_must_share_the_activity_language(db_path):
    with connect(db_path) as conn:
        es = one(conn, "SELECT id FROM languages WHERE code='es'")
        conn.execute("INSERT INTO language_levels(language_id, cefr_code) VALUES (?, 'A1')", (es,))
        conn.execute("INSERT INTO vocabulary_items(language_id, cefr_code, kind, text) VALUES (?, 'A1', 'word', 'hola')", (es,))
    fails(db_path, act(slug="cross", item="(SELECT id FROM vocabulary_items WHERE text='hola')"))


def test_default_status_is_draft_and_topic_cannot_be_deleted_while_used(db_path):
    with connect(db_path) as conn:
        conn.execute(f"INSERT INTO listening_activities(language_id, cefr_code, topic_id, item_id, slug, title, mode, prompt, difficulty, sort_order) VALUES ({HI}, 'A1', {FOOD}, {ITEM}, 'd', 't', 'choose_meaning', 'p', 1, 60)")
        assert one(conn, "SELECT status FROM listening_activities WHERE slug='d'") == "draft"
    fails(db_path, "DELETE FROM topics WHERE slug='food'")


# ---------- listening_options ----------
def test_option_constraints(db_path):
    aid = "(SELECT id FROM listening_activities WHERE slug='food-meaning' AND language_id = (SELECT id FROM languages WHERE code='hi'))"
    ins = f"INSERT INTO listening_options(activity_id, language_id, item_id, sort_order) VALUES ({aid}, {HI}, "
    fails(db_path, ins + f"{OTHER_ITEM}, 1)")          # sort slot taken
    fails(db_path, ins + f"{OTHER_ITEM}, 0)")
    fails(db_path, ins + "(SELECT item_id FROM listening_options WHERE activity_id = " + aid + " LIMIT 1), 9)")  # item already an option
    fails(db_path, ins + "(SELECT 999), 9)")           # unknown item
    with connect(db_path) as conn:
        es = one(conn, "SELECT id FROM languages WHERE code='es'")
        conn.execute("INSERT INTO language_levels(language_id, cefr_code) VALUES (?, 'A1')", (es,))
        conn.execute("INSERT INTO vocabulary_items(language_id, cefr_code, kind, text) VALUES (?, 'A1', 'word', 'hola')", (es,))
        hola = one(conn, "SELECT id FROM vocabulary_items WHERE text='hola'")
    fails(db_path, ins + f"{hola}, 9)")                                                                    # other-language item in a Hindi activity
    fails(db_path, f"INSERT INTO listening_options(activity_id, language_id, item_id, sort_order) VALUES ({aid}, {es}, {hola}, 9)")   # language disagrees with the activity


def test_deleting_an_activity_cascades_to_options_but_keeps_vocabulary(db_path):
    with connect(db_path) as conn:
        vocab = one(conn, "SELECT COUNT(*) FROM vocabulary_items")
        conn.execute("DELETE FROM listening_activities WHERE slug='food-meaning' AND language_id = (SELECT id FROM languages WHERE code='hi')")
        assert one(conn, "SELECT COUNT(*) FROM listening_options WHERE activity_id NOT IN (SELECT id FROM listening_activities)") == 0
        assert one(conn, "SELECT COUNT(*) FROM listening_options WHERE language_id = (SELECT id FROM languages WHERE code='hi')") == 42
        assert one(conn, "SELECT COUNT(*) FROM vocabulary_items") == vocab


def test_vocabulary_used_by_listening_cannot_be_deleted(db_path):
    fails(db_path, "DELETE FROM vocabulary_items WHERE id = (SELECT item_id FROM listening_activities LIMIT 1)")


# ---------- audio_sessions ----------
SES = "INSERT INTO audio_sessions(user_id, language_id, kind, status, started_at, ended_at, duration_ms) VALUES "


@pytest.mark.parametrize("values", [
    f"({DEMO}, {HI}, 'dictation', 'completed', '2026-01-01 00:00:00', '2026-01-01 00:00:05', 5000)",     # kind vocabulary
    f"({DEMO}, {HI}, 'listening', 'paused', '2026-01-01 00:00:00', NULL, NULL)",                          # status vocabulary
    f"({DEMO}, {HI}, 'listening', 'started', '2026-01-01 00:00:00', '2026-01-01 00:00:05', NULL)",       # started must not have ended
    f"({DEMO}, {HI}, 'listening', 'completed', '2026-01-01 00:00:00', NULL, NULL)",                       # ended statuses need ended_at
    f"({DEMO}, {HI}, 'listening', 'completed', '2026-01-01 00:00:10', '2026-01-01 00:00:05', 5000)",     # ended before started
    f"({DEMO}, {HI}, 'listening', 'completed', '2026-01-01 00:00:00', '2026-01-01 00:00:05', -1)",       # negative duration
    f"(999, {HI}, 'listening', 'completed', '2026-01-01 00:00:00', '2026-01-01 00:00:05', 5000)",        # unknown user
    f"({DEMO}, 999, 'listening', 'completed', '2026-01-01 00:00:00', '2026-01-01 00:00:05', 5000)",      # unknown language
])
def test_session_constraints(db_path, values):
    fails(db_path, SES + values)


def test_session_lifecycle_statuses_and_speaking_kind_are_supported(db_path):
    with connect(db_path) as conn:
        conn.execute(SES + f"({DEMO}, {HI}, 'speaking', 'started', '2026-01-01 00:00:00', NULL, NULL)")        # ready for Phase 7B
        for status in ("completed", "abandoned", "failed"):
            conn.execute(SES + f"({DEMO}, {HI}, 'listening', '{status}', '2026-01-01 00:00:00', '2026-01-01 00:00:07', 7000)")
        assert one(conn, "SELECT COUNT(*) FROM audio_sessions") == 4


# ---------- listening_attempts ----------
ATT = "INSERT INTO listening_attempts(user_id, session_id, activity_id, option_id, is_correct, plays, attempted_at) VALUES "


def ids(conn):
    user = one(conn, "SELECT id FROM users WHERE handle='demo-alex'")
    a1, a2 = [r[0] for r in conn.execute("SELECT id FROM listening_activities ORDER BY id LIMIT 2")]
    o1 = one(conn, "SELECT id FROM listening_options WHERE activity_id=? LIMIT 1", a1)
    o2 = one(conn, "SELECT id FROM listening_options WHERE activity_id=? LIMIT 1", a2)
    return user, a1, a2, o1, o2


def new_session(conn, user):
    return conn.execute(SES + f"({user}, {HI}, 'listening', 'completed', '2026-01-01 00:00:00', '2026-01-01 00:00:05', 5000)").lastrowid


def test_attempt_accepts_a_consistent_row(db_path):
    with connect(db_path) as conn:
        user, a1, _, o1, _ = ids(conn)
        conn.execute(ATT + f"({user}, {new_session(conn, user)}, {a1}, {o1}, 1, 2, '2026-01-01 00:00:05')")
        assert one(conn, "SELECT COUNT(*) FROM listening_attempts") == 1


def test_attempt_constraints(db_path):
    with connect(db_path) as conn:
        user, a1, a2, o1, o2 = ids(conn)
        sess = new_session(conn, user)
        conn.execute("INSERT INTO users(handle, display_name) VALUES ('other', 'Other')")
        other = one(conn, "SELECT id FROM users WHERE handle='other'")
        other_sess = new_session(conn, other)
    fails(db_path, ATT + f"({user}, {sess}, {a1}, {o2}, 0, 0, 't')")      # option belongs to a different activity
    fails(db_path, ATT + f"({user}, {other_sess}, {a1}, {o1}, 0, 0, 't')")  # session belongs to a different learner
    fails(db_path, ATT + f"({user}, {sess}, {a1}, {o1}, 2, 0, 't')")      # is_correct domain
    fails(db_path, ATT + f"({user}, {sess}, {a1}, {o1}, 1, -1, 't')")     # plays range
    fails(db_path, ATT + f"({user}, {sess}, {a1}, {o1}, 1, 100, 't')")
    fails(db_path, ATT + f"({user}, 99999, {a1}, {o1}, 1, 0, 't')")        # unknown session
    fails(db_path, ATT + f"(999, {sess}, {a1}, {o1}, 1, 0, 't')")          # unknown user
    fails(db_path, ATT + f"({user}, {sess}, 99999, {o1}, 1, 0, 't')")      # unknown activity
    with connect(db_path) as conn:
        conn.execute(ATT + f"({user}, {sess}, {a1}, {o1}, 1, 0, 't')")
    fails(db_path, ATT + f"({user}, {sess}, {a1}, {o1}, 0, 0, 't2')")      # one attempt per session


def test_attempts_cascade_with_user_and_session_and_activity(db_path):
    with connect(db_path) as conn:
        user, a1, _, o1, _ = ids(conn)
        s = new_session(conn, user)
        conn.execute(ATT + f"({user}, {s}, {a1}, {o1}, 1, 0, 't')")
        conn.execute("DELETE FROM audio_sessions WHERE id=?", (s,))
        assert one(conn, "SELECT COUNT(*) FROM listening_attempts") == 0
        s = new_session(conn, user)
        conn.execute(ATT + f"({user}, {s}, {a1}, {o1}, 1, 0, 't')")
        conn.execute("DELETE FROM users WHERE id=?", (user,))
        assert one(conn, "SELECT COUNT(*) FROM listening_attempts") == 0 and one(conn, "SELECT COUNT(*) FROM audio_sessions") == 0


def test_an_option_with_attempts_cannot_be_deleted(db_path):
    with connect(db_path) as conn:
        user, a1, _, o1, _ = ids(conn)
        conn.execute(ATT + f"({user}, {new_session(conn, user)}, {a1}, {o1}, 1, 0, 't')")
    fails(db_path, "DELETE FROM listening_options WHERE id = ?", o1)


def test_expected_indexes_exist(db_path):
    with connect(db_path) as conn:
        names = {r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='index'")}
    assert {"idx_listening_activities_topic", "idx_listening_activities_item", "idx_listening_options_item", "idx_audio_sessions_user",
            "idx_listening_attempts_user_activity", "idx_listening_attempts_user_time"} <= names


# ---------- the personalization views now see listening ----------
def test_views_include_listening_attempts(db_path):
    with connect(db_path) as conn:
        user, a1, _, o1, _ = ids(conn)
        item = one(conn, "SELECT item_id FROM listening_activities WHERE id=?", a1)
        conn.execute(ATT + f"({user}, {new_session(conn, user)}, {a1}, {o1}, 0, 1, '2026-01-01 00:00:05')")
        row = conn.execute("SELECT source, kind, item_id, difficulty, is_correct, unit_id, task_id FROM learner_attempts").fetchone()
        assert tuple(row) == ("listening", "listening", item, 1, 0, a1, a1)
        topic = conn.execute("SELECT t.slug, v.is_correct FROM learner_attempt_topics v JOIN topics t ON t.id=v.topic_id").fetchone()
        assert tuple(topic) == ("greetings", 0)
