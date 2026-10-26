"""Phase 14E: security events (what is recorded, append-only, private, the failure policy), the admin security-event and account listings
(admin + MFA only, bounded, cursor/offset pages, no identity), and the security health warnings."""
import logging
import re
import sqlite3
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from backend import main, settings
from backend.admin import health as health_service
from backend.admin.learners import ref_for
from backend.auth import events, service
from backend.db import connect

from .conftest import FRONTEND_HEADERS, PASSWORD, plant_mfa_session, register
from .test_two_factor import clock, code, enroll, tick  # noqa: F401  (clock is a fixture)

IP = "203.0.113.50"
NEW_PASSWORD = "a brand new passphrase"


def browser(ip=IP):
    return TestClient(main.app, headers=dict(FRONTEND_HEADERS), client=(ip, 40000))


def db():
    return connect(main.DB_PATH)


def rows(event_type=None):
    with db() as conn:
        sql = "SELECT event_type, outcome, user_id, method, reason, stage, count, ip_ref FROM security_events" + (" WHERE event_type = ?" if event_type else "") + " ORDER BY id"
        return [dict(r) for r in conn.execute(sql, (event_type,) if event_type else ())]


def types():
    return [r["event_type"] for r in rows()]


def uid(email):
    with db() as conn:
        return conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()[0]


def user(email="a@example.com", role="learner", ip=IP):
    c = browser(ip)
    register(c, email, role=role)
    return c


def login(c, email="a@example.com", password=PASSWORD):
    return c.post("/api/auth/login", json={"email": email, "password": password})


def admin_browser(make_admin, email="root@example.com", mfa=True):
    make_admin(email)
    c = browser("198.51.100.200")
    assert login(c, email).status_code == 200
    return plant_mfa_session(c, email) if mfa else c


def page(c, **params):
    r = c.get("/api/admin/security-events", params=params)
    assert r.status_code == 200, r.text
    return r.json()


# =====================================================================================================================
# recording: sign-in, sign-out, sessions, password
# =====================================================================================================================
def test_a_successful_sign_in_is_recorded_in_the_session_transaction(client):
    user()
    login(browser())
    (ev,) = rows("login_success")
    assert ev == {"event_type": "login_success", "outcome": "ok", "user_id": uid("a@example.com"), "method": "password", "reason": None, "stage": "sign_in",
                  "count": None, "ip_ref": events.ip_ref(IP)}
    assert re.fullmatch(r"[0-9a-f]{16}", ev["ip_ref"]) and ev["ip_ref"] != events.ip_ref("198.51.100.1")


def test_failed_sign_ins_are_recorded_for_known_and_unknown_accounts(client):
    user()
    login(browser(), password="wrong password")
    login(browser(), email="nobody@example.com", password="wrong password")
    known, unknown = rows("login_failure")
    assert known["user_id"] == uid("a@example.com") and unknown["user_id"] is None
    assert known["reason"] == unknown["reason"] == "wrong_credentials" and known["outcome"] == "failed"


def test_throttled_sign_ins_are_recorded(client):
    for _ in range(settings.LOGIN_ACCOUNT_MAX_FAILURES):
        login(browser(), email="x@example.com", password="wrong password")
    assert login(browser(), email="x@example.com", password="wrong password").status_code == 429
    (ev,) = rows("login_throttled")
    assert ev["outcome"] == "denied" and ev["reason"] == "throttled" and ev["user_id"] is None


def test_logout_logout_all_and_revocation_are_recorded(client):
    a = user()
    b = browser("198.51.100.2")
    login(b)
    login(browser("198.51.100.3"))
    sid = next(s["id"] for s in a.get("/api/auth/sessions").json()["sessions"] if not s["current"])
    a.delete(f"/api/auth/sessions/{sid}")
    a.post("/api/auth/logout-all")
    a.post("/api/auth/logout")
    me = uid("a@example.com")
    assert [(r["event_type"], r["count"]) for r in rows() if r["event_type"] in ("session_revoked", "logout_all", "logout")] == [("session_revoked", 1), ("logout_all", 1), ("logout", None)]
    assert all(r["user_id"] == me for r in rows() if r["event_type"] in ("session_revoked", "logout_all", "logout"))


def test_a_logout_without_a_session_records_nothing(client):
    browser().post("/api/auth/logout")
    assert rows("logout") == []


def test_password_change_success_failure_and_throttle_are_recorded(client):
    a = user()
    login(browser("198.51.100.4"))
    for _ in range(settings.PASSWORD_CHANGE_MAX_FAILURES):
        a.post("/api/auth/password", json={"current_password": "wrong", "new_password": NEW_PASSWORD})
    a.post("/api/auth/password", json={"current_password": PASSWORD, "new_password": NEW_PASSWORD})
    assert [r["event_type"] for r in rows() if r["event_type"].startswith("password")] == ["password_change_failed"] * 5 + ["password_change_throttled"]
    service.reset_throttle()
    assert a.post("/api/auth/password", json={"current_password": PASSWORD, "new_password": NEW_PASSWORD}).status_code == 200
    (ev,) = rows("password_changed")
    assert ev["count"] == 2 and ev["user_id"] == uid("a@example.com")


# =====================================================================================================================
# recording: two-factor and admins
# =====================================================================================================================
def test_the_two_factor_lifecycle_is_recorded(client, clock):
    a = user()
    secret, codes = enroll(a, clock)
    assert types().count("mfa_setup_started") == 1 and rows("mfa_enabled")[0]["method"] == "password+totp"
    c = browser("198.51.100.5")
    assert login(c).json() == {"mfa_required": True}
    c.post("/api/auth/2fa/verify", json={"code": "000000"})
    c.post("/api/auth/2fa/verify", json={"code": code(secret, clock)})
    tick(clock)
    d = browser("198.51.100.6")
    login(d)
    d.post("/api/auth/2fa/verify", json={"recovery_code": codes[0]})
    a.post("/api/auth/2fa/recovery-codes", json={"password": PASSWORD, "code": code(secret, clock)})
    tick(clock)
    a.post("/api/auth/2fa/disable", json={"password": PASSWORD, "code": "000000"})
    a.post("/api/auth/2fa/disable", json={"password": PASSWORD, "code": code(secret, clock)})
    t = [x for x in types() if x.startswith("mfa")]
    assert t == ["mfa_setup_started", "mfa_enabled", "mfa_challenge", "mfa_failure", "mfa_success", "mfa_challenge", "mfa_success", "mfa_recovery_code_used",
                 "mfa_recovery_codes_regenerated", "mfa_disable_failed", "mfa_disabled"]
    assert rows("mfa_recovery_code_used")[0]["count"] == 9 and rows("mfa_recovery_codes_regenerated")[0]["count"] == 10
    assert [r["method"] for r in rows("mfa_success")] == ["password+totp", "password+recovery"] and rows("mfa_failure")[0]["reason"] == "wrong_code"


def test_two_factor_throttling_is_recorded(client, clock):
    secret, _ = enroll(user(), clock)
    for _ in range(2):
        c = browser("198.51.100.7")
        login(c)
        for _ in range(settings.MFA_CHALLENGE_MAX_ATTEMPTS):
            c.post("/api/auth/2fa/verify", json={"code": "000000"})
    c = browser("198.51.100.8")
    login(c)
    assert c.post("/api/auth/2fa/verify", json={"code": code(secret, clock)}).status_code == 429
    assert len(rows("mfa_failure")) == 10 and rows("mfa_throttled")[0]["reason"] == "throttled"


def test_an_unusable_challenge_is_recorded_without_an_account(client, clock):
    c = browser()
    c.cookies.set("llb_mfa_challenge", "forged-challenge", path="/api/auth/2fa")
    c.post("/api/auth/2fa/verify", json={"code": "123456"})
    (ev,) = rows("mfa_failure")
    assert ev["reason"] == "expired_challenge" and ev["user_id"] is None


def test_admin_sign_in_with_a_code_and_admin_refusals_are_recorded(client, clock, make_admin):
    make_admin("root@example.com")
    c = browser("198.51.100.9")
    login(c, "root@example.com")
    assert c.get("/api/admin/dashboard").status_code == 403
    c.get("/api/admin/audit")                                                # a second refusal within a minute is not repeated
    assert len(rows("admin_access_denied_mfa")) == 1
    clock[0] += timedelta(seconds=events.DENIAL_QUIET_SECONDS + 1)
    c.get("/api/admin/dashboard")
    assert len(rows("admin_access_denied_mfa")) == 2
    secret, _ = enroll(c, clock)
    admin2 = browser("198.51.100.10")
    login(admin2, "root@example.com")
    admin2.post("/api/auth/2fa/verify", json={"code": code(secret, clock)})
    (ev,) = rows("admin_login")
    assert ev["user_id"] == uid("root@example.com") and ev["method"] == "password+totp"
    admin2.post("/api/auth/2fa/disable", json={"password": PASSWORD, "code": code(secret, clock, 1)})
    assert rows("mfa_disable_failed")[-1]["reason"] == "admin_cannot_disable" and rows("mfa_disable_failed")[-1]["outcome"] == "denied"


def test_failed_admin_sign_in_is_recorded_like_any_other(client, make_admin):
    make_admin("root@example.com")
    login(browser(), "root@example.com", "wrong password")
    assert rows("login_failure")[0]["user_id"] == uid("root@example.com")


def test_admin_content_changes_stay_in_the_admin_audit_log(client, make_admin):
    """No duplicate system: CMS writes are recorded in Phase 13's admin_audit_log, not as security events."""
    a = admin_browser(make_admin)
    before = types()
    assert a.post("/api/admin/content/topics", json={"slug": "sec-topic", "name": "S", "icon": "s"}).status_code == 201
    assert types() == before
    with db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM admin_audit_log WHERE entity_type = 'topic' AND action = 'create'").fetchone()[0] == 1


def test_reading_the_events_records_nothing(client, make_admin):
    a = admin_browser(make_admin)
    before = len(rows())
    for _ in range(3):
        page(a)
        a.get("/api/admin/users")
    assert len(rows()) == before


# =====================================================================================================================
# the failure policy
# =====================================================================================================================
def test_a_state_change_and_its_event_commit_together(client, monkeypatch):
    """If the password_changed event cannot be written, the password change does not happen either (no change without its event)."""
    a = user()
    other = browser("198.51.100.11")
    login(other)
    real = events.record

    def broken(conn, event_type, outcome, **kw):
        if event_type == "password_changed":
            raise sqlite3.IntegrityError("simulated")
        return real(conn, event_type, outcome, **kw)
    monkeypatch.setattr(events, "record", broken)
    with pytest.raises(sqlite3.IntegrityError):
        a.post("/api/auth/password", json={"current_password": PASSWORD, "new_password": NEW_PASSWORD})
    monkeypatch.setattr(events, "record", real)
    assert login(browser("198.51.100.12")).status_code == 200                    # the old password still works
    assert other.get("/api/auth/me").status_code == 200                           # and no session was revoked


def test_attack_20_a_busy_database_cannot_turn_a_failed_sign_in_into_an_error(client, monkeypatch, caplog):
    user()
    real = events.record

    def locked(conn, event_type, outcome, **kw):
        if event_type == "login_failure":
            raise sqlite3.OperationalError("database is locked")
        return real(conn, event_type, outcome, **kw)
    monkeypatch.setattr(events, "record", locked)
    with caplog.at_level(logging.WARNING, logger="backend.auth.events"):
        r = login(browser(), password="wrong password")
    assert r.status_code == 401 and r.json() == {"detail": "Invalid email or password"}
    assert "login_failure not recorded (OperationalError)" in caplog.text and "a@example.com" not in caplog.text and "wrong password" not in caplog.text
    assert login(browser()).status_code == 200


def test_a_malformed_event_is_a_programming_error_and_is_never_swallowed(client):
    with pytest.raises(ValueError):
        events.record_now(main.DB_PATH, "login_success_but_made_up", "ok")
    for bad in ({"method": "magic"}, {"reason": "because"}, {"stage": "lobby"}, {"count": -1}, {"count": 10**9}, {"count": True}, {"count": "3"}):
        with pytest.raises(ValueError):
            events.record_now(main.DB_PATH, "logout", "ok", **bad)
    with pytest.raises(ValueError):
        events.record_now(main.DB_PATH, "logout", "maybe")
    assert rows() == []


def test_the_best_effort_writer_swallows_only_transient_errors(client):
    """An integrity violation is never swallowed, even by the best-effort writer: here, an event for an account that does not exist."""
    with pytest.raises(sqlite3.IntegrityError):
        events.record_now(main.DB_PATH, "logout", "ok", user_id=999_999)
    assert rows() == []


def test_attack_20b_nothing_a_client_sends_reaches_an_event(client):
    """Event fields are all chosen by the server: an odd e-mail, password or header cannot make an insert fail or appear in it."""
    user()
    for email, pw in (("x'); DROP TABLE security_events;--@example.com", "x"), ("a@example.com", "' OR 1=1 --"), ("ü@例え.example", "\x00" * 8)):
        r = browser().post("/api/auth/login", json={"email": email, "password": pw}, headers={"X-Event-Type": "admin_login", "User-Agent": "<script>"})
        assert r.status_code in (401, 422)
    assert set(types()) <= {"login_failure"} and all(r["outcome"] == "failed" for r in rows())


# =====================================================================================================================
# append-only and closed fields (the schema)
# =====================================================================================================================
def one_event():
    events.record_now(main.DB_PATH, "logout", "ok", user_id=uid("a@example.com"), count=1)


@pytest.mark.parametrize("change", ["event_type = 'admin_login'", "outcome = 'ok'", "occurred_at = '2000-01-01 00:00:00'", "count = 2", "ip_ref = NULL",
                                    "method = 'password'", "user_id = NULL, count = 2", "user_id = user_id + 1"])
def test_attack_10_events_cannot_be_updated(client, change):
    """The one permitted change, detaching an event from a deleted account (the foreign key's ON DELETE SET NULL), is covered below; any
    other change, including one combined with that, is refused."""
    user()
    one_event()
    before = rows()
    with db() as conn:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(f"UPDATE security_events SET {change}")
    assert rows() == before


def test_attack_11_events_cannot_be_deleted(client):
    user()
    one_event()
    before = rows()
    with db() as conn:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("DELETE FROM security_events")
    assert rows() == before


def test_removing_an_account_only_detaches_its_events(client):
    user()
    one_event()
    with db() as conn:
        conn.execute("DELETE FROM users WHERE email = 'a@example.com'")
    (ev,) = rows("logout")
    assert ev["user_id"] is None and ev["count"] == 1


@pytest.mark.parametrize("bad", [("event_type", "made_up"), ("outcome", "maybe"), ("method", "magic"), ("reason", "free text here"), ("stage", "lobby"),
                                 ("count", -1), ("count", 100001), ("ip_ref", "203.0.113.50"), ("ip_ref", "ABCDEF0123456789"), ("ip_ref", "0" * 17)])
def test_attack_8_and_9_the_schema_refuses_unknown_or_free_text_fields(client, bad):
    col, val = bad
    row = {"occurred_at": "2026-10-01 00:00:00", "event_type": "logout", "outcome": "ok", col: val}
    with db() as conn:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(f"INSERT INTO security_events({', '.join(row)}) VALUES ({', '.join('?' * len(row))})", tuple(row.values()))


def test_the_table_has_no_free_text_column(client):
    with db() as conn:
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(security_events)")}
    assert cols == {"id", "occurred_at", "event_type", "outcome", "user_id", "method", "reason", "stage", "count", "ip_ref"}


# =====================================================================================================================
# privacy
# =====================================================================================================================
def test_attack_12_to_15_no_secret_reaches_an_event_or_the_admin_view(client, clock, make_admin):
    a = user()
    login(browser(), password="this was the wrong one")
    s = a.post("/api/auth/2fa/setup", json={"password": PASSWORD}).json()
    codes = a.post("/api/auth/2fa/confirm", json={"code": code(s["secret"], clock)}).json()["recovery_codes"]
    tick(clock)
    b = browser("198.51.100.13")
    login(b)
    challenge = b.cookies.get("llb_mfa_challenge")
    b.post("/api/auth/2fa/verify", json={"recovery_code": codes[1]})
    a.post("/api/auth/password", json={"current_password": PASSWORD, "new_password": NEW_PASSWORD})
    admin = admin_browser(make_admin)
    with db() as conn:
        dump = "\n".join(str(tuple(r)) for r in conn.execute("SELECT * FROM security_events"))
        password_hash = conn.execute("SELECT password_hash FROM users WHERE email = 'a@example.com'").fetchone()[0]
        token_hashes = [r[0] for r in conn.execute("SELECT token_hash FROM sessions")]
    view = page(admin, limit=100)
    text = dump + str(view)
    for secret in (PASSWORD, NEW_PASSWORD, "this was the wrong one", password_hash, s["secret"], *codes, challenge, b.cookies.get("llb_session"),
                   a.cookies.get("llb_session"), *token_hashes, "a@example.com", "root@example.com", IP, "198.51.100.13"):
        assert secret not in text, secret
    me = uid("a@example.com")
    assert {e["account"] for e in view["items"] if e["account"]} >= {ref_for(me)}
    assert not any(isinstance(v, int) and v == me for e in view["items"] for k, v in e.items() if k != "count")
    assert all(set(e) == {"occurred_at", "type", "outcome", "account", "method", "reason", "stage", "count", "network"} for e in view["items"])


# =====================================================================================================================
# the admin security-event view: who, and how it pages
# =====================================================================================================================
@pytest.mark.parametrize("role", ["learner", "parent"])
def test_attack_1_and_2_learners_and_parents_cannot_read_events(client, role):
    c = user(f"{role}@example.com", role)
    r = c.get("/api/admin/security-events")
    assert r.status_code == 403 and r.json()["detail"] == "Insufficient permissions"


def test_attack_3_an_admin_without_a_second_factor_cannot_read_events(client, make_admin):
    c = admin_browser(make_admin, mfa=False)
    r = c.get("/api/admin/security-events")
    assert r.status_code == 403 and r.json()["detail"]["code"] == "mfa_required"
    assert browser().get("/api/admin/security-events").status_code == 401


@pytest.mark.parametrize("demo", ["1", "0"])
def test_attack_16_and_17_demo_mode_or_forged_levels_do_not_open_the_view(client, make_admin, monkeypatch, demo):
    monkeypatch.setenv("DEMO_MODE", demo)
    c = admin_browser(make_admin, mfa=False)
    c.cookies.set("mfa_level", "1")
    r = c.get("/api/admin/security-events", params={"mfa_level": 1}, headers={"X-MFA-Level": "1"})
    assert r.status_code == 403


def seed(n):
    user()
    for i in range(n):
        events.record_now(main.DB_PATH, "logout", "ok", user_id=uid("a@example.com"), count=i)


def test_pages_are_newest_first_without_duplicates_or_gaps(client, make_admin):
    admin = admin_browser(make_admin)
    seed(60)
    with db() as conn:
        expected = [r[0] for r in conn.execute("SELECT count FROM security_events WHERE event_type = 'logout' ORDER BY id DESC")]
    seen, cursor, pages = [], None, 0
    while True:
        p = page(admin, type="logout", limit=25, **({"before": cursor} if cursor else {}))
        seen += [e["count"] for e in p["items"]]
        pages += 1
        cursor = p["next"]
        if not cursor:
            break
    assert seen == expected and pages == 3 and len(seen) == 60 == len(set(seen))


def test_new_events_do_not_shift_a_page_in_progress(client, make_admin):
    admin = admin_browser(make_admin)
    seed(30)
    first = page(admin, type="logout", limit=10)
    events.record_now(main.DB_PATH, "logout", "ok", user_id=uid("a@example.com"), count=999)       # arrives meanwhile
    second = page(admin, type="logout", limit=10, before=first["next"])
    assert [e["count"] for e in first["items"]] == list(range(29, 19, -1)) and [e["count"] for e in second["items"]] == list(range(19, 9, -1))


def test_the_default_and_the_maximum_page_size(client, make_admin):
    admin = admin_browser(make_admin)
    seed(130)
    assert len(page(admin)["items"]) == 25
    assert len(page(admin, limit=100)["items"]) == 100


@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 101}, {"limit": -1}, {"limit": "many"}, {"before": 0}, {"before": -5}, {"before": "abc"},
                                    {"type": "made_up"}, {"type": "logout' OR '1'='1"}, {"type": "logout; DROP TABLE security_events"}])
def test_attack_5_to_7_invalid_parameters_are_refused(client, make_admin, params):
    admin = admin_browser(make_admin)
    r = admin.get("/api/admin/security-events", params=params)
    assert r.status_code == 422 and isinstance(r.json()["detail"], list)
    assert len(rows()) > 0                                                   # the table is still there


def test_attack_4_and_19_there_is_no_filter_by_person(client, make_admin):
    admin = admin_browser(make_admin)
    seed(5)
    victim = uid("a@example.com")
    plain = page(admin, limit=100)
    for params in ({"user_id": victim}, {"account": ref_for(victim)}, {"email": "a@example.com"}, {"ip": IP}, {"q": "a@example.com"}):
        assert page(admin, limit=100, **params) == plain                     # unknown parameters change nothing


def test_the_type_filter_returns_only_that_type(client, make_admin):
    admin = admin_browser(make_admin)
    seed(3)
    login(browser(), password="wrong")
    assert {e["type"] for e in page(admin, type="login_failure")["items"]} == {"login_failure"}


# =====================================================================================================================
# the account listing
# =====================================================================================================================
def accounts(c, **params):
    r = c.get("/api/admin/users", params=params)
    assert r.status_code == 200, r.text
    return r.json()


def test_accounts_carry_references_roles_dates_and_two_factor_only(client, clock, make_admin):
    a = user()
    enroll(a, clock)
    user("p@example.com", "parent")
    admin = admin_browser(make_admin)
    body = accounts(admin, limit=100)
    assert set(body) == {"items", "total", "limit", "offset"} and body["total"] == 4
    assert all(set(i) == {"ref", "roles", "created", "two_factor"} for i in body["items"])
    by_ref = {i["ref"]: i for i in body["items"]}
    assert by_ref[ref_for(uid("a@example.com"))]["two_factor"] is True and by_ref[ref_for(uid("p@example.com"))]["roles"] == ["parent"]
    assert all(re.fullmatch(r"\d{4}-\d{2}-\d{2}", i["created"]) for i in body["items"])
    text = str(body)
    for leak in ("@example.com", "Test User", "demo-alex", "u_", "scrypt", "password", "token", "secret"):
        assert leak not in text, leak


def test_a_setup_that_was_never_confirmed_is_not_two_factor(client, make_admin):
    a = user()
    assert a.post("/api/auth/2fa/setup", json={"password": PASSWORD}).status_code == 200            # pending, not confirmed
    admin = admin_browser(make_admin)
    by_ref = {i["ref"]: i for i in accounts(admin, limit=100)["items"]}
    assert by_ref[ref_for(uid("a@example.com"))]["two_factor"] is False


def test_account_pages_are_bounded_stable_and_complete(client, make_admin):
    admin = admin_browser(make_admin)
    for i in range(30):
        register(TestClient(main.app), f"u{i}@example.com")
    assert len(accounts(admin)["items"]) == 25 and accounts(admin)["limit"] == 25
    everyone = accounts(admin, limit=100)["items"]
    first, second = accounts(admin, limit=20, offset=0)["items"], accounts(admin, limit=20, offset=20)["items"]
    assert first + second == everyone and len({i["ref"] for i in first + second}) == len(everyone) == 32
    assert accounts(admin, limit=20, offset=20)["items"] == second                               # same answer twice
    assert accounts(admin, offset=1000)["items"] == []


@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 101}, {"limit": -3}, {"offset": -1}, {"limit": "all"}, {"offset": "x"}])
def test_attack_6_and_7_account_page_parameters_are_bounded(client, make_admin, params):
    admin = admin_browser(make_admin)
    assert admin.get("/api/admin/users", params=params).status_code == 422


@pytest.mark.parametrize("role", ["learner", "parent"])
def test_attack_18_the_account_listing_is_admin_and_mfa_only(client, make_admin, role):
    assert user(f"{role}@example.com", role).get("/api/admin/users").status_code == 403
    assert admin_browser(make_admin, mfa=False).get("/api/admin/users").json()["detail"]["code"] == "mfa_required"
    assert browser().get("/api/admin/users").status_code == 401


def test_attack_19_email_cannot_be_pulled_through_parameters(client, make_admin):
    user()
    admin = admin_browser(make_admin)
    for params in ({"fields": "email"}, {"include": "email"}, {"q": "a@example.com"}, {"email": "a@example.com"}, {"sort": "email"}):
        r = admin.get("/api/admin/users", params=params)
        assert r.status_code == 200 and "@example.com" not in r.text


# =====================================================================================================================
# security health
# =====================================================================================================================
def security(c):
    return c.get("/api/admin/health").json()["security"]


def codes_of(sec):
    return {w["code"]: w["severity"] for w in sec["warnings"]}


def test_cookie_secure_off_is_a_warning_and_on_is_not(client, make_admin, monkeypatch):
    admin = admin_browser(make_admin)
    monkeypatch.setenv("COOKIE_SECURE", "0")
    assert security(admin)["cookie_secure"] is False and codes_of(security(admin))["cookie_not_secure"] == "warning"
    monkeypatch.setenv("COOKIE_SECURE", "1")
    assert security(admin)["cookie_secure"] is True and "cookie_not_secure" not in codes_of(security(admin))


@pytest.mark.parametrize("value,status", [(None, "missing"), ("", "missing"), ("not-a-key", "malformed"), ("A" * 44, "malformed")])
def test_a_missing_or_malformed_totp_key_is_critical_when_there_are_admins(client, make_admin, monkeypatch, value, status):
    admin = admin_browser(make_admin)
    if value is None:
        monkeypatch.delenv("TOTP_ENC_KEY")
    else:
        monkeypatch.setenv("TOTP_ENC_KEY", value)
    sec = security(admin)
    assert sec["totp_key"] == status and codes_of(sec)[f"totp_key_{status}"] == "critical"
    assert (value or "") not in str(sec).replace(status, "") or not value


def test_a_valid_totp_key_is_reported_as_valid_and_never_shown(client, make_admin):
    admin = admin_browser(make_admin)
    r = admin.get("/api/admin/health")
    assert r.json()["security"]["totp_key"] == "valid" and not any(w["code"].startswith("totp_key") for w in r.json()["security"]["warnings"])
    from .conftest import TEST_TOTP_ENC_KEY
    assert TEST_TOTP_ENC_KEY not in r.text


def test_without_admins_a_missing_key_is_only_a_warning(monkeypatch):
    monkeypatch.delenv("TOTP_ENC_KEY")
    assert codes_of(health_service._security(0, 0))["totp_key_missing"] == "warning"
    assert codes_of(health_service._security(1, 0))["totp_key_missing"] == "critical"


def test_admins_without_two_factor_demo_mode_and_live_ai_are_warnings(client, clock, make_admin, monkeypatch):
    admin = admin_browser(make_admin)
    make_admin("second@example.com")
    monkeypatch.setenv("DEMO_MODE", "1")
    monkeypatch.setenv("DEMO_LIVE_AI", "1")
    sec = security(admin)
    assert sec["admins"] == 2 and sec["admins_with_two_factor"] == 0
    assert {"admins_without_two_factor", "demo_mode_on", "demo_live_ai_on"} <= set(codes_of(sec))
    monkeypatch.setenv("DEMO_MODE", "0")
    monkeypatch.setenv("DEMO_LIVE_AI", "0")
    assert not {"demo_mode_on", "demo_live_ai_on"} & set(codes_of(security(admin)))


def test_the_public_health_check_says_only_yes_or_no(client, monkeypatch):
    monkeypatch.setattr(main, "provider", lambda: "groq")
    r = browser().get("/api/health")
    assert r.json() == {"ok": True, "ai": True} and "groq" not in r.text
    monkeypatch.setattr(main, "provider", lambda: None)
    assert browser().get("/api/health").json() == {"ok": True, "ai": False}
