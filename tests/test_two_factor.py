"""Phase 14D: TOTP two-factor authentication: AES-GCM secret storage, RFC 6238 codes, the local QR code, setup and confirmation, recovery
codes, the sign-in challenge, replay and brute-force limits, admin enforcement, turning it off, new recovery codes, and the attacks.
Time is a controlled clock; codes are computed from the secret the setup returned, exactly as an authenticator app would."""
import base64
import json
import re
import threading
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from backend import main, settings
from backend.auth import mfa, service, totp, totp_crypto
from backend.db import connect

from .conftest import FRONTEND_HEADERS, PASSWORD, TEST_TOTP_ENC_KEY, plant_mfa_session, register
from .qr_decode import decode

SIGNAL = {"X-Requested-With": "XMLHttpRequest"}
OTHER_KEY = base64.urlsafe_b64encode(b"another-32-byte-key-for-testing!").decode().rstrip("=")


# =====================================================================================================================
# helpers
# =====================================================================================================================
@pytest.fixture
def clock(monkeypatch):
    now = [service.utcnow().replace(microsecond=0)]
    monkeypatch.setattr(service, "utcnow", lambda: now[0])
    return now


def tick(clock, steps=1):
    clock[0] += timedelta(seconds=settings.TOTP_PERIOD_SECONDS * steps)


def unix(clock):
    return mfa._unix(clock[0])


def code(secret_b32, clock, offset=0):
    secret = base64.b32decode(secret_b32 + "=" * (-len(secret_b32) % 8))
    return totp.generate_totp(secret, totp.step_at(unix(clock)) + offset)


def browser(ip="203.0.113.50"):
    return TestClient(main.app, headers=dict(FRONTEND_HEADERS), client=(ip, 40000))


def db():
    return connect(main.DB_PATH)


def user(email="a@example.com", role="learner"):
    c = browser()
    register(c, email, role=role)
    return c


def setup(c, password=PASSWORD):
    return c.post("/api/auth/2fa/setup", json={"password": password})


def enroll(c, clock, password=PASSWORD):
    """Set up and confirm 2FA in browser `c`. Returns (secret, recovery codes). The confirm code's step is spent; the clock moves on."""
    s = setup(c, password)
    assert s.status_code == 200, s.text
    secret = s.json()["secret"]
    r = c.post("/api/auth/2fa/confirm", json={"code": code(secret, clock)})
    assert r.status_code == 200, r.text
    tick(clock)
    return secret, r.json()["recovery_codes"]


def password_login(c, email="a@example.com", password=PASSWORD):
    return c.post("/api/auth/login", json={"email": email, "password": password})


def verify(c, **body):
    return c.post("/api/auth/2fa/verify", json=body)


def mfa_login(email, secret, clock, ip="198.51.100.60"):
    c = browser(ip)
    assert password_login(c, email).json() == {"mfa_required": True}
    r = verify(c, code=code(secret, clock))
    assert r.status_code == 200, r.text
    tick(clock)
    return c


def me(c):
    return c.get("/api/auth/me").status_code


def session_row(token):
    with db() as conn:
        row = conn.execute("SELECT mfa_level, auth_method FROM sessions WHERE token_hash = ?", (service._hash_token(token),)).fetchone()
    return tuple(row) if row else None


def uid(email):
    with db() as conn:
        return conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()[0]


def dump():
    with db() as conn:
        return "\n".join(conn.iterdump())


def cookie_header(r, name):
    return next((h for h in r.headers.get_list("set-cookie") if h.startswith(name + "=")), None)


# =====================================================================================================================
# AES-GCM secret storage
# =====================================================================================================================
def test_secrets_round_trip_with_a_fresh_nonce_each_time():
    secret = totp.new_secret()
    (c1, n1), (c2, n2) = totp_crypto.encrypt(secret, 7), totp_crypto.encrypt(secret, 7)
    assert n1 != n2 and c1 != c2 and len(n1) == 12 and len(c1) == 36 and secret not in c1
    assert totp_crypto.decrypt(c1, n1, 7) == secret == totp_crypto.decrypt(c2, n2, 7)


@pytest.mark.parametrize("tamper", ["ciphertext", "tag", "nonce", "short_nonce", "user", "key"])
def test_any_change_is_detected(monkeypatch, tamper):
    secret = totp.new_secret()
    ct, nonce, user_id = *totp_crypto.encrypt(secret, 7), 7
    if tamper == "ciphertext":
        ct = bytes([ct[0] ^ 1]) + ct[1:]
    elif tamper == "tag":
        ct = ct[:-1] + bytes([ct[-1] ^ 1])
    elif tamper == "nonce":
        nonce = bytes([nonce[0] ^ 1]) + nonce[1:]
    elif tamper == "short_nonce":
        nonce = nonce[:11]
    elif tamper == "user":
        user_id = 8                                                         # a ciphertext moved onto another account
    elif tamper == "key":
        monkeypatch.setenv("TOTP_ENC_KEY", OTHER_KEY)
    with pytest.raises(totp_crypto.SecretUnreadable) as err:
        totp_crypto.decrypt(ct, nonce, user_id)
    assert secret.hex() not in str(err.value) and TEST_TOTP_ENC_KEY not in str(err.value)


@pytest.mark.parametrize("value", [None, "", "short", "A" * 42, "A" * 44, "A" * 45, "!" * 43, "A" * 42 + "+", "A" * 42 + "/",
                                   base64.b64encode(b"x" * 31).decode(), base64.b64encode(b"x" * 33).decode()])
def test_a_missing_or_malformed_key_fails_closed(monkeypatch, value):
    if value is None:
        monkeypatch.delenv("TOTP_ENC_KEY", raising=False)
    else:
        monkeypatch.setenv("TOTP_ENC_KEY", value)
    assert not totp_crypto.available()
    with pytest.raises(totp_crypto.KeyUnavailable) as err:
        totp_crypto.encrypt(b"x" * 20, 1)
    assert value is None or not value or value not in str(err.value)


def test_the_key_may_carry_its_padding(monkeypatch):
    monkeypatch.setenv("TOTP_ENC_KEY", TEST_TOTP_ENC_KEY + "=")
    assert len(totp_crypto.load_key()) == 32


# =====================================================================================================================
# TOTP (RFC 6238)
# =====================================================================================================================
RFC = b"12345678901234567890"


@pytest.mark.parametrize("t,expected", [(59, "94287082"), (1111111109, "07081804"), (1111111111, "14050471"), (1234567890, "89005924"),
                                        (2000000000, "69279037"), (20000000000, "65353130")])
def test_rfc_6238_sha1_vectors(t, expected):
    assert totp.generate_totp(RFC, totp.step_at(t), digits=8) == expected
    assert totp.generate_totp(RFC, totp.step_at(t)) == expected[-6:]      # six digits are the low six of the same value


def test_steps_are_whole_30_second_windows():
    assert [totp.step_at(t) for t in (0, 29, 30, 59, 60)] == [0, 0, 1, 1, 2]


@pytest.mark.parametrize("offset,ok", [(-2, False), (-1, True), (0, True), (1, True), (2, False)])
def test_one_step_of_drift_is_allowed_either_way(offset, ok):
    t = 1_800_000_015
    c = totp.generate_totp(RFC, totp.step_at(t) + offset)
    assert totp.verify_totp(RFC, c, t) is ok
    assert totp.matching_step(RFC, c, t) == (totp.step_at(t) + offset if ok else None)


@pytest.mark.parametrize("bad", ["12345", "1234567", " 287082", "287082 ", "28708a", "٢٨٧٠٨٢", "２８７０８２", "", None, 287082, "28 7082", "+28708"])
def test_only_six_ascii_digits_count(bad):
    assert totp.normalize_code(bad) is None and not totp.verify_totp(RFC, bad, 59)


def test_a_wrong_code_is_refused():
    t = 1_800_000_015
    right = totp.generate_totp(RFC, totp.step_at(t))
    wrong = str((int(right) + 1) % 1_000_000).zfill(6)
    assert totp.verify_totp(RFC, right, t) and not totp.verify_totp(RFC, wrong, t)


def test_secrets_are_160_random_bits():
    secrets_ = {totp.new_secret() for _ in range(50)}
    assert len(secrets_) == 50 and all(len(s) == 20 for s in secrets_)


def test_the_otpauth_uri():
    uri = totp.otpauth_uri(RFC, "a b+c@example.com")
    assert uri == ("otpauth://totp/LingoBuddy:a%20b%2Bc%40example.com?secret=GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ&issuer=LingoBuddy"
                   "&algorithm=SHA1&digits=6&period=30")


# =====================================================================================================================
# the QR code
# =====================================================================================================================
def test_the_setup_qr_encodes_exactly_the_otpauth_uri(client):
    c = user()
    body = setup(c).json()
    assert decode(body["qr"]) == body["otpauth_uri"]
    assert set("".join(body["qr"]["modules"])) == {"0", "1"} and len(body["qr"]["modules"]) == body["qr"]["size"]


@pytest.mark.parametrize("account", ["x@example.com", "ünï cödé@example.com", "a" * 100 + "@example.com"])
def test_the_qr_encoder_round_trips_any_account(account):
    from backend.auth import qr
    uri = totp.otpauth_uri(totp.new_secret(), account)
    assert decode(qr.matrix(uri)) == uri


def test_setup_still_works_if_the_qr_code_cannot_be_drawn(client, clock, monkeypatch):
    from backend.auth import qr
    monkeypatch.setattr(qr, "matrix", lambda text: (_ for _ in ()).throw(ValueError("too long")))
    c = user()
    body = setup(c).json()
    assert body["qr"] is None and body["secret"]
    assert c.post("/api/auth/2fa/confirm", json={"code": code(body["secret"], clock)}).status_code == 200


def test_the_vendored_encoder_is_the_recorded_upstream_file():
    import hashlib
    path = main.ROOT / "backend" / "vendor" / "qrcodegen.py"
    text = path.read_bytes()
    assert hashlib.sha256(text).hexdigest() == "b089855caf16185c61421ea4927c1b213cf9468940d71fa8ab11ef83662dcc84"
    assert b"Copyright (c) Project Nayuki. (MIT License)" in text and b"import requests" not in text and b"urllib" not in text
    readme = (path.parent / "README.md").read_text()
    assert "b089855caf16185c61421ea4927c1b213cf9468940d71fa8ab11ef83662dcc84" in readme and "MIT" in readme


# =====================================================================================================================
# setup and confirmation
# =====================================================================================================================
def test_setup_needs_a_session_and_the_password(client):
    assert browser().post("/api/auth/2fa/setup", json={"password": PASSWORD}).status_code == 401
    c = user()
    assert setup(c, "not my password").status_code == 403
    assert c.post("/api/auth/2fa/setup", json={}).status_code == 422
    with db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM two_factor_credentials").fetchone()[0] == 0


def test_setup_returns_only_the_setup_material_and_stores_only_ciphertext(client):
    c = user()
    r = setup(c)
    body = r.json()
    assert r.status_code == 200 and set(body) == {"secret", "otpauth_uri", "qr", "expires_in_seconds"}
    assert re.fullmatch(r"[A-Z2-7]{32}", body["secret"]) and body["expires_in_seconds"] == 600
    assert f"secret={body['secret']}" in body["otpauth_uri"] and "issuer=LingoBuddy" in body["otpauth_uri"]
    assert str(uid("a@example.com")) not in body["otpauth_uri"].split("?")[0].replace("LingoBuddy:", "")
    raw = base64.b32decode(body["secret"])
    with db() as conn:
        row = conn.execute("SELECT * FROM two_factor_credentials").fetchone()
    assert row["status"] == "pending" and len(row["secret_ciphertext"]) == 36 and len(row["secret_nonce"]) == 12
    assert raw not in row["secret_ciphertext"] and body["secret"] not in dump() and raw.hex() not in dump()
    assert c.get("/api/auth/2fa").json()["pending"] is True and "secret" not in c.get("/api/auth/2fa").text


def test_a_second_setup_replaces_the_first(client, clock):
    c = user()
    first = setup(c).json()["secret"]
    second = setup(c).json()["secret"]
    assert first != second
    assert c.post("/api/auth/2fa/confirm", json={"code": code(first, clock)}).status_code == 403
    assert c.post("/api/auth/2fa/confirm", json={"code": code(second, clock)}).status_code == 200
    with db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM two_factor_credentials").fetchone()[0] == 1


def test_a_setup_expires(client, clock):
    c = user()
    secret = setup(c).json()["secret"]
    clock[0] += timedelta(seconds=settings.TOTP_SETUP_SECONDS)
    assert c.post("/api/auth/2fa/confirm", json={"code": code(secret, clock)}).status_code == 409
    assert c.get("/api/auth/2fa").json() == {**c.get("/api/auth/2fa").json(), "pending": False, "enabled": False}


def test_setup_is_refused_without_an_encryption_key(client, monkeypatch):
    c = user()
    monkeypatch.delenv("TOTP_ENC_KEY")
    r = setup(c)
    assert r.status_code == 503 and c.get("/api/auth/2fa").json()["available"] is False
    with db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM two_factor_credentials").fetchone()[0] == 0


def test_a_wrong_confirmation_code_turns_nothing_on(client, clock):
    c = user()
    secret = setup(c).json()["secret"]
    wrong = str((int(code(secret, clock)) + 5) % 1_000_000).zfill(6)
    r = c.post("/api/auth/2fa/confirm", json={"code": wrong})
    assert r.status_code == 403 and r.json() == {"detail": "That is not correct"}
    assert c.get("/api/auth/2fa").json()["enabled"] is False
    with db() as conn:
        assert conn.execute("SELECT kind FROM mfa_failures").fetchall()[0][0] == "confirm"


def test_confirming_turns_it_on_issues_recovery_codes_once_and_upgrades_this_session(client, clock):
    c = user()
    other = browser("198.51.100.9")
    assert password_login(other).status_code == 200                          # another device, signed in with the password before
    before = c.cookies.get("llb_session")
    secret = setup(c).json()["secret"]
    r = c.post("/api/auth/2fa/confirm", json={"code": code(secret, clock)})
    codes = r.json()["recovery_codes"]
    assert r.status_code == 200 and set(r.json()) == {"ok", "recovery_codes"} and len(codes) == 10 and len(set(codes)) == 10
    assert all(re.fullmatch(r"[A-Z2-7]{4}(-[A-Z2-7]{4}){3}", x) for x in codes)
    assert me(with_token(before)) == 401 and session_row(c.cookies.get("llb_session")) == (1, "password+totp")
    assert session_row(other.cookies.get("llb_session")) == (0, "password")          # an older session does not become an MFA one
    status = c.get("/api/auth/2fa").json()
    assert status["enabled"] is True and status["recovery_codes_remaining"] == 10 and "recovery_codes" not in status
    text = dump()
    assert all(x not in text and x.replace("-", "") not in text for x in codes)
    with db() as conn:
        hashes = [r[0] for r in conn.execute("SELECT code_hash FROM recovery_codes")]
    assert len(hashes) == 10 and all(re.fullmatch(r"[0-9a-f]{64}", h) for h in hashes)
    assert setup(c).status_code == 409                                       # the secret is never handed out again


def with_token(t):
    c = browser("203.0.113.99")
    c.cookies.set("llb_session", t)
    return c


# =====================================================================================================================
# signing in
# =====================================================================================================================
def test_an_account_without_2fa_signs_in_as_before(client):
    user()
    c = browser()
    r = password_login(c)
    assert r.status_code == 200 and "user" in r.json() and me(c) == 200
    assert session_row(c.cookies.get("llb_session")) == (0, "password")


def test_a_correct_password_for_an_mfa_account_opens_only_a_challenge(client, clock):
    secret, _ = enroll(user(), clock)
    c = browser("198.51.100.61")
    r = password_login(c)
    assert r.status_code == 200 and r.json() == {"mfa_required": True}
    assert "llb_session" not in r.headers.get("set-cookie", "").split("llb_mfa_challenge")[0]
    assert c.cookies.get("llb_session") is None and me(c) == 401
    header = cookie_header(r, "llb_mfa_challenge")
    assert "HttpOnly" in header and "SameSite=lax" in header and "Path=/api/auth/2fa" in header and "Max-Age=300" in header and "Secure" not in header
    token = c.cookies.get("llb_mfa_challenge")
    assert token not in r.text
    with db() as conn:
        assert conn.execute("SELECT token_hash FROM login_challenges").fetchone()[0] == service._hash_token(token)
    assert token not in dump()


def test_the_challenge_cookie_is_secure_when_configured(client, clock, monkeypatch):
    secret, _ = enroll(user(), clock)
    monkeypatch.setenv("COOKIE_SECURE", "1")
    assert "Secure" in cookie_header(password_login(browser("198.51.100.62")), "llb_mfa_challenge")


def test_the_right_code_creates_an_mfa_session_and_clears_the_challenge(client, clock):
    secret, _ = enroll(user(), clock)
    c = browser("198.51.100.63")
    password_login(c)
    r = verify(c, code=code(secret, clock))
    assert r.status_code == 200 and set(r.json()) == {"user"} and r.json()["user"]["email"] == "a@example.com"
    assert session_row(c.cookies.get("llb_session")) == (1, "password+totp") and me(c) == 200
    assert 'llb_mfa_challenge=""' in cookie_header(r, "llb_mfa_challenge") and "Path=/api/auth/2fa" in cookie_header(r, "llb_mfa_challenge")
    with db() as conn:
        assert conn.execute("SELECT completed_at FROM login_challenges").fetchone()[0] is not None


def test_a_wrong_code_leaves_the_browser_signed_out_and_counts(client, clock):
    secret, _ = enroll(user(), clock)
    c = browser("198.51.100.64")
    password_login(c)
    wrong = str((int(code(secret, clock)) + 1) % 1_000_000).zfill(6)
    r = verify(c, code=wrong)
    assert r.status_code == 401 and r.json() == {"detail": "That code is not correct"} and me(c) == 401
    with db() as conn:
        assert conn.execute("SELECT attempts FROM login_challenges").fetchone()[0] == 1


def test_five_wrong_codes_end_the_challenge(client, clock):
    secret, _ = enroll(user(), clock)
    c = browser("198.51.100.65")
    password_login(c)
    for _ in range(settings.MFA_CHALLENGE_MAX_ATTEMPTS):
        assert verify(c, code="000000").status_code == 401
    r = verify(c, code=code(secret, clock))
    assert r.status_code == 401 and "expired" in r.json()["detail"] and me(c) == 401


def test_an_expired_challenge_is_refused(client, clock):
    secret, _ = enroll(user(), clock)
    c = browser("198.51.100.66")
    password_login(c)
    clock[0] += timedelta(seconds=settings.MFA_CHALLENGE_SECONDS)
    r = verify(c, code=code(secret, clock))
    assert r.status_code == 401 and "expired" in r.json()["detail"] and me(c) == 401


def test_a_completed_challenge_cannot_be_used_again(client, clock):
    secret, _ = enroll(user(), clock)
    c = browser("198.51.100.67")
    password_login(c)
    challenge = c.cookies.get("llb_mfa_challenge")
    assert verify(c, code=code(secret, clock)).status_code == 200
    tick(clock)
    replay = browser("198.51.100.68")
    replay.cookies.set("llb_mfa_challenge", challenge, path="/api/auth/2fa")
    r = verify(replay, code=code(secret, clock))
    assert r.status_code == 401 and replay.cookies.get("llb_session") is None


def test_a_code_cannot_be_used_twice(client, clock):
    secret, _ = enroll(user(), clock)
    used = code(secret, clock)
    c1 = browser("198.51.100.69")
    password_login(c1)
    assert verify(c1, code=used).status_code == 200
    c2 = browser("198.51.100.70")
    password_login(c2)
    assert verify(c2, code=used).status_code == 401                         # same step: replay
    assert verify(c2, code=code(secret, clock, -1)).status_code == 401       # an earlier step is never accepted after a later one
    assert verify(c2, code=code(secret, clock, +1)).status_code == 200       # the next step is


def test_concurrent_use_of_one_code_succeeds_once(client, clock):
    secret, _ = enroll(user(), clock)
    browsers = [browser(f"198.51.100.{80 + i}") for i in range(4)]
    for b in browsers:
        password_login(b)
    the_code, barrier, results = code(secret, clock), threading.Barrier(4), []

    def go(b):
        barrier.wait()
        results.append(verify(b, code=the_code).status_code)

    threads = [threading.Thread(target=go, args=(b,)) for b in browsers]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert sorted(results) == [200, 401, 401, 401]


def test_signing_in_with_a_code_revokes_the_session_this_browser_had(client, clock):
    secret, _ = enroll(user(), clock)
    register(browser("198.51.100.71"), "b@example.com")
    c = browser("198.51.100.72")
    password_login(c, "b@example.com")
    b_token = c.cookies.get("llb_session")
    password_login(c)
    verify(c, code=code(secret, clock))
    assert me(with_token(b_token)) == 401 and c.get("/api/auth/me").json()["user"]["email"] == "a@example.com"


# =====================================================================================================================
# recovery codes
# =====================================================================================================================
def test_a_recovery_code_signs_in_once(client, clock):
    _, codes = enroll(user(), clock)
    c = browser("198.51.100.73")
    password_login(c)
    r = verify(c, recovery_code=codes[0].lower().replace("-", " "))       # case, dashes and spaces do not matter
    assert r.status_code == 200 and session_row(c.cookies.get("llb_session")) == (1, "password+recovery")
    assert c.get("/api/auth/2fa").json()["recovery_codes_remaining"] == 9
    again = browser("198.51.100.74")
    password_login(again)
    assert verify(again, recovery_code=codes[0]).status_code == 401
    assert verify(again, recovery_code=codes[1]).status_code == 200


@pytest.mark.parametrize("bad", ["AAAA-AAAA-AAAA-AAAA", "1234", "", "AAAA-AAAA-AAAA-AAA1", "x" * 32])
def test_a_wrong_recovery_code_is_refused_and_counted(client, clock, bad):
    enroll(user(), clock)
    c = browser("198.51.100.75")
    password_login(c)
    assert verify(c, recovery_code=bad).status_code in (401, 422) and me(c) == 401


def test_a_recovery_code_of_another_account_does_not_work(client, clock):
    _, a_codes = enroll(user(), clock)
    enroll(user("b@example.com"), clock)
    c = browser("198.51.100.76")
    password_login(c, "b@example.com")
    assert verify(c, recovery_code=a_codes[0]).status_code == 401 and me(c) == 401
    with db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM recovery_codes WHERE used_at IS NOT NULL").fetchone()[0] == 0


def test_concurrent_use_of_one_recovery_code_succeeds_once(client, clock):
    _, codes = enroll(user(), clock)
    browsers = [browser(f"198.51.100.{90 + i}") for i in range(4)]
    for b in browsers:
        password_login(b)
    barrier, results = threading.Barrier(4), []

    def go(b):
        barrier.wait()
        results.append(verify(b, recovery_code=codes[3]).status_code)

    threads = [threading.Thread(target=go, args=(b,)) for b in browsers]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert sorted(results) == [200, 401, 401, 401]


def test_the_verify_body_takes_exactly_one_factor(client, clock):
    secret, codes = enroll(user(), clock)
    c = browser("198.51.100.77")
    password_login(c)
    assert verify(c).status_code == 422
    assert verify(c, code=code(secret, clock), recovery_code=codes[0]).status_code == 422
    assert c.post("/api/auth/2fa/verify", json={"code": code(secret, clock), "user_id": 1}).status_code == 422


# =====================================================================================================================
# database-backed throttling
# =====================================================================================================================
def test_wrong_codes_across_challenges_are_limited_per_user_in_the_database(client, clock):
    secret, _ = enroll(user(), clock)
    for _ in range(settings.MFA_MAX_FAILURES // settings.MFA_CHALLENGE_MAX_ATTEMPTS):
        c = browser("198.51.100.78")
        password_login(c)
        for _ in range(settings.MFA_CHALLENGE_MAX_ATTEMPTS):
            assert verify(c, code="000000").status_code == 401
    service.reset_throttle()                                                 # the in-memory limiters reset (as on a restart)...
    clock[0] += timedelta(seconds=100)
    c = browser("198.51.100.79")
    assert password_login(c).json() == {"mfa_required": True}
    r = verify(c, code=code(secret, clock))                                  # ...the database-backed one does not: even the right code waits
    assert r.status_code == 429 and int(r.headers["retry-after"]) == settings.MFA_WINDOW_SECONDS - 100 and me(c) == 401
    clock[0] += timedelta(seconds=settings.MFA_WINDOW_SECONDS - 100)
    assert verify(c, code=code(secret, clock)).status_code == 401            # this challenge has expired by now...
    assert mfa_login("a@example.com", secret, clock) is not None             # ...but a fresh sign-in works again: nothing is locked forever


def test_the_limit_is_per_user(client, clock):
    a_secret, _ = enroll(user(), clock)
    b_secret, _ = enroll(user("b@example.com"), clock)
    for _ in range(2):
        c = browser("198.51.100.85")
        password_login(c)
        for _ in range(settings.MFA_CHALLENGE_MAX_ATTEMPTS):
            verify(c, code="000000")
    assert mfa_login("b@example.com", b_secret, clock) is not None


def test_failed_confirmations_count_too(client, clock):
    c = user()
    setup(c)
    for _ in range(settings.MFA_MAX_FAILURES):
        assert c.post("/api/auth/2fa/confirm", json={"code": "000000"}).status_code == 403
    assert c.post("/api/auth/2fa/confirm", json={"code": "000000"}).status_code == 429
    assert setup(c).status_code == 429


# =====================================================================================================================
# admins
# =====================================================================================================================
def admin_routes():
    return [p for p, item in main.app.openapi()["paths"].items() if p.startswith("/api/admin") and "get" in item and "{" not in p]


def make_admin_browser(make_admin, email="root@example.com", ip="198.51.100.100"):
    make_admin(email)
    c = browser(ip)
    r = password_login(c, email)
    assert r.status_code == 200 and "user" in r.json()                      # no 2FA yet: a password session
    return c


def test_an_admin_without_a_second_factor_reaches_no_admin_route(client, make_admin):
    c = make_admin_browser(make_admin)
    routes = admin_routes()
    assert len(routes) >= 15
    for path in routes:
        r = c.get(path)
        assert r.status_code == 403 and r.json()["detail"]["code"] == "mfa_required", path
    assert c.post("/api/admin/content/topics", json={"slug": "t", "name": "T", "icon": "t"}).status_code == 403
    assert me(c) == 200                                                      # the session itself is fine: only the admin API is closed


def test_an_admin_with_a_second_factor_reaches_every_admin_route(client, make_admin):
    c = make_admin_browser(make_admin)
    plant_mfa_session(c, "root@example.com")
    for path in admin_routes():
        assert c.get(path).status_code == 200, path


def test_an_admin_enrols_and_the_console_opens_in_that_browser(client, clock, make_admin):
    c = make_admin_browser(make_admin)
    old_device = browser("198.51.100.101")
    password_login(old_device, "root@example.com")
    assert c.get("/api/admin/dashboard").status_code == 403
    secret, _ = enroll(c, clock)
    assert c.get("/api/admin/dashboard").status_code == 200
    assert old_device.get("/api/admin/dashboard").json()["detail"]["code"] == "mfa_required"   # a session from before enrolment stays password-only
    fresh = browser("198.51.100.102")
    assert password_login(fresh, "root@example.com").json() == {"mfa_required": True}
    assert fresh.get("/api/admin/dashboard").status_code == 401
    assert verify(fresh, code=code(secret, clock)).status_code == 200 and fresh.get("/api/admin/dashboard").status_code == 200


@pytest.mark.parametrize("trick", [{"headers": {"X-MFA-Level": "1", "X-Auth-Method": "password+totp", "X-Admin": "1"}},
                                   {"params": {"mfa_level": "1", "mfa": "true"}},
                                   {"cookies": {"mfa_level": "1", "llb_mfa": "1"}}])
def test_nothing_in_the_request_can_raise_the_mfa_level(client, make_admin, trick):
    c = make_admin_browser(make_admin)
    for k, v in trick.get("cookies", {}).items():
        c.cookies.set(k, v)
    r = c.get("/api/admin/dashboard", headers=trick.get("headers"), params=trick.get("params"))
    assert r.status_code == 403 and r.json()["detail"]["code"] == "mfa_required"


@pytest.mark.parametrize("demo", ["1", "0"])
def test_demo_mode_does_not_open_the_admin_api(client, make_admin, monkeypatch, demo):
    monkeypatch.setenv("DEMO_MODE", demo)
    c = make_admin_browser(make_admin)
    assert c.get("/api/admin/dashboard").status_code == 403
    assert browser().get("/api/admin/dashboard").status_code == 401


def test_learners_and_parents_with_2fa_are_still_not_admins(client, clock):
    for email, role in (("l@example.com", "learner"), ("p@example.com", "parent")):
        c = user(email, role)
        enroll(c, clock)
        r = c.get("/api/admin/dashboard")
        assert r.status_code == 403 and r.json()["detail"] == "Insufficient permissions"


def test_admins_cannot_turn_2fa_off_even_with_a_valid_code(client, clock, make_admin):
    c = make_admin_browser(make_admin)
    secret, codes = enroll(c, clock)
    for factor in ({"code": code(secret, clock)}, {"recovery_code": codes[0]}):
        r = c.post("/api/auth/2fa/disable", json={"password": PASSWORD, **factor})
        assert r.status_code == 403 and "Administrators" in r.json()["detail"]
    assert c.get("/api/auth/2fa").json()["enabled"] is True and c.get("/api/admin/dashboard").status_code == 200
    assert c.get("/api/auth/2fa").json()["recovery_codes_remaining"] == 10


def test_admins_can_get_new_recovery_codes(client, clock, make_admin):
    c = make_admin_browser(make_admin)
    secret, old = enroll(c, clock)
    r = c.post("/api/auth/2fa/recovery-codes", json={"password": PASSWORD, "code": code(secret, clock)})
    assert r.status_code == 200 and len(r.json()["recovery_codes"]) == 10 and not set(r.json()["recovery_codes"]) & set(old)


# =====================================================================================================================
# turning it off, new recovery codes
# =====================================================================================================================
def test_turning_it_off_needs_the_password_and_a_second_factor(client, clock):
    c = user()
    secret, codes = enroll(c, clock)
    assert c.post("/api/auth/2fa/disable", json={"password": PASSWORD}).status_code == 422
    assert c.post("/api/auth/2fa/disable", json={"password": PASSWORD, "code": "000000"}).status_code == 403
    assert c.post("/api/auth/2fa/disable", json={"password": "wrong password", "code": code(secret, clock)}).status_code == 403
    assert c.get("/api/auth/2fa").json()["enabled"] is True
    r = c.post("/api/auth/2fa/disable", json={"password": PASSWORD, "code": code(secret, clock)})   # the code was not burnt above
    assert r.status_code == 200 and c.get("/api/auth/2fa").json()["enabled"] is False


def test_turning_it_off_with_a_recovery_code_ends_every_other_session(client, clock):
    c = user()
    secret, codes = enroll(c, clock)
    other = mfa_login("a@example.com", secret, clock)
    before = c.cookies.get("llb_session")
    assert c.post("/api/auth/2fa/disable", json={"password": PASSWORD, "recovery_code": codes[0]}).status_code == 200
    assert me(other) == 401 and me(with_token(before)) == 401 and me(c) == 200
    assert session_row(c.cookies.get("llb_session")) == (0, "password")
    with db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM recovery_codes").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM two_factor_credentials").fetchone()[0] == 0
    assert "user" in password_login(browser("198.51.100.110")).json()       # signing in is password-only again


def test_new_recovery_codes_replace_the_old_ones_and_are_shown_once(client, clock):
    c = user()
    secret, old = enroll(c, clock)
    assert c.post("/api/auth/2fa/recovery-codes", json={"password": PASSWORD, "code": "000000"}).status_code == 403
    r = c.post("/api/auth/2fa/recovery-codes", json={"password": PASSWORD, "code": code(secret, clock)})
    new = r.json()["recovery_codes"]
    assert r.status_code == 200 and set(r.json()) == {"recovery_codes"} and len(new) == 10
    for spent, ok in ((old[0], False), (new[0], True)):
        b = browser("198.51.100.111")
        password_login(b)
        assert (verify(b, recovery_code=spent).status_code == 200) is ok
    assert all(x not in c.get("/api/auth/2fa").text for x in new)


def test_new_recovery_codes_need_2fa_on(client):
    c = user()
    assert c.post("/api/auth/2fa/recovery-codes", json={"password": PASSWORD, "code": "123456"}).status_code == 409
    assert browser().post("/api/auth/2fa/recovery-codes", json={"password": PASSWORD, "code": "123456"}).status_code == 401


# =====================================================================================================================
# the attacks
# =====================================================================================================================
def mfa_user(clock, email="a@example.com"):
    c = user(email)
    return enroll(c, clock)


def test_attack_1_skipping_the_second_step(client, clock):
    mfa_user(clock)
    c = browser("192.0.2.1")
    password_login(c)
    assert me(c) == 401 and c.get("/api/auth/sessions").status_code == 401 and c.get("/api/profile").status_code == 401
    c.cookies.set("llb_session", c.cookies.get("llb_mfa_challenge"))        # the challenge token is no session
    assert me(c) == 401


def test_attack_2_and_3_forging_mfa_level_or_a_role_in_the_body(client, clock, make_admin):
    mfa_user(clock)
    c = browser("192.0.2.2")
    for extra in ({"mfa_level": 1}, {"role": "admin"}, {"auth_method": "password+totp"}, {"verified": True}):
        assert c.post("/api/auth/login", json={"email": "a@example.com", "password": PASSWORD, **extra}).status_code == 422
    assert me(c) == 401


def test_attack_4_calling_the_admin_api_with_only_the_password(client, make_admin):
    c = make_admin_browser(make_admin)
    assert c.get("/api/admin/users").json()["detail"]["code"] == "mfa_required"


def test_attack_6_brute_forcing_codes(client, clock):
    secret, _ = mfa_user(clock)
    tried = 0
    for _ in range(4):
        c = browser("192.0.2.6")
        password_login(c)
        for guess in range(settings.MFA_CHALLENGE_MAX_ATTEMPTS):
            r = verify(c, code=str(guess).zfill(6))
            tried += r.status_code in (401, 429)
    assert tried == 20
    with db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM mfa_failures").fetchone()[0] <= settings.MFA_MAX_FAILURES   # beyond the limit nothing is even checked


def test_attack_8_brute_forcing_recovery_codes(client, clock):
    mfa_user(clock)
    c = browser("192.0.2.8")
    password_login(c)
    for _ in range(settings.MFA_CHALLENGE_MAX_ATTEMPTS):
        assert verify(c, recovery_code="AAAA-BBBB-CCCC-DDDD").status_code == 401
    assert verify(c, recovery_code="AAAA-BBBB-CCCC-DDDD").status_code == 401 and "expired" in verify(c, code="123456").json()["detail"]


def test_attack_11_a_challenge_moved_to_another_browser_still_needs_its_owners_code(client, clock):
    a_secret, _ = mfa_user(clock)
    b_secret, _ = mfa_user(clock, "b@example.com")
    c = browser("192.0.2.11")
    password_login(c)                                                        # a's challenge
    thief = browser("192.0.2.12")
    thief.cookies.set("llb_mfa_challenge", c.cookies.get("llb_mfa_challenge"), path="/api/auth/2fa")
    assert verify(thief, code=code(b_secret, clock)).status_code == 401      # b's valid code does not complete a's challenge


@pytest.mark.parametrize("forged", ["", "x", "A" * 43, "garbage-value", "a" * 200])
def test_attack_12_and_13_modified_or_guessed_challenges(client, clock, forged):
    secret, _ = mfa_user(clock)
    c = browser("192.0.2.13")
    password_login(c)
    real = c.cookies.get("llb_mfa_challenge")
    c.cookies.set("llb_mfa_challenge", forged or real[:-1] + ("A" if real[-1] != "A" else "B"), path="/api/auth/2fa")
    r = verify(c, code=code(secret, clock))
    assert r.status_code == 401 and "expired" in r.json()["detail"] and c.cookies.get("llb_session") is None


@pytest.mark.parametrize("tamper", ["ciphertext", "nonce", "key"])
def test_attack_14_to_16_a_tampered_secret_or_changed_key_fails_closed_but_recovery_still_works(client, clock, monkeypatch, tamper):
    secret, codes = mfa_user(clock)
    with db() as conn:
        row = conn.execute("SELECT secret_ciphertext, secret_nonce FROM two_factor_credentials").fetchone()
    if tamper == "key":
        monkeypatch.setenv("TOTP_ENC_KEY", OTHER_KEY)
    else:
        # an enabled credential's secret cannot be edited through SQL (trigger); simulate an attacker with raw file access by rebuilding it
        col, val = ("secret_ciphertext", bytes([row[0][0] ^ 1]) + row[0][1:]) if tamper == "ciphertext" else ("secret_nonce", bytes([row[1][0] ^ 1]) + row[1][1:])
        with db() as conn:
            conn.execute("DROP TRIGGER two_factor_enabled_secret_is_fixed")
            conn.execute(f"UPDATE two_factor_credentials SET {col} = ?", (val,))
    c = browser("192.0.2.14")
    password_login(c)
    r = verify(c, code=code(secret, clock))
    assert r.status_code == 503 and me(c) == 401 and secret not in r.text
    assert verify(c, recovery_code=codes[0]).status_code == 200              # recovery codes do not depend on the key


def test_attack_17_to_19_disabling_or_regenerating_without_the_second_factor(client, clock, make_admin):
    c = user()
    secret, _ = enroll(c, clock)
    assert c.post("/api/auth/2fa/disable", json={"password": PASSWORD}).status_code == 422
    assert c.post("/api/auth/2fa/recovery-codes", json={"password": PASSWORD}).status_code == 422
    assert c.post("/api/auth/2fa/recovery-codes", json={"password": PASSWORD, "code": "999999"}).status_code == 403
    admin = make_admin_browser(make_admin)
    a_secret, _ = enroll(admin, clock)
    assert admin.post("/api/auth/2fa/disable", json={"password": PASSWORD, "code": code(a_secret, clock)}).status_code == 403


def test_attack_20_and_21_old_admin_sessions_never_pass(client, clock, make_admin):
    c = make_admin_browser(make_admin)
    stale = browser("192.0.2.20")
    password_login(stale, "root@example.com")
    enroll(c, clock)
    assert stale.get("/api/admin/learners").json()["detail"]["code"] == "mfa_required"


@pytest.mark.parametrize("path", ["/api/auth/2fa/setup", "/api/auth/2fa/confirm", "/api/auth/2fa/verify", "/api/auth/2fa/disable", "/api/auth/2fa/recovery-codes"])
@pytest.mark.parametrize("raw", [b"{not json", b"[]", b'"code"', b"null", b""])
def test_attack_23_malformed_json_is_a_clean_422(client, path, raw):
    c = user()
    r = c.post(path, content=raw)
    assert r.status_code == 422 and isinstance(r.json()["detail"], list)


@pytest.mark.parametrize("path", ["/api/auth/2fa/setup", "/api/auth/2fa/confirm", "/api/auth/2fa/verify", "/api/auth/2fa/disable", "/api/auth/2fa/recovery-codes"])
def test_attack_24_every_new_write_is_behind_the_csrf_guard(client, path):
    victim = TestClient(main.app)
    register(victim, "v@example.com")
    for headers in ({}, {"Content-Type": "application/json"}, {**SIGNAL, "Content-Type": "application/json", "Origin": "https://evil.example"}):
        r = victim.post(path, content=b'{"password": "x", "code": "123456"}', headers=headers)
        assert r.status_code == 403 and r.json()["detail"].startswith("CSRF check failed"), (path, headers)


def test_attack_25_one_account_cannot_manage_anothers_2fa(client, clock):
    a = user()
    secret, _ = enroll(a, clock)
    b = user("b@example.com")
    assert b.get("/api/auth/2fa").json()["enabled"] is False
    assert b.post("/api/auth/2fa/disable", json={"password": PASSWORD, "code": code(secret, clock)}).status_code == 409
    assert b.post("/api/auth/2fa/confirm", json={"code": code(secret, clock)}).status_code == 409
    assert a.get("/api/auth/2fa").json()["enabled"] is True


def test_no_secret_ever_appears_in_a_later_response(client, clock):
    c = user()
    s = setup(c).json()
    confirm = c.post("/api/auth/2fa/confirm", json={"code": code(s["secret"], clock)})
    codes = confirm.json()["recovery_codes"]
    tick(clock)
    later = [c.get("/api/auth/2fa"), c.get("/api/auth/me"), c.get("/api/auth/sessions"), password_login(browser("192.0.2.30"))]
    for r in later:
        assert s["secret"] not in r.text and all(x not in r.text for x in codes)
        for word in ("ciphertext", "nonce", "code_hash", "token_hash", "TOTP_ENC_KEY", TEST_TOTP_ENC_KEY):
            assert word not in r.text
