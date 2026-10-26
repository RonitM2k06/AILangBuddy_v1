"""Phase 14C: sessions (rotation, listing, revocation, logout-all, idle and absolute expiry), password change, and the layered
authentication throttles. Time is a controlled clock; client addresses are set per browser. Every refusal is checked for its effect."""
import hashlib
import re
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from backend import main, settings
from backend.auth import passwords, service, throttle
from backend.db import connect

from .conftest import FRONTEND_HEADERS, PASSWORD, register

NEW_PASSWORD = "a brand new passphrase"


@pytest.fixture
def clock(monkeypatch):
    now = [service.utcnow().replace(microsecond=0)]
    monkeypatch.setattr(service, "utcnow", lambda: now[0])
    return now


def advance(clock, **delta):
    clock[0] += timedelta(**delta)


def browser(ip="203.0.113.10"):
    return TestClient(main.app, headers=dict(FRONTEND_HEADERS), client=(ip, 50000))


def db():
    return connect(main.DB_PATH)


def session_rows(email=None):
    with db() as conn:
        sql = "SELECT s.* FROM sessions s JOIN users u ON u.id = s.user_id" + (" WHERE u.email = ?" if email else "")
        return [dict(r) for r in conn.execute(sql, (email,) if email else ())]


def login(c, email, password=PASSWORD):
    return c.post("/api/auth/login", json={"email": email, "password": password})


def signed_in(email="a@example.com", ip="203.0.113.10", role="learner"):
    c = browser(ip)
    register(c, email, role=role)
    return c


def second_browser(email, ip="203.0.113.11", password=PASSWORD):
    c = browser(ip)
    assert login(c, email, password).status_code == 200
    return c


def me(c):
    return c.get("/api/auth/me").status_code


def token(c):
    return c.cookies.get("llb_session")


def with_token(t):
    c = browser("203.0.113.99")
    c.cookies.set("llb_session", t)
    return c


# =====================================================================================================================
# session lifecycle
# =====================================================================================================================
def test_login_issues_a_fresh_session_and_revokes_the_one_this_browser_had(client):
    c = signed_in("a@example.com")
    register(browser(), "b@example.com")
    first = token(c)
    assert login(c, "b@example.com").status_code == 200                     # the same browser signs in as someone else
    assert token(c) != first and c.get("/api/auth/me").json()["user"]["email"] == "b@example.com"
    assert me(with_token(first)) == 401                                     # the session it had is gone, not merely forgotten
    assert len(session_rows("a@example.com")) == 0


def test_registering_also_revokes_the_session_this_browser_had(client):
    c = signed_in("a@example.com")
    first = token(c)
    register(c, "b@example.com")
    assert me(with_token(first)) == 401 and token(c) != first


def test_an_attacker_chosen_cookie_never_becomes_a_session(client):
    """Session fixation: a token planted in the victim's browser before sign-in is not adopted; sign-in issues its own."""
    register(browser(), "a@example.com")
    c = browser()
    c.cookies.set("llb_session", "attacker-chosen-token-value")
    r = login(c, "a@example.com")
    assert r.status_code == 200 and r.cookies.get("llb_session") not in (None, "attacker-chosen-token-value")
    assert me(with_token("attacker-chosen-token-value")) == 401 and me(with_token(r.cookies.get("llb_session"))) == 200


def test_several_sessions_may_coexist(client):
    a = signed_in("a@example.com")
    b = second_browser("a@example.com")
    assert me(a) == me(b) == 200 and len(session_rows("a@example.com")) == 2


def test_logout_ends_only_the_current_session(client):
    a = signed_in("a@example.com")
    b = second_browser("a@example.com")
    stale = token(a)
    assert a.post("/api/auth/logout").status_code == 200
    assert me(with_token(stale)) == 401 and me(b) == 200


def test_logout_all_signs_out_every_other_session_and_keeps_this_one(client):
    a = signed_in("a@example.com")
    others = [second_browser("a@example.com", ip=f"203.0.113.{20 + i}") for i in range(3)]
    stranger = signed_in("z@example.com", ip="198.51.100.5")
    r = a.post("/api/auth/logout-all")
    assert r.status_code == 200 and r.json() == {"ok": True, "revoked": 3}
    assert me(a) == 200 and all(me(o) == 401 for o in others)
    assert me(stranger) == 200                                              # nobody else's session is touched
    assert a.post("/api/auth/logout-all").json()["revoked"] == 0


def test_the_session_list_is_the_users_own_with_safe_fields_only(client):
    a = signed_in("a@example.com")
    b = second_browser("a@example.com")
    signed_in("z@example.com", ip="198.51.100.5")
    r = a.get("/api/auth/sessions")
    listed = r.json()["sessions"]
    assert r.status_code == 200 and len(listed) == 2
    assert all(set(s) == {"id", "created_at", "last_seen_at", "expires_at", "auth_method", "current"} for s in listed)
    assert all(re.fullmatch(r"[0-9a-f]{32}", s["id"]) for s in listed) and {s["auth_method"] for s in listed} == {"password"}
    assert [s["current"] for s in listed].count(True) == 1
    for raw in (token(a), token(b)):
        assert raw not in r.text and hashlib.sha256(raw.encode()).hexdigest() not in r.text
    with db() as conn:
        ids = {row[0] for row in conn.execute("SELECT public_id FROM sessions s JOIN users u ON u.id = s.user_id WHERE u.email = 'a@example.com'")}
        row_ids = {str(row[0]) for row in conn.execute("SELECT id FROM sessions")}
    assert {s["id"] for s in listed} == ids and not row_ids & {s["id"] for s in listed}
    assert current_id(a) != current_id(b) and {current_id(a), current_id(b)} == ids             # each browser sees its own as current


def current_id(c):
    return next(s["id"] for s in c.get("/api/auth/sessions").json()["sessions"] if s["current"])


def test_the_current_flag_follows_the_cookie_not_the_client(client):
    a = signed_in("a@example.com")
    b = second_browser("a@example.com")
    assert current_id(a) != current_id(b)
    r = a.get("/api/auth/sessions", params={"current": current_id(b)}, headers={"X-Session-Id": current_id(b)})
    assert next(s["id"] for s in r.json()["sessions"] if s["current"]) == current_id(a)


def test_revoking_another_of_my_sessions(client):
    a = signed_in("a@example.com")
    b = second_browser("a@example.com")
    r = a.delete(f"/api/auth/sessions/{current_id(b)}")
    assert r.status_code == 200 and r.json() == {"ok": True, "current": False}
    assert me(b) == 401 and me(a) == 200


def test_revoking_my_current_session_signs_me_out(client):
    a = signed_in("a@example.com")
    stale = token(a)
    r = a.delete(f"/api/auth/sessions/{current_id(a)}")
    assert r.status_code == 200 and r.json()["current"] is True and 'llb_session=""' in r.headers["set-cookie"]
    assert me(with_token(stale)) == 401


@pytest.mark.parametrize("make_id", [lambda other: other, lambda other: "0" * 32, lambda other: "f" * 32, lambda other: "not-a-session",
                                     lambda other: other.upper(), lambda other: "1"])
def test_a_session_that_is_not_mine_looks_exactly_like_one_that_does_not_exist(client, make_id):
    a = signed_in("a@example.com")
    victim = signed_in("v@example.com", ip="198.51.100.5")
    r = a.delete(f"/api/auth/sessions/{make_id(current_id(victim))}")
    assert r.status_code == 404 and r.json() == {"detail": "Not found"}
    assert me(victim) == 200 and me(a) == 200


def test_session_apis_need_a_session(client):
    c = browser()
    for method, path in (("get", "/api/auth/sessions"), ("post", "/api/auth/logout-all"), ("delete", "/api/auth/sessions/" + "a" * 32), ("post", "/api/auth/password")):
        r = getattr(c, method)(path, **({"json": {"current_password": PASSWORD, "new_password": NEW_PASSWORD}} if path.endswith("password") else {}))
        assert r.status_code == 401, (method, path)


# =====================================================================================================================
# idle timeout and absolute lifetime
# =====================================================================================================================
def test_an_active_session_keeps_working_past_the_idle_window(client, clock):
    a = signed_in("a@example.com")
    for _ in range(4):                                                      # 4 x 25 min = 100 min of use, never 30 idle
        advance(clock, minutes=25)
        assert me(a) == 200


@pytest.mark.parametrize("idle,ok", [(timedelta(minutes=30) - timedelta(seconds=1), True), (timedelta(minutes=30), False), (timedelta(hours=5), False)])
def test_the_idle_timeout_boundary(client, clock, idle, ok):
    a = signed_in("a@example.com")
    clock[0] += idle
    assert me(a) == (200 if ok else 401)
    assert len(session_rows("a@example.com")) == (1 if ok else 0)          # an idle-expired session is deleted when presented


def test_the_idle_timeout_is_configurable(client, clock, monkeypatch):
    monkeypatch.setenv("SESSION_IDLE_MINUTES", "5")
    a = signed_in("a@example.com")
    advance(clock, minutes=4)
    assert me(a) == 200
    advance(clock, minutes=5, seconds=30)
    assert me(a) == 401


def test_last_seen_is_written_at_most_once_a_minute(client, clock):
    a = signed_in("a@example.com")
    created = session_rows("a@example.com")[0]["last_seen_at"]
    advance(clock, seconds=30)
    me(a)
    assert session_rows("a@example.com")[0]["last_seen_at"] == created          # 30 s: no write
    advance(clock, seconds=30)
    me(a)
    moved = session_rows("a@example.com")[0]["last_seen_at"]
    assert moved == service._fmt(clock[0]) and moved > created                    # 60 s: one write, to the server's own time


def test_requests_that_do_not_authenticate_never_touch_last_seen(client, clock):
    a = signed_in("a@example.com")
    before = session_rows("a@example.com")[0]["last_seen_at"]
    advance(clock, minutes=5)
    a.get("/api/languages")                                                  # public: no session lookup
    with_token("garbage").get("/api/auth/me")
    assert session_rows("a@example.com")[0]["last_seen_at"] == before


def test_the_client_cannot_set_last_seen(client, clock):
    a = signed_in("a@example.com")
    advance(clock, minutes=20)
    a.get("/api/auth/me", params={"last_seen_at": "2099-01-01 00:00:00"}, headers={"X-Last-Seen": "2099-01-01 00:00:00"})
    a.post("/api/auth/logout-all", json={"last_seen_at": "2099-01-01 00:00:00"})
    assert session_rows("a@example.com")[0]["last_seen_at"] == service._fmt(clock[0])
    advance(clock, minutes=31)
    assert me(a) == 401


def test_activity_never_extends_the_absolute_lifetime(client, clock, monkeypatch):
    monkeypatch.setenv("SESSION_IDLE_MINUTES", str(24 * 60))
    a = signed_in("a@example.com")
    expires = session_rows("a@example.com")[0]["expires_at"]
    for _ in range(7):                                                      # used every 23 h: 161 h after sign-in, never idle
        advance(clock, hours=23)
        assert me(a) == 200
    assert session_rows("a@example.com")[0]["expires_at"] == expires
    advance(clock, hours=6, minutes=59, seconds=59)                          # 167 h 59 m 59 s: 1 s before the 7-day mark, still active
    assert me(a) == 200
    advance(clock, seconds=1)                                                # exactly 7 days, after only 7 h idle: the absolute lifetime ends it
    assert me(a) == 401 and len(session_rows("a@example.com")) == 0


def test_an_expired_session_cannot_be_revived(client, clock):
    a = signed_in("a@example.com")
    stale = token(a)
    advance(clock, minutes=45)
    assert me(a) == 401
    advance(clock, seconds=-45 * 60)                                         # even if the clock (or a replay) goes back
    assert me(with_token(stale)) == 401


def test_a_session_that_went_idle_is_not_listed_even_before_any_cleanup(client, clock):
    a = signed_in("a@example.com")
    b = second_browser("a@example.com")
    advance(clock, minutes=25)
    assert me(b) == 200                                                      # b stays active, a does not
    advance(clock, minutes=10)
    listed = b.get("/api/auth/sessions").json()["sessions"]
    assert len(listed) == 1 and listed[0]["current"] is True
    assert len(session_rows("a@example.com")) == 2                           # a's row is still there (nothing has presented it), just not live


def test_idle_and_expired_sessions_are_not_listed_and_are_cleaned_at_login(client, clock):
    a = signed_in("a@example.com")
    advance(clock, minutes=40)
    b = second_browser("a@example.com")
    assert len(b.get("/api/auth/sessions").json()["sessions"]) == 1 and len(session_rows("a@example.com")) == 1


# =====================================================================================================================
# password change
# =====================================================================================================================
def change(c, current=PASSWORD, new=NEW_PASSWORD, **extra):
    return c.post("/api/auth/password", json={"current_password": current, "new_password": new, **extra})


def test_a_wrong_current_password_changes_nothing(client):
    a = signed_in("a@example.com")
    b = second_browser("a@example.com")
    r = change(a, current="not my password")
    assert r.status_code == 403 and r.json() == {"detail": "The current password is not correct"}
    assert me(a) == me(b) == 200 and login(browser("198.51.100.1"), "a@example.com").status_code == 200


def test_changing_the_password_signs_out_everything_else_and_rotates_this_session(client):
    a = signed_in("a@example.com")
    others = [second_browser("a@example.com", ip=f"203.0.113.{30 + i}") for i in range(2)]
    stale = token(a)
    r = change(a)
    assert r.status_code == 200 and r.json() == {"ok": True}
    assert token(a) != stale and me(a) == 200 and me(with_token(stale)) == 401
    assert all(me(o) == 401 for o in others) and len(session_rows("a@example.com")) == 1
    assert login(browser("198.51.100.2"), "a@example.com").status_code == 401
    assert login(browser("198.51.100.3"), "a@example.com", NEW_PASSWORD).status_code == 200
    with db() as conn:
        stored = conn.execute("SELECT password_hash FROM users WHERE email = 'a@example.com'").fetchone()[0]
    assert stored.startswith("scrypt$32768$8$1$") and passwords.verify_password(NEW_PASSWORD, stored) and NEW_PASSWORD not in stored
    assert stored not in r.text and "password" not in r.text.replace("password_hash", "")


@pytest.mark.parametrize("new,status", [("short77", 422), ("x" * 129, 422), (" " * 12, 422), ("\t\n       ", 422), ("", 422),
                                        ("x" * 8, 200), ("x" * 128, 200), ("pässwörd密码🙂", 200), ("  spaced pass  ", 200)])
def test_the_new_password_policy(client, new, status):
    a = signed_in("a@example.com")
    r = change(a, new=new)
    assert r.status_code == status, r.text
    if status == 200:
        assert login(browser("198.51.100.4"), "a@example.com", new).status_code == 200      # used exactly as typed, never trimmed
        if new != new.strip():
            assert login(browser("198.51.100.6"), "a@example.com", new.strip()).status_code == 401
    else:
        assert not new.strip() or new not in r.text                         # a refused password is never echoed back


def test_the_password_change_body_names_no_account(client):
    a = signed_in("a@example.com")
    b = signed_in("b@example.com", ip="198.51.100.5")
    for extra in ({"user_id": 2}, {"email": "b@example.com"}, {"handle": "u_x"}):
        assert change(a, **extra).status_code == 422
    assert change(a, current=None).status_code == 422 and a.post("/api/auth/password", json={"new_password": NEW_PASSWORD}).status_code == 422
    assert login(browser("198.51.100.7"), "b@example.com").status_code == 200 and me(b) == 200


def test_wrong_current_passwords_are_throttled_per_user(client, clock):
    a = signed_in("a@example.com")
    b = signed_in("b@example.com", ip="198.51.100.5")
    for _ in range(settings.PASSWORD_CHANGE_MAX_FAILURES):
        assert change(a, current="wrong").status_code == 403
    r = change(a)                                                            # even the right one, now
    assert r.status_code == 429 and int(r.headers["retry-after"]) == settings.PASSWORD_CHANGE_WINDOW_SECONDS
    assert login(browser("198.51.100.8"), "a@example.com").status_code == 200   # the password did not change
    assert change(b).status_code == 200                                      # another user is not affected
    advance(clock, seconds=settings.PASSWORD_CHANGE_WINDOW_SECONDS)
    assert change(a).status_code == 200


def test_a_successful_change_clears_the_users_failures(client, clock):
    a = signed_in("a@example.com")
    for _ in range(settings.PASSWORD_CHANGE_MAX_FAILURES - 1):
        change(a, current="wrong")
    assert change(a).status_code == 200
    for _ in range(settings.PASSWORD_CHANGE_MAX_FAILURES - 1):
        assert change(a, current="wrong").status_code == 403
    assert change(a, current=NEW_PASSWORD, new="yet another passphrase").status_code == 200


@pytest.mark.parametrize("pw,status", [(" " * 8, 422), ("\t" * 10, 422), ("pässwörd密码🙂", 201), ("        x", 201)])
def test_registration_refuses_whitespace_only_passwords(client, pw, status):
    r = browser().post("/api/auth/register", json={"email": "p@example.com", "password": pw, "display_name": "P"})
    assert r.status_code == status


# =====================================================================================================================
# login throttling
# =====================================================================================================================
def fail(email, ip):
    return login(browser(ip), email, "definitely wrong")


def test_attack_1_credential_stuffing_many_emails_from_one_address(client, clock):
    register(browser("198.51.100.200"), "real@example.com")
    for i in range(settings.LOGIN_IP_MAX_FAILURES):
        assert fail(f"guess{i}@example.com", "192.0.2.66").status_code == 401
    r = login(browser("192.0.2.66"), "real@example.com")                    # even correct credentials, from that address
    assert r.status_code == 429 and int(r.headers["retry-after"]) == settings.LOGIN_WINDOW_SECONDS
    assert login(browser("192.0.2.67"), "real@example.com").status_code == 200   # the account itself is not locked by it


def test_guessing_one_account_from_many_addresses_is_throttled(client, clock):
    register(browser(), "victim@example.com")
    for i in range(settings.LOGIN_ACCOUNT_MAX_FAILURES):
        assert fail("victim@example.com", f"192.0.2.{i + 1}").status_code == 401
    assert login(browser("192.0.2.200"), "victim@example.com").status_code == 429
    assert login(browser("192.0.2.200"), "VICTIM@Example.COM").status_code == 429        # normalised: letter case does not escape it


def test_unknown_and_known_accounts_are_throttled_identically(client, clock):
    register(browser(), "known@example.com")
    out = {}
    for email in ("known@example.com", "nobody@example.com"):
        for i in range(settings.LOGIN_ACCOUNT_MAX_FAILURES):
            fail(email, f"192.0.2.{50 + i}")
        r = fail(email, "192.0.2.99")
        out[email] = (r.status_code, r.json(), r.headers["retry-after"])
    assert out["known@example.com"] == out["nobody@example.com"] and out["known@example.com"][0] == 429


def test_a_success_resets_the_account_but_never_the_address(client, clock):
    register(browser("198.51.100.200"), "mine@example.com")
    for _ in range(settings.LOGIN_ACCOUNT_MAX_FAILURES - 1):
        fail("mine@example.com", "192.0.2.10")
    assert login(browser("192.0.2.10"), "mine@example.com").status_code == 200
    for _ in range(settings.LOGIN_ACCOUNT_MAX_FAILURES - 1):                # the account's count started again: 4 more are allowed
        assert fail("mine@example.com", "192.0.2.11").status_code == 401
    assert login(browser("192.0.2.11"), "mine@example.com").status_code == 200
    # ...but the address 192.0.2.10 still counts its 4 failures: an attacker who owns one real account cannot use its successful
    # sign-ins to reset the address between guesses at other accounts.
    for i in range(settings.LOGIN_IP_MAX_FAILURES - (settings.LOGIN_ACCOUNT_MAX_FAILURES - 1)):
        assert fail(f"other{i}@example.com", "192.0.2.10").status_code == 401
    assert login(browser("192.0.2.10"), "mine@example.com").status_code == 429


def test_retry_after_counts_down_and_the_window_slides(client, clock):
    for i in range(settings.LOGIN_IP_MAX_FAILURES):
        fail(f"g{i}@example.com", "192.0.2.5")
        if i == 0:
            advance(clock, seconds=100)
    assert int(fail("g@example.com", "192.0.2.5").headers["retry-after"]) == settings.LOGIN_WINDOW_SECONDS - 100
    advance(clock, seconds=settings.LOGIN_WINDOW_SECONDS - 100)
    assert fail("g@example.com", "192.0.2.5").status_code == 401             # the oldest failure has left the window


def test_a_throttled_login_does_no_password_work_and_an_unknown_one_still_does(client, clock, monkeypatch):
    calls = []
    real = service.verify_password
    monkeypatch.setattr(service, "verify_password", lambda pw, stored: calls.append(stored) or real(pw, stored))
    fail("nobody@example.com", "192.0.2.7")
    assert calls == [service._DUMMY_HASH]                                    # unknown email: the dummy hash is still verified
    for _ in range(settings.LOGIN_ACCOUNT_MAX_FAILURES - 1):
        fail("nobody@example.com", "192.0.2.7")
    calls.clear()
    assert fail("nobody@example.com", "192.0.2.7").status_code == 429 and calls == []


def test_limiters_remember_a_bounded_number_of_keys(client, clock, monkeypatch):
    monkeypatch.setattr(settings, "THROTTLE_MAX_KEYS", 3)
    for i in range(10):
        fail(f"spray{i}@example.com", f"192.0.2.{100 + i}")
        assert len(throttle.login_account) <= 3 and len(throttle.login_ip) <= 3
    assert "spray9@example.com" in throttle.login_account._events and "spray0@example.com" not in throttle.login_account._events


def test_a_limit_can_be_raised_through_the_environment(client, clock, monkeypatch):
    """For deployments where many people share one public address (a classroom behind NAT)."""
    monkeypatch.setenv("REGISTER_IP_MAX", "2")
    assert reg("192.0.2.80", "e1@example.com").status_code == 201 and reg("192.0.2.80", "e2@example.com").status_code == 201
    assert reg("192.0.2.80", "e3@example.com").status_code == 429
    for bad in ("0", "-5", "many", ""):
        monkeypatch.setenv("REGISTER_IP_MAX", bad)
        assert settings.throttle_limit("REGISTER_IP_MAX") == settings.REGISTER_IP_MAX


def test_stale_keys_are_dropped_before_live_ones(clock, monkeypatch):
    monkeypatch.setattr(settings, "THROTTLE_MAX_KEYS", 2)
    lim = throttle.Limiter("LOGIN_IP_MAX_FAILURES", "LOGIN_WINDOW_SECONDS")
    lim.record("old", clock[0])
    advance(clock, seconds=settings.LOGIN_WINDOW_SECONDS)
    lim.record("live", clock[0])
    lim.record("new", clock[0])
    assert set(lim._events) == {"live", "new"}
    assert lim.retry_after("gone", clock[0]) is None and "gone" not in lim._events     # asking never creates a key


def test_a_stale_key_goes_before_an_older_but_live_one(clock, monkeypatch):
    """Eviction order: first every key whose window has passed, and only then the longest-remembered keys."""
    monkeypatch.setattr(settings, "THROTTLE_MAX_KEYS", 2)
    lim = throttle.Limiter("LOGIN_IP_MAX_FAILURES", "LOGIN_WINDOW_SECONDS")
    window = settings.LOGIN_WINDOW_SECONDS
    lim.record("first", clock[0])                                            # remembered longest...
    lim.record("second", clock[0])
    advance(clock, seconds=window // 2)
    lim.record("first", clock[0])                                            # ...but used again, so still live later
    advance(clock, seconds=window // 2 + 1)                                  # "second" is now stale, "first" is not
    lim.record("third", clock[0])
    assert set(lim._events) == {"first", "third"}


# =====================================================================================================================
# registration throttling and enumeration
# =====================================================================================================================
def reg(ip, email):
    return browser(ip).post("/api/auth/register", json={"email": email, "password": PASSWORD, "display_name": "R"})


def test_attack_2_registration_spam_from_one_address(client, clock):
    for i in range(settings.REGISTER_IP_MAX):
        assert reg("192.0.2.30", f"spam{i}@example.com").status_code == 201
    r = reg("192.0.2.30", "one-more@example.com")
    assert r.status_code == 429 and int(r.headers["retry-after"]) == settings.REGISTER_WINDOW_SECONDS
    with db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM users WHERE email = 'one-more@example.com'").fetchone()[0] == 0
    assert reg("192.0.2.31", "neighbour@example.com").status_code == 201   # other addresses can still sign up
    advance(clock, seconds=settings.REGISTER_WINDOW_SECONDS)
    assert reg("192.0.2.30", "later@example.com").status_code == 201


def test_probing_for_registered_emails_counts_against_the_same_limit(client):
    reg("192.0.2.40", "taken@example.com")
    for _ in range(settings.REGISTER_IP_MAX - 1):
        assert reg("192.0.2.41", "taken@example.com").status_code == 409
    assert reg("192.0.2.41", "taken@example.com").status_code == 409
    assert reg("192.0.2.41", "taken@example.com").status_code == 429


# =====================================================================================================================
# authorization
# =====================================================================================================================
def test_parents_and_admins_manage_only_their_own_sessions(client, make_admin):
    learner = signed_in("kid@example.com")
    parent = signed_in("p@example.com", ip="198.51.100.20", role="parent")
    make_admin("root@example.com")
    admin = browser("198.51.100.21")
    assert login(admin, "root@example.com").status_code == 200
    kid_session = current_id(learner)
    for other in (parent, admin):
        listed = other.get("/api/auth/sessions").json()["sessions"]
        assert len(listed) == 1 and listed[0]["id"] != kid_session
        assert other.delete(f"/api/auth/sessions/{kid_session}").status_code == 404
        assert other.post("/api/auth/logout-all").json()["revoked"] == 0
    assert me(learner) == 200


def test_attack_3_guessing_session_ids_reveals_nothing(client):
    a = signed_in("a@example.com")
    signed_in("v@example.com", ip="198.51.100.5")
    bodies = {a.delete(f"/api/auth/sessions/{i:032x}").text for i in range(25)}
    assert bodies == {'{"detail":"Not found"}'} and len(session_rows()) == 2


# =====================================================================================================================
# the remaining attacks
# =====================================================================================================================
def test_attack_4_a_session_id_from_another_account(client):
    a = signed_in("a@example.com")
    v = signed_in("v@example.com", ip="198.51.100.5")
    assert a.delete(f"/api/auth/sessions/{current_id(v)}").status_code == 404 and me(v) == 200


def test_attack_5_reusing_a_logged_out_session(client):
    a = signed_in("a@example.com")
    stale = token(a)
    a.post("/api/auth/logout")
    assert me(with_token(stale)) == 401


def test_attack_6_reusing_a_session_after_logout_all(client):
    a = signed_in("a@example.com")
    b = second_browser("a@example.com")
    stale = token(b)
    a.post("/api/auth/logout-all")
    assert me(with_token(stale)) == 401


def test_attack_7_reusing_another_session_after_a_password_change(client):
    a = signed_in("a@example.com")
    stolen = token(second_browser("a@example.com"))
    change(a)
    assert me(with_token(stolen)) == 401


def test_attack_8_forged_public_id_in_delete(client):
    a = signed_in("a@example.com")
    for forged in ("%2e%2e", "' OR 1=1 --", "a" * 64, "*", "%25"):
        assert a.delete(f"/api/auth/sessions/{forged}").status_code == 404
    assert a.delete("/api/auth/sessions/../sessions").status_code == 405     # normalised to another path, which has no DELETE
    assert a.delete("/api/auth/sessions/" + "a" * 65).status_code == 422     # longer than any id: refused before any lookup
    assert me(a) == 200 and len(session_rows()) == 1


def test_attack_9_password_change_without_the_current_password(client):
    a = signed_in("a@example.com")
    assert a.post("/api/auth/password", json={"new_password": NEW_PASSWORD}).status_code == 422
    assert change(a, current="").status_code == 422
    assert login(browser("198.51.100.9"), "a@example.com").status_code == 200


def test_attack_10_password_change_as_another_user(client):
    a = signed_in("a@example.com")
    signed_in("b@example.com", ip="198.51.100.5")
    assert change(a, current=PASSWORD, user_id=2).status_code == 422
    assert change(a).status_code == 200                                      # A changes A...
    assert login(browser("198.51.100.10"), "b@example.com").status_code == 200   # ...and B is untouched


def test_attack_11_and_12_last_seen_and_expiry_cannot_be_moved_from_outside(client, clock):
    a = signed_in("a@example.com")
    with db() as conn:                                                       # not even a direct write could push a session past its life
        with pytest.raises(Exception):
            conn.execute("UPDATE sessions SET expires_at = '2099-01-01 00:00:00'")
    advance(clock, minutes=31)
    a.get("/api/auth/me", headers={"X-Last-Seen": service._fmt(clock[0])})
    assert me(a) == 401


def test_attack_13_session_apis_anonymously(client):
    test_session_apis_need_a_session(client)


def test_attack_14_admin_cannot_reach_a_learners_session(client, make_admin):
    learner = signed_in("kid@example.com")
    make_admin("root@example.com")
    admin = browser("198.51.100.21")
    login(admin, "root@example.com")
    assert admin.delete(f"/api/auth/sessions/{current_id(learner)}").status_code == 404 and me(learner) == 200
    assert all(s["id"] != current_id(learner) for s in admin.get("/api/auth/sessions").json()["sessions"])


# =====================================================================================================================
# cookies
# =====================================================================================================================
def cookie_of(r):
    return r.headers["set-cookie"]


def test_session_cookies_are_httponly_lax_and_not_secure_on_plain_http(client):
    c = browser()
    r = c.post("/api/auth/register", json={"email": "c@example.com", "password": PASSWORD, "display_name": "C"})
    for set_cookie in (cookie_of(r), cookie_of(change(c)), cookie_of(login(c, "c@example.com", NEW_PASSWORD))):
        assert "HttpOnly" in set_cookie and "SameSite=lax" in set_cookie and "Secure" not in set_cookie and "Path=/" in set_cookie
        assert f"Max-Age={settings.SESSION_TTL_DAYS * 86400}" in set_cookie
    assert "HttpOnly" in cookie_of(c.post("/api/auth/logout"))


def test_session_cookies_are_secure_when_configured(client, monkeypatch):
    monkeypatch.setenv("COOKIE_SECURE", "1")
    c = browser()
    r = c.post("/api/auth/register", json={"email": "c@example.com", "password": PASSWORD, "display_name": "C"})
    assert "Secure" in cookie_of(r) and "HttpOnly" in cookie_of(r)
    c.cookies.set("llb_session", r.cookies.get("llb_session"))
    assert "Secure" in cookie_of(change(c)) and "Secure" in cookie_of(c.post("/api/auth/logout"))


def test_the_token_never_appears_in_a_response_body(client):
    c = signed_in("a@example.com")
    t = token(c)
    bodies = [c.get(p).text for p in ("/api/auth/me", "/api/auth/sessions")] + [change(c).text, c.post("/api/auth/logout-all").text]
    assert all(t not in b and token(c) not in b for b in bodies)
