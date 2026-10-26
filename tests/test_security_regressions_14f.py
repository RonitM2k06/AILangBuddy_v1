"""Phase 14F: regression tests for the security defects the final verification found. Each was reproduced first (against the Phase 14E code)
and is fixed in this phase:

  DEFECT-1  Concurrent wrong codes against one login challenge: every request passed the "attempts left" check before any was counted, so
            the extra ones hit the schema's CHECK (attempts <= 5) and failed with an IntegrityError (a 500), and their failures were rolled
            back uncounted. Now an attempt is taken from the challenge in one conditional UPDATE before the code is checked.
  DEFECT-2  Concurrent wrong passwords for one account: the in-memory throttle was checked, then the (slow) password, then the failure was
            counted, so every concurrent guess got through (15 checked against a limit of 5). Now the attempt is counted before the
            password is checked, in one locked step, and given back when the password was right.
  DEFECT-3  The same race in the password-change throttle.
  DEFECT-4  The same race in the database-backed second-factor limit (MFA_MAX_FAILURES per user): now a failure row is reserved by one
            conditional INSERT before the code is checked, and given back on success.
  DEFECT-5  A whole number beyond SQLite's 64-bit range in a path, query string or JSON body raised OverflowError: a 500 on many routes.
            Now it is a 422.
  DEFECT-6  Refusals that cost nothing to repeat wrote one security event each: throttled sign-ins (no password is checked once throttled)
            and dead login challenges let an anonymous client add rows without limit (about 400 a second in the probe). Now they are recorded
            at most once a minute per type, account, reason, stage and address.
Every database is a temp file; no provider is reachable."""
import base64
import json
import re
import sqlite3
import threading
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from backend import main, settings
from backend.auth import events, mfa, service, throttle, totp
from backend.db import connect
from backend.repositories import two_factor as tf_repo

from .conftest import FRONTEND_HEADERS, PASSWORD, plant_mfa_session, register

NEW_PASSWORD = "a different long password"


@pytest.fixture
def clock(monkeypatch):
    now = [service.utcnow().replace(microsecond=0)]
    monkeypatch.setattr(service, "utcnow", lambda: now[0])
    return now


def browser(ip="198.51.100.20"):
    return TestClient(main.app, headers=dict(FRONTEND_HEADERS), client=(ip, 40000))


def db():
    return connect(main.DB_PATH)


def uid(email):
    with db() as conn:
        return conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()[0]


def event_count(event_type, reason=None):
    with db() as conn:
        return conn.execute("SELECT COUNT(*) FROM security_events WHERE event_type = ? AND (? IS NULL OR reason = ?)", (event_type, reason, reason)).fetchone()[0]


def run_together(n, fn):
    """Run fn(i) on n threads at once; returns the results (or exceptions) in order."""
    out = [None] * n
    gate = threading.Barrier(n)

    def run(i):
        try:
            gate.wait(5)
            out[i] = fn(i)
        except Exception as exc:          # noqa: BLE001 - the test inspects what each request ended with
            out[i] = exc
    threads = [threading.Thread(target=run, args=(i,)) for i in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(30)
    return out


@pytest.fixture
def slow_passwords(monkeypatch):
    """Every password check waits until all concurrent requests have reached it (or 1 s): the widest possible race window."""
    real = service.verify_password
    checked, lock = [], threading.Lock()
    gate = {"barrier": None}

    def verify(password, stored):
        with lock:
            checked.append(password)
        if gate["barrier"] is not None:
            try:
                gate["barrier"].wait(1)
            except threading.BrokenBarrierError:
                pass
        return real(password, stored)
    monkeypatch.setattr(service, "verify_password", verify)

    def arm(n):
        gate["barrier"] = threading.Barrier(n)
    return checked, arm


def enrolled(c, clock, email):
    """Turn on 2FA for the signed-in browser `c`. Returns the raw secret."""
    secret_b32 = c.post("/api/auth/2fa/setup", json={"password": PASSWORD}).json()["secret"]
    secret = base64.b32decode(secret_b32 + "=" * (-len(secret_b32) % 8))
    assert c.post("/api/auth/2fa/confirm", json={"code": totp.generate_totp(secret, totp.step_at(mfa._unix(clock[0])))}).status_code == 200
    clock[0] += timedelta(seconds=settings.TOTP_PERIOD_SECONDS)
    return secret


def challenge_for(email):
    try:
        service.login(main.DB_PATH, email=email, password=PASSWORD, client="198.51.100.20")
    except service.MfaRequired as exc:
        return exc.challenge_token
    raise AssertionError("no challenge")


# =====================================================================================================================
# DEFECT-1: concurrent wrong codes on one login challenge
# =====================================================================================================================
def test_defect_1_concurrent_wrong_codes_never_overrun_the_challenge_or_fail_with_a_server_error(client, clock):
    c = browser()
    register(c, "a@example.com")
    enrolled(c, clock, "a@example.com")
    token = challenge_for("a@example.com")
    with db() as conn:
        conn.execute("UPDATE login_challenges SET attempts = ?", (settings.MFA_CHALLENGE_MAX_ATTEMPTS - 1,))   # one attempt left
    results = run_together(6, lambda i: mfa.verify_challenge(main.DB_PATH, token, code="000000", client="198.51.100.20"))
    assert not [r for r in results if isinstance(r, sqlite3.Error)], results                   # no IntegrityError (it was a 500)
    assert sum(isinstance(r, mfa.WrongCredentials) for r in results) == 1                       # exactly one code was checked
    assert all(isinstance(r, (mfa.WrongCredentials, mfa.ChallengeInvalid)) for r in results)
    with db() as conn:
        assert conn.execute("SELECT attempts FROM login_challenges").fetchone()[0] == settings.MFA_CHALLENGE_MAX_ATTEMPTS
        assert conn.execute("SELECT COUNT(*) FROM mfa_failures").fetchone()[0] == 1            # the checked one is counted, the refused ones are not


def test_defect_1_over_http_the_losers_get_the_normal_expired_answer(client, clock):
    c = browser()
    register(c, "a@example.com")
    enrolled(c, clock, "a@example.com")
    token = challenge_for("a@example.com")
    with db() as conn:
        conn.execute("UPDATE login_challenges SET attempts = ?", (settings.MFA_CHALLENGE_MAX_ATTEMPTS - 1,))
    def attempt(_i):
        attacker = TestClient(main.app, headers=dict(FRONTEND_HEADERS), raise_server_exceptions=False)
        attacker.cookies.set(settings.MFA_COOKIE_NAME, token)
        return attacker.post("/api/auth/2fa/verify", json={"code": "000000"}).status_code
    statuses = run_together(5, attempt)
    assert statuses == [401] * 5


def test_a_correct_code_still_works_on_the_last_attempt(client, clock):
    c = browser()
    register(c, "a@example.com")
    secret = enrolled(c, clock, "a@example.com")
    token = challenge_for("a@example.com")
    with db() as conn:
        conn.execute("UPDATE login_challenges SET attempts = ?", (settings.MFA_CHALLENGE_MAX_ATTEMPTS - 1,))
    user, _ = mfa.verify_challenge(main.DB_PATH, token, code=totp.generate_totp(secret, totp.step_at(mfa._unix(clock[0]))))
    assert user.mfa_level == 1
    with db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM mfa_failures").fetchone()[0] == 0              # a success gives its reservation back


# =====================================================================================================================
# DEFECT-2 / DEFECT-3: the in-memory throttles under concurrency
# =====================================================================================================================
def test_defect_2_concurrent_wrong_passwords_cannot_exceed_the_account_limit(client, slow_passwords):
    checked, arm = slow_passwords
    register(browser(), "victim@example.com")
    checked.clear()
    arm(15)
    results = run_together(15, lambda i: service.login(main.DB_PATH, email="victim@example.com", password=f"guess-{i}", client=f"198.51.100.{i + 1}"))
    assert len(checked) == throttle.login_account.limit                                       # was 15
    assert sum(isinstance(r, service.InvalidCredentials) for r in results) == throttle.login_account.limit
    assert all(isinstance(r, (service.InvalidCredentials, service.TooManyAttempts)) for r in results)


def test_defect_2_concurrent_guesses_from_one_address_cannot_exceed_the_address_limit(client, slow_passwords, monkeypatch):
    checked, arm = slow_passwords
    monkeypatch.setenv("LOGIN_IP_MAX_FAILURES", "4")
    checked.clear()
    arm(12)
    results = run_together(12, lambda i: service.login(main.DB_PATH, email=f"nobody{i}@example.com", password="guess", client="198.51.100.9"))
    assert len(checked) == 4 and sum(isinstance(r, service.TooManyAttempts) for r in results) == 8


def test_a_right_password_gives_its_counted_attempt_back(client):
    register(browser(), "a@example.com")
    for _ in range(30):                                                         # more than every limit: successes are never failures
        service.login(main.DB_PATH, email="a@example.com", password=PASSWORD, client="198.51.100.1")
    assert throttle.login_ip.retry_after("198.51.100.1", service.utcnow()) is None
    assert throttle.login_account.retry_after("a@example.com", service.utcnow()) is None


def test_a_throttled_attempt_counts_against_neither_limit(client):
    """Refused before any check, it must not push the other limiter (or the same one) further."""
    register(browser(), "a@example.com")
    for i in range(settings.LOGIN_ACCOUNT_MAX_FAILURES):
        with pytest.raises(service.InvalidCredentials):
            service.login(main.DB_PATH, email="a@example.com", password="wrong", client=f"198.51.100.{i + 1}")
    for _ in range(50):
        with pytest.raises(service.TooManyAttempts):
            service.login(main.DB_PATH, email="a@example.com", password="wrong", client="198.51.100.99")
    assert len(throttle.login_ip._recent("198.51.100.99", service.utcnow())) == 0


def test_defect_3_concurrent_wrong_current_passwords_cannot_exceed_the_change_limit(client, slow_passwords):
    checked, arm = slow_passwords
    c = browser()
    register(c, "a@example.com")
    user = service.authenticate(main.DB_PATH, c.cookies.get(settings.COOKIE_NAME))
    checked.clear()
    arm(12)
    results = run_together(12, lambda i: service.change_password(main.DB_PATH, user, current_password=f"guess-{i}", new_password=NEW_PASSWORD))
    assert len(checked) == throttle.password_change.limit
    assert sum(isinstance(r, service.WrongPassword) for r in results) == throttle.password_change.limit
    assert sum(isinstance(r, service.TooManyAttempts) for r in results) == 12 - throttle.password_change.limit


def test_the_limiter_counts_and_gives_back_exactly():
    lim = throttle.Limiter("LOGIN_ACCOUNT_MAX_FAILURES", "LOGIN_WINDOW_SECONDS")
    now = service.utcnow()
    assert [lim.acquire("k", now) is None for _ in range(settings.LOGIN_ACCOUNT_MAX_FAILURES)] == [True] * settings.LOGIN_ACCOUNT_MAX_FAILURES
    assert lim.acquire("k", now) is not None and len(lim._recent("k", now)) == settings.LOGIN_ACCOUNT_MAX_FAILURES   # refused: not counted
    lim.release("k", now)
    assert len(lim._recent("k", now)) == settings.LOGIN_ACCOUNT_MAX_FAILURES - 1 and lim.acquire("k", now) is None
    lim.release("unknown", now)                                                 # nothing to give back: harmless
    lim.release("k", now - timedelta(seconds=1))                                # a time it never counted: nothing changes
    assert len(lim._recent("k", now)) == settings.LOGIN_ACCOUNT_MAX_FAILURES


def test_the_limiters_check_and_count_are_one_step():
    """acquire holds the lock from the check to the count: a second thread cannot slip between them, however slow the check is."""
    gate = threading.Barrier(2)

    class Slow(throttle.Limiter):
        def retry_after(self, key, now):
            wait = super().retry_after(key, now)
            try:
                gate.wait(0.5)                          # both threads would pass the check here if the lock were not held
            except threading.BrokenBarrierError:
                pass
            return wait
    lim = Slow("LOGIN_ACCOUNT_MAX_FAILURES", "LOGIN_WINDOW_SECONDS")
    now = service.utcnow()
    for _ in range(settings.LOGIN_ACCOUNT_MAX_FAILURES - 1):
        lim.record("k", now)
    results = run_together(2, lambda i: lim.acquire("k", now))
    assert sorted(r is None for r in results) == [False, True] and len(lim._recent("k", now)) == settings.LOGIN_ACCOUNT_MAX_FAILURES


def test_an_address_throttled_attempt_does_not_count_against_the_account(client, monkeypatch):
    monkeypatch.setenv("LOGIN_IP_MAX_FAILURES", "2")
    register(browser(), "a@example.com")
    for i in range(2):
        with pytest.raises(service.InvalidCredentials):
            service.login(main.DB_PATH, email=f"other{i}@example.com", password="wrong", client="198.51.100.5")
    for _ in range(20):
        with pytest.raises(service.TooManyAttempts):
            service.login(main.DB_PATH, email="a@example.com", password="wrong", client="198.51.100.5")
    assert len(throttle.login_account._recent("a@example.com", service.utcnow())) == 0
    service.login(main.DB_PATH, email="a@example.com", password=PASSWORD, client="198.51.100.6")


def test_the_limiter_survives_concurrent_use_at_its_key_limit(monkeypatch):
    """Eviction iterates the key table; another thread changing it meanwhile must not break it."""
    monkeypatch.setattr(settings, "THROTTLE_MAX_KEYS", 20)
    lim = throttle.Limiter("LOGIN_IP_MAX_FAILURES", "LOGIN_WINDOW_SECONDS")
    now = service.utcnow()
    results = run_together(16, lambda i: [lim.acquire(f"{i}-{j}", now) for j in range(300)])
    assert not [r for r in results if isinstance(r, Exception)] and len(lim) <= 20


# =====================================================================================================================
# DEFECT-4: the database-backed second-factor limit under concurrency
# =====================================================================================================================
def test_defect_4_concurrent_wrong_codes_cannot_exceed_the_users_second_factor_limit(client, clock, monkeypatch):
    c = browser()
    register(c, "a@example.com")
    enrolled(c, clock, "a@example.com")
    user_id = uid("a@example.com")
    with db() as conn:                                                          # one failure short of the limit
        for _ in range(settings.MFA_MAX_FAILURES - 1):
            conn.execute("INSERT INTO mfa_failures(user_id, kind, occurred_at) VALUES (?, 'verify', ?)", (user_id, service._fmt(clock[0])))
    tokens = [challenge_for("a@example.com") for _ in range(8)]                 # one fresh challenge each: only the user's limit applies
    checked = []
    real = totp.matching_step

    def counting(*args):
        checked.append(1)
        return real(*args)
    monkeypatch.setattr(totp, "matching_step", counting)
    results = run_together(8, lambda i: mfa.verify_challenge(main.DB_PATH, tokens[i], code="000000"))
    assert len(checked) == 1, results                                           # was every one of them
    assert sum(isinstance(r, mfa.WrongCredentials) for r in results) == 1
    assert sum(isinstance(r, service.TooManyAttempts) for r in results) == 7
    with db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM mfa_failures WHERE user_id = ?", (user_id,)).fetchone()[0] == settings.MFA_MAX_FAILURES


@pytest.mark.parametrize("flow", ["setup", "confirm", "disable", "regenerate", "verify"])
def test_a_second_factor_attempt_that_succeeds_or_stops_early_is_not_a_failure(client, clock, flow):
    """The reservation is given back by every way out but a wrong answer."""
    c = browser()
    register(c, "a@example.com")
    user_id = uid("a@example.com")
    if flow == "setup":
        assert c.post("/api/auth/2fa/setup", json={"password": PASSWORD}).status_code == 200                 # success
        assert c.post("/api/auth/2fa/setup", json={"password": PASSWORD}).status_code == 200
    elif flow == "confirm":
        assert c.post("/api/auth/2fa/confirm", json={"code": "123456"}).status_code == 409                   # no setup: stops early
        enrolled(c, clock, "a@example.com")                                                                 # success
    else:
        assert c.post("/api/auth/2fa/disable", json={"password": PASSWORD, "code": "123456"}).status_code == 409   # not on: stops early
        assert c.post("/api/auth/2fa/recovery-codes", json={"password": PASSWORD, "code": "123456"}).status_code == 409
        secret = enrolled(c, clock, "a@example.com")
        now_code = totp.generate_totp(secret, totp.step_at(mfa._unix(clock[0])))
        if flow == "disable":
            assert c.post("/api/auth/2fa/disable", json={"password": PASSWORD, "code": now_code}).status_code == 200
        elif flow == "regenerate":
            assert c.post("/api/auth/2fa/recovery-codes", json={"password": PASSWORD, "code": now_code}).status_code == 200
        else:
            mfa.verify_challenge(main.DB_PATH, challenge_for("a@example.com"), code=now_code)
    with db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM mfa_failures WHERE user_id = ?", (user_id,)).fetchone()[0] == 0


@pytest.mark.parametrize("flow", ["setup", "confirm", "disable", "regenerate", "verify"])
def test_a_wrong_second_factor_answer_is_counted_once_per_attempt(client, clock, flow):
    c = browser()
    register(c, "a@example.com")
    user_id = uid("a@example.com")
    if flow == "setup":
        r = c.post("/api/auth/2fa/setup", json={"password": "wrong password"})
    elif flow == "confirm":
        c.post("/api/auth/2fa/setup", json={"password": PASSWORD})
        r = c.post("/api/auth/2fa/confirm", json={"code": "000000"})
    else:
        enrolled(c, clock, "a@example.com")
        if flow == "disable":
            r = c.post("/api/auth/2fa/disable", json={"password": PASSWORD, "code": "000000"})
        elif flow == "regenerate":
            r = c.post("/api/auth/2fa/recovery-codes", json={"password": "wrong password", "code": "000000"})
        else:
            with pytest.raises(mfa.WrongCredentials):
                mfa.verify_challenge(main.DB_PATH, challenge_for("a@example.com"), code="000000")
            r = None
    assert r is None or r.status_code == 403
    kind = {"setup": "confirm", "confirm": "confirm", "disable": "disable", "regenerate": "regenerate", "verify": "verify"}[flow]
    with db() as conn:
        assert [tuple(x) for x in conn.execute("SELECT kind FROM mfa_failures WHERE user_id = ?", (user_id,))] == [(kind,)]


def test_the_failure_reservation_is_one_statement_that_refuses_at_the_limit(db_path):
    user, _ = service.create_user(db_path, email="a@example.com", password=PASSWORD, display_name="A", roles=["learner"], with_session=False)
    other, _ = service.create_user(db_path, email="b@example.com", password=PASSWORD, display_name="B", roles=["learner"], with_session=False)
    with connect(db_path) as conn:
        ids = [tf_repo.reserve_failure(conn, user.id, "verify", "2026-10-01 00:00:00", "2026-09-30 23:45:00", 3) for _ in range(5)]
        assert ids[:3] == sorted(ids[:3]) and None not in ids[:3] and ids[3:] == [None, None]
        tf_repo.release_failure(conn, user.id + 1, ids[0])                      # someone else's id: nothing happens
        assert conn.execute("SELECT COUNT(*) FROM mfa_failures").fetchone()[0] == 3
        tf_repo.release_failure(conn, user.id, ids[0])
        assert tf_repo.reserve_failure(conn, user.id, "verify", "2026-10-01 00:00:00", "2026-09-30 23:45:00", 3) is not None
        # failures older than the window neither count nor stay
        assert tf_repo.reserve_failure(conn, user.id, "verify", "2026-10-01 01:00:00", "2026-10-01 00:00:00", 1) is not None
        assert conn.execute("SELECT COUNT(*) FROM mfa_failures").fetchone()[0] == 1
        # another user's failures never count against this one
        assert tf_repo.reserve_failure(conn, other.id, "verify", "2026-10-01 01:00:00", "2026-10-01 00:00:00", 1) is not None


def test_a_challenge_attempt_is_taken_only_while_it_is_live(db_path):
    user, _ = service.create_user(db_path, email="a@example.com", password=PASSWORD, display_name="A", roles=["learner"], with_session=False)
    with connect(db_path) as conn:
        tf_repo.create_challenge(conn, user.id, "c" * 64, "2026-10-01 00:00:00", "2026-10-01 00:05:00")
        cid = conn.execute("SELECT id FROM login_challenges").fetchone()[0]
        assert [tf_repo.take_attempt(conn, cid, "2026-10-01 00:01:00", 2) for _ in range(3)] == [1, 1, 0]
    with connect(db_path) as conn:
        tf_repo.create_challenge(conn, user.id, "d" * 64, "2026-10-01 00:00:00", "2026-10-01 00:05:00")
        cid = conn.execute("SELECT id FROM login_challenges WHERE token_hash = ?", ("d" * 64,)).fetchone()[0]
        assert tf_repo.take_attempt(conn, cid, "2026-10-01 00:05:00", 5) == 0                    # expired
        tf_repo.complete_challenge(conn, cid, "2026-10-01 00:01:00")
        assert tf_repo.take_attempt(conn, cid, "2026-10-01 00:02:00", 5) == 0                    # completed


# =====================================================================================================================
# DEFECT-5: numbers beyond SQLite's range
# =====================================================================================================================
BIG = 10 ** 25


@pytest.fixture
def everyone(client, make_admin):
    learner = browser("198.51.100.30")
    register(learner, "l@example.com")
    learner.put("/api/profile", json={"native_language": "en", "target_language": "hi", "cefr_level": "A1", "date_of_birth": "2000-05-20"})
    make_admin()
    admin = plant_mfa_session(TestClient(main.app, headers=dict(FRONTEND_HEADERS), raise_server_exceptions=False), "admin@example.com")
    learner = TestClient(main.app, headers=dict(FRONTEND_HEADERS), raise_server_exceptions=False, cookies=dict(learner.cookies))
    return learner, admin


def _operations():
    spec = main.app.openapi()
    for path, item in sorted(spec["paths"].items()):
        for method, op in sorted(item.items()):
            yield method.upper(), path, op, spec["components"]["schemas"]


def test_defect_5_no_path_query_or_body_number_is_a_server_error(everyone):
    learner, admin = everyone
    tried, errors = 0, []
    for method, path, op, schemas in _operations():
        if path.startswith("/api/auth/logout"):
            continue                                                            # would sign the sweeping browsers out
        params = op.get("parameters", [])
        int_path = [p["name"] for p in params if p["in"] == "path" and p["schema"].get("type") == "integer"]
        url = path
        for p in params:
            if p["in"] == "path":
                url = url.replace("{" + p["name"] + "}", str(BIG) if p["name"] in int_path else "x")
        bodies = [None]
        ref = op.get("requestBody", {}).get("content", {}).get("application/json", {}).get("schema", {}).get("$ref")
        if ref:
            bodies = [json.dumps({k: BIG}).encode() for k in schemas[ref.split("/")[-1]].get("properties", {})] or [b"{}"]
        queries = [{}] + [{p["name"]: str(BIG)} for p in params if p["in"] == "query"]
        for who in (learner, admin):
            for body in bodies:
                for q in queries:
                    if not int_path and not q and body is None:
                        continue
                    tried += 1
                    r = who.request(method, url, params=q, content=body if body is not None else (b"{}" if method != "GET" else None))
                    if r.status_code >= 500:
                        errors.append((method, path, q, body and body[:40], r.status_code))
    assert tried > 200 and errors == []


@pytest.mark.parametrize("method,url,body", [
    ("GET", f"/api/admin/audit/{BIG}", None), ("GET", f"/api/admin/content/lessons/{BIG}", None), ("GET", f"/api/admin/audit?offset={BIG}", None),
    ("GET", f"/api/admin/audit?entity_id={BIG}", None), ("PATCH", f"/api/admin/content/topics/{BIG}", {}),
])
def test_defect_5_admin_examples_are_a_structured_422(everyone, method, url, body):
    _, admin = everyone
    r = admin.request(method, url, json=body)
    assert r.status_code == 422 and r.json() == {"detail": [{"loc": ["request"], "msg": "A number is out of range", "type": "value_error"}]}
    assert r.headers["x-content-type-options"] == "nosniff" and r.headers["cache-control"] == "no-store"   # the security headers still apply


@pytest.mark.parametrize("method,url,body", [
    ("POST", f"/api/ai/micro-lessons/{BIG}/answer", {}), ("POST", f"/api/ai/recommendations/{BIG}/apply", {}),
    ("POST", "/api/roleplay/sessions", {"situation_id": BIG}), ("POST", "/api/tutor/conversations", {"lesson_id": BIG}),
    ("POST", "/api/listening/1/attempts", {"option_id": BIG}),
])
def test_defect_5_learner_examples_are_a_structured_422(everyone, method, url, body):
    learner, _ = everyone
    r = learner.request(method, url, json=body)
    assert r.status_code == 422 and r.json()["detail"][0]["msg"] == "A number is out of range"


def test_defect_5_other_overflow_errors_stay_server_errors(client, monkeypatch):
    """Only SQLite's integer range is a client error: any other OverflowError is a bug and must not be disguised as a 422."""
    from backend.repositories import catalog
    monkeypatch.setattr(catalog, "list_cities", lambda _p: (_ for _ in ()).throw(OverflowError("math range error")))
    bare = TestClient(main.app, raise_server_exceptions=False)
    assert bare.get("/api/cities").status_code == 500


# =====================================================================================================================
# DEFECT-6: refusals that cost nothing to repeat cannot flood the event table
# =====================================================================================================================
def test_defect_6_a_flood_of_throttled_sign_ins_writes_one_event_a_minute(client, clock):
    c = browser("198.51.100.66")
    for i in range(settings.LOGIN_ACCOUNT_MAX_FAILURES):
        c.post("/api/auth/login", json={"email": "nobody@example.com", "password": f"guess-{i}"})
    for _ in range(200):
        assert c.post("/api/auth/login", json={"email": "nobody@example.com", "password": "guess"}).status_code == 429
    assert event_count("login_throttled") == 1                                  # was 200
    assert event_count("login_failure") == settings.LOGIN_ACCOUNT_MAX_FAILURES  # every CHECKED attempt is still recorded
    clock[0] += timedelta(seconds=events.DENIAL_QUIET_SECONDS)
    c.post("/api/auth/login", json={"email": "nobody@example.com", "password": "guess"})
    assert event_count("login_throttled") == 2                                  # a minute later it is recorded again


def test_defect_6_another_address_still_gets_its_own_event(client, clock):
    for i in range(settings.LOGIN_ACCOUNT_MAX_FAILURES):
        browser().post("/api/auth/login", json={"email": "victim@example.com", "password": f"guess-{i}"})
    for ip in ("198.51.100.71", "198.51.100.72", "198.51.100.71"):
        browser(ip).post("/api/auth/login", json={"email": "victim@example.com", "password": "guess"})
    with db() as conn:
        assert tuple(conn.execute("SELECT COUNT(DISTINCT ip_ref), COUNT(*) FROM security_events WHERE event_type = 'login_throttled'").fetchone()) == (2, 2)


def test_defect_6_dead_login_challenges_cannot_flood_the_table(client):
    c = browser("198.51.100.67")
    for i in range(200):
        c.cookies.set(settings.MFA_COOKIE_NAME, f"forged-{i}")
        assert c.post("/api/auth/2fa/verify", json={"code": "123456"}).status_code == 401
    assert event_count("mfa_failure", "expired_challenge") == 1                 # was 200


def test_defect_6_throttled_second_factor_and_password_change_are_quiet_too(client, clock):
    c = browser()
    register(c, "a@example.com")
    for i in range(settings.PASSWORD_CHANGE_MAX_FAILURES + 30):
        c.post("/api/auth/password", json={"current_password": f"wrong-{i}", "new_password": NEW_PASSWORD})
    assert event_count("password_change_failed") == settings.PASSWORD_CHANGE_MAX_FAILURES and event_count("password_change_throttled") == 1
    with db() as conn:
        for _ in range(settings.MFA_MAX_FAILURES):
            conn.execute("INSERT INTO mfa_failures(user_id, kind, occurred_at) VALUES (?, 'confirm', ?)", (uid("a@example.com"), service._fmt(clock[0])))
    for _ in range(30):
        assert c.post("/api/auth/2fa/setup", json={"password": PASSWORD}).status_code == 429
    assert event_count("mfa_throttled") == 1


def test_defect_6_an_admin_asking_to_turn_off_two_factor_again_and_again_is_recorded_once(client, make_admin):
    make_admin()
    admin = plant_mfa_session(browser(), "admin@example.com")
    for _ in range(25):
        assert admin.post("/api/auth/2fa/disable", json={"password": PASSWORD, "code": "123456"}).status_code == 403
    assert event_count("mfa_disable_failed", "admin_cannot_disable") == 1


def test_the_quiet_writer_keys_on_every_field_and_reads_only_the_time_index(client, monkeypatch, clock):
    a = browser()
    register(a, "a@example.com")
    user_id = uid("a@example.com")
    base = dict(user_id=user_id, reason="throttled", stage="sign_in", client="198.51.100.1")
    events.record_quiet(main.DB_PATH, "mfa_throttled", "denied", **base)
    for change in ({"user_id": None}, {"reason": "wrong_code"}, {"stage": "setup"}, {"client": "198.51.100.2"}):
        events.record_quiet(main.DB_PATH, "mfa_throttled", "denied", **{**base, **change})
    events.record_quiet(main.DB_PATH, "login_throttled", "denied", **base)
    events.record_quiet(main.DB_PATH, "mfa_failure", "failed", **base)
    events.record_quiet(main.DB_PATH, "mfa_throttled", "denied", **base)          # the same again: quiet
    events.record_quiet(main.DB_PATH, "mfa_throttled", "failed", **base)          # same type and fields, another outcome: its own event
    events.record_quiet(main.DB_PATH, "mfa_throttled", "failed", **base)          # ...and quiet after that
    with db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM security_events").fetchone()[0] == 8
        assert [tuple(r) for r in conn.execute("SELECT outcome, COUNT(*) FROM security_events WHERE event_type = 'mfa_throttled' AND user_id = ? "
                                               "AND reason = 'throttled' AND stage = 'sign_in' AND ip_ref = ? GROUP BY outcome ORDER BY outcome",
                                               (user_id, events.ip_ref("198.51.100.1")))] == [("denied", 1), ("failed", 1)]
        plan = " ".join(r[3] for r in conn.execute("""EXPLAIN QUERY PLAN SELECT 1 FROM security_events INDEXED BY idx_security_events_time
                                                      WHERE occurred_at > '' AND event_type = 'x' AND outcome = 'denied' LIMIT 1"""))
    assert "idx_security_events_time" in plan
    with pytest.raises(ValueError):
        events.record_quiet(main.DB_PATH, "not_a_type", "denied")              # a programming error still raises


@pytest.mark.parametrize("bad", [{"event_type": "not_a_type"}, {"outcome": "maybe"}, {"reason": "free text"}, {"stage": "elsewhere"}])
def test_a_malformed_quiet_event_is_refused_before_the_database_is_touched(tmp_path, bad):
    """A programming error raises even where the database is unusable (here: not there at all), and nothing is opened or created."""
    missing = tmp_path / "never-created.db"
    args = {"event_type": "login_throttled", "outcome": "denied", "reason": "throttled", "stage": "sign_in", **bad}
    with pytest.raises(ValueError):
        events.record_quiet(missing, args.pop("event_type"), args.pop("outcome"), **args)
    assert not missing.exists()


def test_the_quiet_writer_swallows_only_transient_errors(client, monkeypatch, caplog):
    def locked(*_a, **_k):
        raise sqlite3.OperationalError("database is locked")
    monkeypatch.setattr(events, "record", locked)
    events.record_quiet(main.DB_PATH, "login_throttled", "denied", reason="throttled", client="198.51.100.1")
    assert "login_throttled not recorded (OperationalError)" in caplog.text and "198.51.100.1" not in caplog.text

    def broken(*_a, **_k):
        raise sqlite3.IntegrityError("CHECK constraint failed")
    monkeypatch.setattr(events, "record", broken)
    with pytest.raises(sqlite3.IntegrityError):
        events.record_quiet(main.DB_PATH, "login_throttled", "denied", reason="throttled")


def test_a_transient_event_failure_never_turns_a_throttle_into_a_server_error(client, monkeypatch):
    for i in range(settings.LOGIN_ACCOUNT_MAX_FAILURES):
        browser().post("/api/auth/login", json={"email": "x@example.com", "password": f"g{i}"})

    def locked(*_a, **_k):
        raise sqlite3.OperationalError("database is locked")
    monkeypatch.setattr(events, "record", locked)
    r = browser().post("/api/auth/login", json={"email": "x@example.com", "password": "g"})
    assert r.status_code == 429 and re.fullmatch(r"\d+", r.headers["retry-after"])
