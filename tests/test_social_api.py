"""Friends and the friends leaderboard: the request lifecycle, ownership, no discovery, age-group restrictions (children have no
social features, enforced by the server), privacy and leaderboard integrity."""
import json
import sqlite3

import pytest

from backend.gamification import rules
from backend.social import service as social_service

from .agekids import freeze_clock, make_learner, profile
from .conftest import PASSWORD, register
from .gam import db, listen_right, seed_event, summary, uid
from .par import all_keys, browser


@pytest.fixture(autouse=True)
def _throttle():
    social_service.reset_throttle()
    yield
    social_service.reset_throttle()


def my_code(c):
    r = c.get("/api/social/friends")
    assert r.status_code == 200, r.text
    return r.json()["my_friend_code"]


def request_friend(c, other):
    return c.post("/api/social/friends/requests", json={"code": my_code(other)})


def befriend(a, b):
    r = request_friend(a, b)
    assert r.status_code == 201, r.text
    rid = b.get("/api/social/friends").json()["incoming"][0]["id"]
    assert b.post(f"/api/social/friends/requests/{rid}/accept").status_code == 200
    return a.get("/api/social/friends").json()["friends"][0]["id"]


@pytest.fixture
def pair(client, client2):
    return make_learner(client, "a@example.com", 14), make_learner(client2, "b@example.com", 15)


SOCIAL = [("get", "/api/social/friends", None), ("post", "/api/social/friend-code", None), ("post", "/api/social/friends/requests", {"code": "ABCDEFGHJK"}),
          ("post", "/api/social/friends/requests/1/accept", None), ("post", "/api/social/friends/requests/1/reject", None), ("delete", "/api/social/friends/1", None),
          ("get", "/api/social/leaderboard", None)]


def call(c, method, path, body=None):
    return getattr(c, method)(path, **({"json": body} if body is not None else {}))


# ---------- access ----------
@pytest.mark.parametrize("method,path,body", SOCIAL)
def test_unauthenticated_rejected(client, lockdown, method, path, body):
    assert call(client, method, path, body).status_code == 401


@pytest.mark.parametrize("method,path,body", SOCIAL)
def test_parents_and_admins_rejected(client, client2, make_admin, method, path, body):
    register(client, "p@example.com", role="parent")
    assert call(client, method, path, body).status_code == 403
    make_admin()
    client2.post("/api/auth/login", json={"email": "admin@example.com", "password": PASSWORD})
    assert call(client2, method, path, body).status_code == 403


@pytest.mark.parametrize("method,path,body", SOCIAL)
def test_a_profile_is_needed(client, method, path, body):
    register(client, "np@example.com")
    assert call(client, method, path, body).status_code == 409


# ---------- children have no social features (enforced by the server) ----------
@pytest.mark.parametrize("age", [5, 9])
@pytest.mark.parametrize("method,path,body", SOCIAL)
def test_children_are_refused_everywhere(client, age, method, path, body):
    make_learner(client, "kid@example.com", age)
    assert call(client, method, path, body).status_code == 403
    with db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM friend_requests").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM friendships").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM learner_gamification WHERE friend_code IS NOT NULL").fetchone()[0] == 0     # a child never gets a code


def test_a_child_cannot_be_reached_even_with_an_old_code(client, client2):
    adult = make_learner(client, "grown@example.com", 30)
    code = my_code(adult)
    kid = client2
    make_learner(kid, "kid@example.com", 14)
    assert adult.put("/api/profile", json=profile(8)).status_code == 200            # the first learner is now a child
    r = kid.post("/api/social/friends/requests", json={"code": code})
    assert r.status_code == 404                                                      # indistinguishable from an unknown code
    with db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM friend_requests").fetchone()[0] == 0


def test_a_learner_who_becomes_a_child_loses_social_access(pair):
    a, b = pair
    befriend(a, b)
    assert a.put("/api/profile", json=profile(8)).status_code == 200
    assert a.get("/api/social/friends").status_code == 403 and a.get("/api/social/leaderboard").status_code == 403
    assert b.get("/api/social/friends").json()["friends"] == []                     # and is no longer listed to others


def test_teens_and_adults_cannot_befriend_each_other(client, client2):
    teen, adult = make_learner(client, "t@example.com", 14), make_learner(client2, "a@example.com", 30)
    assert teen.post("/api/social/friends/requests", json={"code": my_code(adult)}).status_code == 404
    assert adult.post("/api/social/friends/requests", json={"code": my_code(teen)}).status_code == 404


def test_friends_who_change_age_group_are_hidden(pair):
    a, b = pair
    befriend(a, b)
    assert len(a.get("/api/social/friends").json()["friends"]) == 1
    assert b.put("/api/profile", json=profile(30)).status_code == 200
    assert a.get("/api/social/friends").json()["friends"] == []
    assert [e["display_name"] for e in a.get("/api/social/leaderboard").json()["entries"]] == ["Test User"]
    assert len(a.get("/api/social/leaderboard").json()["entries"]) == 1


def test_adults_can_be_friends_with_adults(client, client2):
    a, b = make_learner(client, "a@example.com", 25), make_learner(client2, "b@example.com", 40)
    befriend(a, b)


# ---------- the request lifecycle ----------
def test_send_accept_and_both_sides_see_each_other(pair):
    a, b = pair
    r = request_friend(a, b)
    assert r.status_code == 201 and set(r.json()["request"]) == {"id", "display_name", "created_at"}
    assert [x["display_name"] for x in b.get("/api/social/friends").json()["incoming"]] == ["Test User"]
    assert len(a.get("/api/social/friends").json()["outgoing"]) == 1
    rid = b.get("/api/social/friends").json()["incoming"][0]["id"]
    assert b.post(f"/api/social/friends/requests/{rid}/accept").json() == {"status": "accepted"}
    for c in (a, b):
        f = c.get("/api/social/friends").json()
        assert len(f["friends"]) == 1 and f["incoming"] == [] and f["outgoing"] == []
        assert set(f["friends"][0]) == {"id", "since", "display_name", "level", "rank", "xp"}


def test_reject(pair):
    a, b = pair
    request_friend(a, b)
    rid = b.get("/api/social/friends").json()["incoming"][0]["id"]
    assert b.post(f"/api/social/friends/requests/{rid}/reject").json() == {"status": "rejected"}
    assert a.get("/api/social/friends").json()["friends"] == [] and a.get("/api/social/friends").json()["outgoing"] == []
    assert b.post(f"/api/social/friends/requests/{rid}/accept").status_code == 409


def test_a_request_can_be_answered_once(pair):
    a, b = pair
    request_friend(a, b)
    rid = b.get("/api/social/friends").json()["incoming"][0]["id"]
    assert b.post(f"/api/social/friends/requests/{rid}/accept").status_code == 200
    assert b.post(f"/api/social/friends/requests/{rid}/accept").status_code == 409
    assert b.post(f"/api/social/friends/requests/{rid}/reject").status_code == 409
    with db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM friendships").fetchone()[0] == 1


def test_duplicate_requests_are_refused_in_either_direction(pair):
    a, b = pair
    assert request_friend(a, b).status_code == 201
    assert request_friend(a, b).status_code == 409
    assert request_friend(b, a).status_code == 409                                  # the other way round is the same pair
    with db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM friend_requests").fetchone()[0] == 1


def test_cannot_request_an_existing_friend(pair):
    a, b = pair
    befriend(a, b)
    assert request_friend(a, b).status_code == 409 and request_friend(b, a).status_code == 409


def test_self_friendship_is_refused(pair):
    a, _ = pair
    assert a.post("/api/social/friends/requests", json={"code": my_code(a)}).status_code == 404
    with db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM friend_requests").fetchone()[0] == 0
        me = uid("a@example.com")
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO friend_requests(requester_id, addressee_id, created_at) VALUES (?, ?, 't')", (me, me))
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO friendships(user_low, user_high, created_at) VALUES (?, ?, 't')", (me, me))


def test_only_the_addressee_can_answer(client, client2, pair):
    a, b = pair
    c = browser()
    make_learner(c, "c@example.com", 14)
    request_friend(a, b)
    rid = b.get("/api/social/friends").json()["incoming"][0]["id"]
    for who in (a, c):                                                              # the sender and a stranger
        assert who.post(f"/api/social/friends/requests/{rid}/accept").status_code == 404
        assert who.post(f"/api/social/friends/requests/{rid}/reject").status_code == 404
    assert a.get("/api/social/friends").json()["friends"] == []
    assert b.post("/api/social/friends/requests/99999/accept").status_code == 404
    assert b.post(f"/api/social/friends/requests/{rid}/accept").status_code == 200


def test_rejecting_blocks_nagging_for_a_while(pair, monkeypatch):
    tick = freeze_clock(monkeypatch)
    a, b = pair
    request_friend(a, b)
    rid = b.get("/api/social/friends").json()["incoming"][0]["id"]
    b.post(f"/api/social/friends/requests/{rid}/reject")
    assert request_friend(a, b).status_code == 409
    tick(86400 * rules.REJECT_COOLDOWN_DAYS + 1)
    assert request_friend(a, b).status_code == 201
    assert request_friend(b, a).status_code == 409                                  # theirs now waits on mine (same pair)


def test_remove_friend(pair):
    a, b = pair
    fid = befriend(a, b)
    assert a.delete(f"/api/social/friends/{fid}").json() == {"ok": True}
    for c in (a, b):
        assert c.get("/api/social/friends").json()["friends"] == []
    assert a.delete(f"/api/social/friends/{fid}").status_code == 404
    assert request_friend(b, a).status_code == 201                                   # they can become friends again


def test_either_friend_can_remove(pair):
    a, b = pair
    befriend(a, b)
    fid = b.get("/api/social/friends").json()["friends"][0]["id"]
    assert b.delete(f"/api/social/friends/{fid}").status_code == 200
    assert a.get("/api/social/friends").json()["friends"] == []


def test_a_stranger_cannot_remove_someone_elses_friendship(client, client2, pair):
    a, b = pair
    fid = befriend(a, b)
    c = browser()
    make_learner(c, "c@example.com", 14)
    assert c.delete(f"/api/social/friends/{fid}").status_code == 404
    assert len(a.get("/api/social/friends").json()["friends"]) == 1


def test_limits(pair, monkeypatch):
    a, b = pair
    monkeypatch.setattr(rules, "MAX_PENDING_OUTGOING", 1)
    c = browser()
    make_learner(c, "c@example.com", 14)
    assert request_friend(a, b).status_code == 201
    assert request_friend(a, c).status_code == 409
    monkeypatch.setattr(rules, "MAX_FRIENDS", 1)
    rid = b.get("/api/social/friends").json()["incoming"][0]["id"]
    b.post(f"/api/social/friends/requests/{rid}/accept")
    assert request_friend(c, a).status_code == 409                                   # a's list is full


# ---------- codes: no discovery ----------
@pytest.mark.parametrize("body", [{}, {"code": ""}, {"code": "abc"}, {"code": "x" * 41}, {"code": 5}, {"code": "ABCDEFGHJK", "user_id": 1}, {"code": "ABCDEFGHJK", "email": "a@b.c"}])
def test_request_body_is_validated(pair, body):
    assert pair[0].post("/api/social/friends/requests", json=body).status_code == 422


def test_there_is_no_way_to_find_learners(pair):
    a, b = pair
    for path in ("/api/social/search", "/api/social/users", "/api/social/learners", "/api/social/friends/search", f"/api/social/users/{uid('b@example.com')}"):
        assert a.get(path).status_code in (404, 405)
    assert a.get("/api/social/friends").json()["friends"] == []


def test_wrong_codes_look_alike_and_are_throttled(pair):
    a, b = pair
    for _ in range(rules.CODE_MAX_FAILURES):
        assert a.post("/api/social/friends/requests", json={"code": "WRONGCODE1"}).status_code == 404
    blocked = a.post("/api/social/friends/requests", json={"code": my_code(b)})
    assert blocked.status_code == 429 and int(blocked.headers["Retry-After"]) > 0
    assert b.post("/api/social/friends/requests", json={"code": my_code(a)}).status_code == 201


def test_codes_are_case_and_space_insensitive_and_can_be_replaced(pair):
    a, b = pair
    old = my_code(b)
    new = b.post("/api/social/friend-code").json()["code"]
    assert new != old and len(new) == rules.FRIEND_CODE_LENGTH and my_code(b) == new
    assert a.post("/api/social/friends/requests", json={"code": old}).status_code == 404
    assert a.post("/api/social/friends/requests", json={"code": new[:5].lower() + " " + new[5:].lower()}).status_code == 201


def test_codes_are_unique(client, client2):
    codes = set()
    for i in range(6):
        c = browser()
        make_learner(c, f"u{i}@example.com", 14)
        codes.add(my_code(c))
    assert len(codes) == 6


# ---------- privacy ----------
def test_no_private_data_or_internal_ids_are_shared(pair):
    a, b = pair
    befriend(a, b)
    listen_right(b, 2)
    blob = json.dumps([a.get("/api/social/friends").json(), a.get("/api/social/leaderboard").json(), b.get("/api/social/friends").json()])
    for needle in ("a@example.com", "b@example.com", "date_of_birth", "password", "handle", "u_"):
        assert needle not in blob
    assert not ({"email", "date_of_birth", "handle", "user_id", "requester_id", "addressee_id", "friend_id", "learner_id", "password_hash"} & all_keys(json.loads(blob)))


def test_a_stranger_sees_nothing_of_a_friendship(pair):
    a, b = pair
    befriend(a, b)
    c = browser()
    make_learner(c, "c@example.com", 14)
    f = c.get("/api/social/friends").json()
    assert f["friends"] == f["incoming"] == f["outgoing"] == []
    assert len(c.get("/api/social/leaderboard").json()["entries"]) == 1


# ---------- the leaderboard ----------
def give(user_email, xp, day="2026-09-01", source=1):
    seed_event(uid(user_email), "challenge", source, xp, day)


def board(c, period="all"):
    r = c.get(f"/api/social/leaderboard?period={period}")
    assert r.status_code == 200, r.text
    return r.json()["entries"]


def named(client, name, email, age=14):
    c = browser() if client is None else client
    register(c, email, name=name)
    assert c.put("/api/profile", json=profile(age)).status_code == 200
    return c


def test_ranking_is_by_xp_with_deterministic_ties(client):
    me = named(client, "Maya", "maya@example.com")
    others = {n: named(None, n, f"{n}@example.com") for n in ("Zed", "Amy", "Bo")}
    for o in others.values():
        befriend(me, o)
    for who, xp in (("maya@example.com", 50), ("Zed@example.com", 80), ("Amy@example.com", 50), ("Bo@example.com", 20)):
        summary(me)
        give(who, xp, source=uid(who))
    entries = board(me)
    assert [(e["display_name"], e["xp"], e["rank"]) for e in entries] == [("Zed", 80, 1), ("Amy", 50, 2), ("Maya", 50, 2), ("Bo", 20, 4)]
    assert [e["is_me"] for e in entries] == [False, False, True, False]
    assert board(me) == entries                                                     # stable


def test_entries_show_only_name_xp_and_level(pair):
    a, b = pair
    befriend(a, b)
    for e in board(a):
        assert set(e) == {"display_name", "xp", "level", "rank_name", "is_me", "rank"}


def test_only_friends_are_ranked(client, client2, pair):
    a, b = pair
    c = browser()
    make_learner(c, "c@example.com", 14)
    give("c@example.com", 99, source=7)
    befriend(a, b)
    assert len(board(a)) == 2 and all(e["xp"] == 0 for e in board(a))


def test_the_period_filters_by_day(pair, monkeypatch):
    freeze_clock(monkeypatch)                                                       # Tuesday 2026-09-01
    a, b = pair
    befriend(a, b)
    give("a@example.com", 30, day="2026-08-20", source=1)                           # an earlier week
    give("a@example.com", 10, day="2026-09-01", source=2)
    assert [e["xp"] for e in board(a, "week") if e["is_me"]] == [10]
    assert [e["xp"] for e in board(a, "all") if e["is_me"]] == [40]
    give("a@example.com", 5, day="2026-08-31", source=3)                            # Monday: still this week
    assert [e["xp"] for e in board(a, "week") if e["is_me"]] == [15]


def test_bad_period_is_rejected(pair):
    assert pair[0].get("/api/social/leaderboard?period=forever").status_code == 422


def test_scores_cannot_be_submitted(pair):
    a, b = pair
    befriend(a, b)
    for method in ("post", "put", "patch"):
        assert getattr(a, method)("/api/social/leaderboard", json={"xp": 9999}).status_code in (404, 405)
    assert a.delete("/api/social/leaderboard").status_code in (404, 405)
    r = a.get("/api/social/leaderboard?period=all&xp=9999&user=me")
    assert r.status_code == 200 and all(e["xp"] == 0 for e in r.json()["entries"])


def test_leaderboard_xp_comes_from_real_activity_and_updates_for_friends(pair):
    a, b = pair
    befriend(a, b)
    listen_right(b, 3)                                                              # b does something; a looks
    assert sorted(e["xp"] for e in board(a)) == [0, 15]


def test_unfriending_removes_them_from_the_board(pair):
    a, b = pair
    fid = befriend(a, b)
    a.delete(f"/api/social/friends/{fid}")
    assert len(board(a)) == 1 and len(board(b)) == 1


def test_the_board_reflects_friends_challenge_rewards_too(pair):
    a, b = pair
    befriend(a, b)
    give("b@example.com", 40, source=5)
    assert sorted(e["xp"] for e in board(a)) == [0, 40]


# ---------- schema ----------
def test_friend_tables_constraints(db_path):
    from backend.db import connect
    with connect(db_path) as conn:
        def user(n):
            return conn.execute("INSERT INTO users(handle, display_name) VALUES (?, ?)", (f"h{n}", f"U{n}")).lastrowid
        a, b, c = user(1), user(2), user(3)
        conn.execute("INSERT INTO friend_requests(requester_id, addressee_id, created_at) VALUES (?, ?, 't')", (a, b))
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO friend_requests(requester_id, addressee_id, created_at) VALUES (?, ?, 't')", (a, b))
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO friend_requests(requester_id, addressee_id, created_at) VALUES (?, ?, 't')", (b, a))     # reverse pair
        conn.execute("INSERT INTO friend_requests(requester_id, addressee_id, created_at) VALUES (?, ?, 't')", (a, c))
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO friend_requests(requester_id, addressee_id, status, created_at) VALUES (?, ?, 'accepted', 't')", (c, b))   # needs responded_at
        conn.execute("UPDATE friend_requests SET status = 'rejected', responded_at = 't' WHERE requester_id = ? AND addressee_id = ?", (a, b))
        conn.execute("INSERT INTO friend_requests(requester_id, addressee_id, created_at) VALUES (?, ?, 't2')", (b, a))             # a rejected pair may ask again
        conn.execute("INSERT INTO friendships(user_low, user_high, created_at) VALUES (?, ?, 't')", (a, b))
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO friendships(user_low, user_high, created_at) VALUES (?, ?, 't')", (a, b))
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO friendships(user_low, user_high, created_at) VALUES (?, ?, 't')", (b, a))                     # must be (low, high)
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO friendships(user_low, user_high, created_at) VALUES (?, 9999, 't')", (a,))
        conn.execute("DELETE FROM users WHERE id = ?", (a,))
        assert conn.execute("SELECT COUNT(*) FROM friendships").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM friend_requests").fetchone()[0] == 0
