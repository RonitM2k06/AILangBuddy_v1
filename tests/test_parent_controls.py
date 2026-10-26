"""Parental controls: safe defaults, validation, ownership, server-side enforcement, and the child-voice boundary."""
import sqlite3

import pytest

from backend.parent import service as parent_service

from .agekids import answer_key, play
from .par import browser, code_for, db, link, make_child, make_parent, uid
from .spk import audio, create, prompt_items, transcribe, upload


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("STT_PROVIDER", "mock")
    monkeypatch.setenv("PRONUNCIATION_PROVIDER", "mock")
    parent_service.reset_throttle()


def controls(parent, i):
    return parent.get(f"/api/parent/children/{i}/controls").json()["controls"]


def put(parent, i, body):
    return parent.put(f"/api/parent/children/{i}/controls", json=body)


def family(client, age=14, email="kid@example.com", pemail="p@example.com"):
    child = make_child(client, email, age)
    parent = browser()
    make_parent(parent, pemail)
    return parent, child, link(parent, child)


# ---------- defaults ----------
def test_safe_defaults_for_a_teen(client):
    parent, child, i = family(client, 14)
    assert controls(parent, i) == {"voice_disabled": False, "updated_at": None, "voice_available_to_child": True, "voice_unavailable_reason": None}
    with db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM parent_controls").fetchone()[0] == 0          # no row = no extra restriction
    assert child.post("/api/speaking/sessions", json={}).status_code == 201                      # linking changed nothing for the child


def test_child_voice_is_off_by_default_and_the_parent_is_told_why(client):
    parent, child, i = family(client, 7)
    c = controls(parent, i)
    assert c["voice_disabled"] is False                                  # the parent has not restricted anything...
    assert c["voice_available_to_child"] is False and c["voice_unavailable_reason"] == "age_group"   # ...the product keeps it off
    assert child.post("/api/speaking/sessions", json={}).status_code == 403


# ---------- the boundary: nothing switches child voice on ----------
@pytest.mark.parametrize("value", [True, False])
def test_no_control_value_enables_child_voice(client, value):
    parent, child, i = family(client, 7)
    assert put(parent, i, {"voice_disabled": value}).status_code == 200
    assert child.post("/api/speaking/sessions", json={}).status_code == 403
    c = controls(parent, i)
    assert c["voice_available_to_child"] is False and c["voice_unavailable_reason"] == "age_group"
    with db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM speaking_sessions").fetchone()[0] == 0


def test_a_child_cannot_change_their_own_controls(client):
    parent, child, i = family(client, 7)
    for method, path, body in (("get", f"/api/parent/children/{i}/controls", None), ("put", f"/api/parent/children/{i}/controls", {"voice_disabled": False}),
                               ("post", "/api/parent/children", {"code": "ABCDEFGHJK"})):
        r = getattr(child, method)(path, **({"json": body} if body else {}))
        assert r.status_code == 403
    assert controls(parent, i)["voice_disabled"] is False


def test_a_child_who_grows_up_gets_voice_unless_a_parent_switched_it_off(client):
    parent, child, i = family(client, 7)
    from .agekids import dob_for_age, profile
    assert child.put("/api/profile", json=profile(30)).status_code == 409      # Phase 14A: a linked child cannot edit their way out of the child group...
    with db() as conn:                                                          # ...but really growing up (time passing) still works
        conn.execute("UPDATE learner_profiles SET date_of_birth = ? WHERE user_id = ?", (dob_for_age(30), uid("kid@example.com")))
    assert controls(parent, i)["voice_available_to_child"] is True
    assert put(parent, i, {"voice_disabled": True}).status_code == 200
    assert child.post("/api/speaking/sessions", json={}).status_code == 403


def test_no_biometric_or_new_voice_data_is_created_for_a_child(client):
    parent, child, i = family(client, 7)
    put(parent, i, {"voice_disabled": False})
    child.post("/api/speaking/sessions", json={})
    with db() as conn:
        for t in ("audio_sessions", "speaking_sessions", "stt_runs", "speaking_transcripts", "pronunciation_assessments"):
            assert conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] == 0


# ---------- enforcement ----------
def test_voice_off_blocks_every_speaking_step(client):
    parent, child, i = family(client, 14)
    s = create(child)                                                   # created while allowed
    assert put(parent, i, {"voice_disabled": True}).status_code == 200
    assert child.post("/api/speaking/sessions", json={}).status_code == 403
    assert upload(child, s["id"], audio("x")).status_code == 403
    assert transcribe(child, s["id"]).status_code == 403
    with db() as conn:
        assert conn.execute("SELECT stage FROM speaking_sessions").fetchone()[0] == "created"   # nothing was recorded or transcribed
        assert conn.execute("SELECT COUNT(*) FROM stt_runs").fetchone()[0] == 0


def test_voice_off_blocks_new_pronunciation_analysis_but_not_reading_results(client):
    parent, child, i = family(client, 14)
    from .spk import transcribed
    done = transcribed(child, "नमस्ते, आप कैसे हैं?", pron={"overall": 80}, item_id=prompt_items(child)[0]["item"]["id"])
    second = transcribed(child, "नमस्ते", item_id=prompt_items(child)[0]["item"]["id"])
    assert child.post(f"/api/speaking/sessions/{done['id']}/assess-pronunciation").status_code == 200
    put(parent, i, {"voice_disabled": True})
    assert child.post(f"/api/speaking/sessions/{second['id']}/assess-pronunciation").status_code == 403    # new analysis refused
    assert child.post(f"/api/speaking/sessions/{done['id']}/assess-pronunciation").status_code == 200     # an existing result is just read
    assert child.get(f"/api/speaking/sessions/{done['id']}/pronunciation").status_code == 200
    assert child.get("/api/speaking/sessions").status_code == 200 and child.get("/api/speaking/progress").status_code == 200


def test_switching_voice_back_on_restores_it(client):
    parent, child, i = family(client, 14)
    put(parent, i, {"voice_disabled": True})
    assert child.post("/api/speaking/sessions", json={}).status_code == 403
    r = put(parent, i, {"voice_disabled": False})
    assert r.status_code == 200 and r.json()["controls"]["voice_available_to_child"] is True
    assert child.post("/api/speaking/sessions", json={}).status_code == 201


def test_controls_do_not_affect_other_learning(client):
    parent, child, i = family(client, 14)
    put(parent, i, {"voice_disabled": True})
    for path in ("/api/lessons", "/api/listening", "/api/situations", "/api/recommendations", "/api/daily-plan", "/api/experience"):
        assert child.get(path).status_code == 200


def test_the_controls_view_never_shows_a_parent_enabled_child_voice(client):
    parent, child, i = family(client, 7)
    put(parent, i, {"voice_disabled": True})
    assert controls(parent, i)["voice_unavailable_reason"] == "age_group"          # the product reason wins over the parent's


def test_control_applies_only_to_the_linked_learner(client, client2):
    parent, child, i = family(client, 14)
    other = make_child(client2, "other@example.com", 14)
    put(parent, i, {"voice_disabled": True})
    assert child.post("/api/speaking/sessions", json={}).status_code == 403
    assert other.post("/api/speaking/sessions", json={}).status_code == 201


def test_the_strictest_of_several_parents_applies(client):
    parent, child, i = family(client, 14)
    second = browser(); make_parent(second, "p2@example.com")
    j = link(second, child)
    put(parent, i, {"voice_disabled": True})
    assert controls(second, j)["voice_disabled"] is False                          # each parent sees their own switch...
    assert controls(second, j)["voice_available_to_child"] is False                # ...and the real effect
    assert child.post("/api/speaking/sessions", json={}).status_code == 403
    put(second, j, {"voice_disabled": False})                                      # the second parent cannot lift the first one's
    assert child.post("/api/speaking/sessions", json={}).status_code == 403
    put(parent, i, {"voice_disabled": False})
    assert child.post("/api/speaking/sessions", json={}).status_code == 201


def test_unlinking_removes_that_parents_restriction(client):
    parent, child, i = family(client, 14)
    put(parent, i, {"voice_disabled": True})
    parent.delete(f"/api/parent/children/{i}")
    assert child.post("/api/speaking/sessions", json={}).status_code == 201
    with db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM parent_controls").fetchone()[0] == 0


# ---------- validation and ownership ----------
@pytest.mark.parametrize("body", [{}, {"voice_disabled": "yes"}, {"voice_disabled": 1}, {"voice_disabled": 0}, {"voice_disabled": "true"}, {"voice_disabled": None},
                                  {"voice_disabled": [True]}, {"voice_disabled": True, "extra": 1}, {"voice_disabled": True, "voice_enabled": True},
                                  {"voice_disabled": True, "child_voice": True}, {"voice": True}])
def test_invalid_control_bodies_change_nothing(client, body):
    parent, child, i = family(client, 14)
    assert put(parent, i, body).status_code == 422
    assert controls(parent, i)["voice_disabled"] is False
    with db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM parent_controls").fetchone()[0] == 0


def test_control_is_idempotent_and_records_when(client):
    parent, child, i = family(client, 14)
    a = put(parent, i, {"voice_disabled": True}).json()["controls"]
    b = put(parent, i, {"voice_disabled": True}).json()["controls"]
    assert a["voice_disabled"] is b["voice_disabled"] is True and a["updated_at"]
    with db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM parent_controls").fetchone()[0] == 1


def test_only_the_linked_parent_can_read_or_change_controls(client, client2):
    parent, child, i = family(client, 14)
    stranger = browser(); make_parent(stranger, "s@example.com")
    assert stranger.get(f"/api/parent/children/{i}/controls").status_code == 404
    assert put(stranger, i, {"voice_disabled": True}).status_code == 404
    assert controls(parent, i)["voice_disabled"] is False
    assert child.post("/api/speaking/sessions", json={}).status_code == 201


def test_unknown_link_id_is_404(client):
    parent, child, i = family(client, 14)
    assert put(parent, i + 100, {"voice_disabled": True}).status_code == 404
    assert parent.get("/api/parent/children/abc/controls").status_code == 422


# ---------- schema ----------
def user(conn, email, *roles):
    uid_ = conn.execute("INSERT INTO users(handle, display_name, email, password_hash) VALUES (?, 'U', ?, 'x')", ("h" + email, email)).lastrowid
    for r in roles:
        conn.execute("INSERT INTO user_roles SELECT ?, id FROM roles WHERE name = ?", (uid_, r))
    return uid_


def test_role_ids_match_the_names(db_path):
    from backend.db import connect
    with connect(db_path) as conn:
        assert dict(conn.execute("SELECT name, id FROM roles").fetchall()) == {"learner": 1, "parent": 2, "admin": 3}


def test_the_database_refuses_bad_links(db_path):
    from backend.db import connect
    with connect(db_path) as conn:
        parent, child, other_parent, admin = user(conn, "p@x", "parent"), user(conn, "c@x", "learner"), user(conn, "p2@x", "parent"), user(conn, "a@x", "admin")
        both = user(conn, "b@x", "parent", "learner")
        conn.execute("INSERT INTO parent_links(parent_id, learner_id, created_at) VALUES (?, ?, 't')", (parent, child))
        for p, c in ((parent, child), (child, parent), (admin, child), (parent, admin), (parent, parent), (both, both), (parent, 9999), (9999, child), (child, child)):
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute("INSERT INTO parent_links(parent_id, learner_id, created_at) VALUES (?, ?, 't')", (p, c))
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO parent_links(parent_id, learner_id, parent_role_id, created_at) VALUES (?, ?, 3, 't')", (other_parent, child))
        conn.execute("INSERT INTO parent_links(parent_id, learner_id, created_at) VALUES (?, ?, 't')", (other_parent, child))     # a second parent is fine
        conn.execute("INSERT INTO parent_links(parent_id, learner_id, created_at) VALUES (?, ?, 't')", (both, child))             # dual-role parent ok


def test_control_and_code_constraints(db_path):
    from backend.db import connect
    with connect(db_path) as conn:
        parent, child, stranger = user(conn, "p@x", "parent"), user(conn, "c@x", "learner"), user(conn, "s@x", "parent")
        link_id = conn.execute("INSERT INTO parent_links(parent_id, learner_id, created_at) VALUES (?, ?, 't')", (parent, child)).lastrowid
        for bad in (2, -1, 5):
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute("INSERT INTO parent_controls(link_id, voice_disabled, updated_at) VALUES (?, ?, 't')", (link_id, bad))
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO parent_controls(link_id, voice_disabled, updated_at) VALUES (999, 1, 't')")
        conn.execute("INSERT INTO parent_controls(link_id, voice_disabled, updated_at) VALUES (?, 1, 't')", (link_id,))
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO parent_controls(link_id, voice_disabled, updated_at) VALUES (?, 0, 't')", (link_id,))
        # codes: only a learner can have one; expiry after creation; used_at and used_by together; hash unique
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO parent_link_codes(learner_id, code_hash, created_at, expires_at) VALUES (?, 'h', 'a', 'b')", (parent,))
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO parent_link_codes(learner_id, code_hash, created_at, expires_at) VALUES (?, 'h', 'b', 'a')", (child,))
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO parent_link_codes(learner_id, code_hash, created_at, expires_at, used_at) VALUES (?, 'h', 'a', 'b', 'a')", (child,))
        conn.execute("INSERT INTO parent_link_codes(learner_id, code_hash, created_at, expires_at) VALUES (?, 'h', 'a', 'b')", (child,))
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO parent_link_codes(learner_id, code_hash, created_at, expires_at) VALUES (?, 'h', 'a', 'b')", (child,))


def test_deleting_a_user_or_link_cleans_up(db_path):
    from backend.db import connect
    with connect(db_path) as conn:
        parent, child = user(conn, "p@x", "parent"), user(conn, "c@x", "learner")
        link_id = conn.execute("INSERT INTO parent_links(parent_id, learner_id, created_at) VALUES (?, ?, 't')", (parent, child)).lastrowid
        conn.execute("INSERT INTO parent_controls VALUES (?, 1, 't')", (link_id,))
        conn.execute("DELETE FROM users WHERE id = ?", (parent,))
        assert conn.execute("SELECT COUNT(*) FROM parent_links").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM parent_controls").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM users WHERE id = ?", (child,)).fetchone()[0] == 1


def test_removing_a_role_removes_the_relationship(db_path):
    from backend.db import connect
    with connect(db_path) as conn:
        parent, child = user(conn, "p@x", "parent"), user(conn, "c@x", "learner")
        conn.execute("INSERT INTO parent_links(parent_id, learner_id, created_at) VALUES (?, ?, 't')", (parent, child))
        conn.execute("DELETE FROM user_roles WHERE user_id = ? AND role_id = 2", (parent,))
        assert conn.execute("SELECT COUNT(*) FROM parent_links").fetchone()[0] == 0


# ---------- Phase 8 still works for a linked child ----------
def test_kids_adventure_still_works_for_a_linked_child(client):
    parent, child, i = family(client, 7)
    key = answer_key()
    q, right, wrong = key[1][0]
    assert play(child, 1, q, wrong).json()["lives"]["current"] == 4
    overview = parent.get(f"/api/parent/children/{i}/overview").json()
    assert overview["listening"]["attempts"] == 1
    assert overview["weaknesses_count"] == 0
    assert child.get("/api/kids/adventure").json()["lives"]["current"] == 4
