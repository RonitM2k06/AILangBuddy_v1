"""Phase 14B: the global browser-request (CSRF) guard and the security headers.

The attacker is a bare client: it sends only what a cross-site page could make a browser send (no custom header, a form or text/plain
body, a foreign Origin or Referer), while the victim's session cookie rides along. Every refusal is checked for the right reason (a 403
whose detail says CSRF) AND for its effect: the protected change did not happen."""
import re

import pytest
from fastapi.testclient import TestClient

from backend import main
from backend.db import connect
from backend.security import csrf

from .agekids import profile
from .conftest import FRONTEND_HEADERS, PASSWORD, plant_mfa_session, register
from .spk import audio

SIGNAL = {"X-Requested-With": "XMLHttpRequest"}
JSON_ONLY = {"Content-Type": "application/json"}
BOTH = {**SIGNAL, **JSON_ONLY}
EVIL = "https://evil.example"
SELF = "http://testserver"                                 # the TestClient's own origin (scheme http, Host testserver)
UNSAFE = ("POST", "PUT", "PATCH", "DELETE")


def bare():
    """A browser the attacker controls the page of: no headers of its own."""
    return TestClient(main.app)


def db():
    return connect(main.DB_PATH)


def count(table):
    with db() as conn:
        return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def victim(age=30, email="victim@example.com"):
    """A signed-in learner: a session cookie in a browser that sends nothing extra by itself."""
    c = bare()
    register(c, email)
    assert c.put("/api/profile", json=profile(age), headers=SIGNAL).status_code == 200
    return c


def is_csrf(r):
    return r.status_code == 403 and r.headers["content-type"].startswith("application/json") and r.json()["detail"].startswith("CSRF check failed")


def routes(methods):
    """[(method, path)] for every route the app really serves (from its OpenAPI document), path parameters filled in."""
    out = []
    for path, item in sorted(main.app.openapi()["paths"].items()):
        for m in sorted(item):
            if m.upper() in methods:
                out.append((m.upper(), re.sub(r"\{[^}]+\}", "1", path)))
    return out


# =====================================================================================================================
# A. global coverage
# =====================================================================================================================
def test_the_coverage_tests_iterate_a_real_route_table():
    unsafe = routes(UNSAFE)
    assert len(unsafe) >= 55 and {m for m, _ in unsafe} == {"POST", "PUT", "PATCH", "DELETE"}
    assert any(p.startswith("/api/admin/") for _, p in unsafe) and any(p.startswith("/api/parent/") for _, p in unsafe)


@pytest.mark.parametrize("method,path", routes(UNSAFE))
def test_every_unsafe_route_refuses_an_unsignalled_write_from_a_signed_in_browser(client, method, path):
    c = victim()
    r = c.request(method, path, json={})                                    # a JSON body, but no X-Requested-With
    assert is_csrf(r), (method, path, r.status_code, r.text)


@pytest.mark.parametrize("method,path", routes(UNSAFE))
def test_every_unsafe_route_refuses_an_unsignalled_write_from_anyone(client, method, path):
    r = bare().request(method, path)
    assert is_csrf(r), (method, path, r.status_code, r.text)


@pytest.mark.parametrize("method,path", routes(("GET",)))
def test_safe_requests_are_never_refused_by_the_guard(client, method, path):
    for c in (bare(), victim()):
        r = c.get(path, headers={"Origin": EVIL})                           # even a foreign Origin: reads are not the guard's business
        assert not (r.status_code == 403 and "CSRF" in r.text), (path, r.text)


def test_head_and_options_are_never_refused_by_the_guard(client):
    for method in ("HEAD", "OPTIONS"):
        r = bare().request(method, "/api/profile/parent-link-code", headers={"Origin": EVIL})
        assert not (r.status_code == 403 and "CSRF" in r.text)


def test_there_is_no_cors_grant(client):
    """The guard relies on browsers needing a preflight for the custom header; no route may answer one with a CORS grant."""
    r = bare().options("/api/auth/login", headers={"Origin": EVIL, "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "x-requested-with"})
    assert "access-control-allow-origin" not in r.headers
    r = victim().post("/api/profile/parent-link-code", headers={**BOTH, "Origin": SELF})
    assert "access-control-allow-origin" not in r.headers


# =====================================================================================================================
# B + C. body-less writes and header combinations (the audit's bypass)
# =====================================================================================================================
@pytest.mark.parametrize("headers,ok", [({}, False), (JSON_ONLY, False), (SIGNAL, False), (BOTH, True)])
def test_the_parent_link_code_needs_both_headers(client, headers, ok):
    c = victim()
    before = count("parent_link_codes")
    r = c.post("/api/profile/parent-link-code", headers=headers)
    if ok:
        assert r.status_code == 201 and count("parent_link_codes") == before + 1
    else:
        assert is_csrf(r) and count("parent_link_codes") == before


@pytest.mark.parametrize("path,make", [
    ("/api/profile/parent-link-code", lambda: victim()),
    ("/api/social/friend-code", lambda: victim(age=14, email="teen@example.com")),
    ("/api/daily-plan/generate", lambda: victim(email="plan@example.com")),
    ("/api/auth/logout", lambda: victim(email="out@example.com")),
])
@pytest.mark.parametrize("headers", [{}, JSON_ONLY, SIGNAL])
def test_body_less_writes_have_no_bypass(client, path, make, headers):
    c = make()
    r = c.post(path, headers=headers)
    assert is_csrf(r), (path, headers, r.text)
    assert c.get("/api/auth/me").status_code == 200                     # (for logout: the session survived the forged request)
    assert c.post(path, headers=BOTH).status_code in (200, 201)


@pytest.mark.parametrize("ctype", ["text/plain", "application/x-www-form-urlencoded", "multipart/form-data; boundary=x", "application/jsonp",
                                   "text/json", "audio/webm", ""])
def test_a_json_route_refuses_any_other_content_type_even_with_the_signal(client, ctype):
    c = victim()
    headers = {**SIGNAL, "Content-Type": ctype} if ctype else SIGNAL
    r = c.post("/api/confidence", content=b'{"topic": "food", "score": 5}', headers=headers)
    assert is_csrf(r) and count("confidence_scores") == 0


def test_json_with_a_charset_and_both_headers_is_accepted(client):
    c = victim()
    r = c.post("/api/confidence", content=b'{"topic": "food", "score": 5}', headers={**SIGNAL, "Content-Type": "application/json; charset=utf-8"})
    assert r.status_code == 201


@pytest.mark.parametrize("ctype", ["Application/JSON", "APPLICATION/JSON; charset=UTF-8"])
def test_the_json_media_type_is_matched_case_insensitively(client, ctype):
    """Media types are case-insensitive (RFC 9110); the guard must not refuse a correct one spelled differently."""
    r = victim().post("/api/confidence", content=b'{"topic": "food", "score": 5}', headers={**SIGNAL, "Content-Type": ctype})
    assert r.status_code == 201


@pytest.mark.parametrize("value", ["", "xmlhttprequest", "XMLHttpRequest ", "fetch", "1", "XMLHttpRequest2"])
def test_only_the_exact_header_value_counts(client, value):
    r = victim().post("/api/profile/parent-link-code", headers={"X-Requested-With": value, **JSON_ONLY})
    assert is_csrf(r)


# =====================================================================================================================
# D. Origin and Referer
# =====================================================================================================================
@pytest.mark.parametrize("origin", [EVIL, "null", "https://testserver", "http://testserver:8080", "http://testserver.evil.example", "http://evil.testserver",
                                    "testserver", ""])
def test_a_foreign_origin_is_refused_even_with_both_headers(client, origin):
    c = victim()
    before = count("parent_link_codes")
    r = c.post("/api/profile/parent-link-code", headers={**BOTH, "Origin": origin})
    assert is_csrf(r) and "did not come from this site" in r.json()["detail"] and count("parent_link_codes") == before


@pytest.mark.parametrize("origin", [SELF, "HTTP://TESTSERVER", SELF + "/"])
def test_the_own_origin_is_accepted(client, origin):
    assert victim().post("/api/profile/parent-link-code", headers={**BOTH, "Origin": origin}).status_code == 201


def test_no_origin_is_not_a_bypass(client):
    c = victim()
    assert is_csrf(c.post("/api/profile/parent-link-code"))                   # neither Origin nor the headers: refused
    assert c.post("/api/profile/parent-link-code", headers=BOTH).status_code == 201   # no Origin (non-browser or old browser), headers: fine


@pytest.mark.parametrize("referer", [EVIL + "/page", "https://testserver/", "not a url", "javascript:alert(1)", "http://testserver.evil.example/x"])
def test_a_foreign_referer_is_refused_when_there_is_no_origin(client, referer):
    r = victim().post("/api/profile/parent-link-code", headers={**BOTH, "Referer": referer})
    assert is_csrf(r) and "did not come from this site" in r.json()["detail"]


def test_an_own_referer_is_accepted(client):
    assert victim().post("/api/profile/parent-link-code", headers={**BOTH, "Referer": SELF + "/#/profile"}).status_code == 201


def test_origin_wins_over_referer(client):
    c = victim()
    assert c.post("/api/profile/parent-link-code", headers={**BOTH, "Origin": SELF, "Referer": EVIL + "/x"}).status_code == 201
    assert is_csrf(c.post("/api/profile/parent-link-code", headers={**BOTH, "Origin": EVIL, "Referer": SELF + "/x"}))


def test_trusted_origins_are_matched_case_insensitively(client, monkeypatch):
    monkeypatch.setenv("TRUSTED_ORIGINS", "https://Lingo.Example")
    assert victim().post("/api/profile/parent-link-code", headers={**BOTH, "Origin": "https://lingo.example"}).status_code == 201


def test_a_non_web_referer_never_counts_even_if_such_an_origin_were_trusted(client, monkeypatch):
    """Only http(s) Referers name a web origin. Even a misconfigured TRUSTED_ORIGINS entry with another scheme is never matched by one."""
    monkeypatch.setenv("TRUSTED_ORIGINS", "ftp://lingo.example, https://lingo.example")
    c = victim()
    assert is_csrf(c.post("/api/profile/parent-link-code", headers={**BOTH, "Referer": "ftp://lingo.example/file"}))
    assert c.post("/api/profile/parent-link-code", headers={**BOTH, "Referer": "https://lingo.example/#/profile"}).status_code == 201


def test_https_is_accepted_for_the_same_host_when_cookie_secure_says_the_site_is_https(client, monkeypatch):
    c = victim()
    assert is_csrf(c.post("/api/profile/parent-link-code", headers={**BOTH, "Origin": "https://testserver"}))
    monkeypatch.setenv("COOKIE_SECURE", "1")
    assert c.post("/api/profile/parent-link-code", headers={**BOTH, "Origin": "https://testserver"}).status_code == 201
    assert is_csrf(c.post("/api/profile/parent-link-code", headers={**BOTH, "Origin": EVIL}))


def test_trusted_origins_replace_the_derived_origin(client, monkeypatch):
    c = victim()
    monkeypatch.setenv("TRUSTED_ORIGINS", "https://lingo.example, https://www.lingo.example/")
    assert c.post("/api/profile/parent-link-code", headers={**BOTH, "Origin": "https://lingo.example"}).status_code == 201
    assert c.post("/api/profile/parent-link-code", headers={**BOTH, "Origin": "https://www.lingo.example"}).status_code == 201
    assert is_csrf(c.post("/api/profile/parent-link-code", headers={**BOTH, "Origin": SELF}))       # the derived origin no longer counts
    assert is_csrf(c.post("/api/profile/parent-link-code", headers={**BOTH, "Origin": EVIL}))


def test_a_spoofed_host_header_cannot_be_used_to_match_a_foreign_origin_from_a_browser(client):
    """A browser always sends the real Host of the site it talks to; matching Origin against Host therefore only ever accepts this site.
    (A non-browser client that forges both is not a CSRF victim: it has no one else's cookie.)"""
    assert csrf.own_origins("http", "testserver") == frozenset({"http://testserver"})
    assert csrf.own_origins("http", None) == frozenset()
    assert csrf.rejection("POST", "/api/x", {"x-requested-with": "XMLHttpRequest", "content-type": "application/json", "origin": SELF}, "http") is not None


# =====================================================================================================================
# E. the raw audio upload
# =====================================================================================================================
@pytest.fixture
def speaker(client, monkeypatch):
    monkeypatch.setenv("STT_PROVIDER", "mock")
    c = victim()
    s = c.post("/api/speaking/sessions", json={}, headers=SIGNAL)
    assert s.status_code == 201
    return c, s.json()["session"]["id"]


def recording_url(sid):
    return f"/api/speaking/sessions/{sid}/recording?duration_ms=1500"


def stage(c, sid):
    return c.get(f"/api/speaking/sessions/{sid}").json()["session"]["stage"]


def test_a_legitimate_recording_upload_still_works(speaker):
    c, sid = speaker
    r = c.post(recording_url(sid), content=audio("namaste"), headers={**SIGNAL, "Content-Type": "audio/webm;codecs=opus"})
    assert r.status_code == 200 and stage(c, sid) == "recorded"


@pytest.mark.parametrize("headers", [{"Content-Type": "audio/webm"}, {"Content-Type": "audio/webm", "X-Requested-With": "fetch"}])
def test_a_recording_without_the_signal_is_refused_and_nothing_is_stored(speaker, headers, tmp_path):
    c, sid = speaker
    r = c.post(recording_url(sid), content=audio("namaste"), headers=headers)
    assert is_csrf(r) and stage(c, sid) == "created"
    assert not list((tmp_path / "recordings").glob("*")) if (tmp_path / "recordings").exists() else True


def test_the_recording_route_still_does_its_own_media_check(speaker):
    c, sid = speaker
    r = c.post(recording_url(sid), content=audio("namaste"), headers={**SIGNAL, "Content-Type": "video/webm"})
    assert r.status_code == 415 and stage(c, sid) == "created"


def test_a_recording_from_a_foreign_origin_is_refused(speaker):
    c, sid = speaker
    r = c.post(recording_url(sid), content=audio("namaste"), headers={**SIGNAL, "Content-Type": "audio/webm", "Origin": EVIL})
    assert is_csrf(r) and stage(c, sid) == "created"


def test_the_raw_body_exception_is_exactly_the_recording_upload():
    raw = [(m, p) for m, p in routes(UNSAFE) if csrf.is_raw_media(m, p)]
    assert raw == [("POST", "/api/speaking/sessions/1/recording")]
    for path in ("/api/speaking/sessions/1/recording/x", "/api/speaking/sessions/abc/recording", "/x/api/speaking/sessions/1/recording",
                 "/api/speaking/sessions/1/transcribe"):
        assert not csrf.is_raw_media("POST", path)
    assert not csrf.is_raw_media("PUT", "/api/speaking/sessions/1/recording")


@pytest.mark.parametrize("path,method", [("/api/speaking/sessions/1/transcribe", "POST"), ("/api/profile", "PUT"), ("/api/state/x", "PUT")])
def test_a_non_json_body_is_refused_everywhere_else(client, path, method):
    r = victim().request(method, path, content=b"\x1a\x45\xdf\xa3rest", headers={**SIGNAL, "Content-Type": "audio/webm"})
    assert is_csrf(r)


# =====================================================================================================================
# F. admin
# =====================================================================================================================
def admin_browser(make_admin):
    make_admin("root@example.com")
    c = bare()
    assert c.post("/api/auth/login", json={"email": "root@example.com", "password": PASSWORD}, headers=SIGNAL).status_code == 200
    return plant_mfa_session(c, "root@example.com")                           # Phase 14D: the admin API needs a second factor


def test_admin_writes_need_the_signal_and_the_router_guard_is_still_there(client, make_admin):
    c = admin_browser(make_admin)
    body = {"slug": "csrf-check", "title": "T", "language": "hi", "cefr": "A1", "topic": "greetings"}
    assert is_csrf(c.post("/api/admin/content/lessons", json=body))
    assert is_csrf(c.post("/api/admin/content/lessons", json=body, headers={**BOTH, "Origin": EVIL}))
    assert c.post("/api/admin/content/lessons", json=body, headers=BOTH).status_code != 403
    # the admin router keeps its own csrf_guard dependency as a second layer: test_admin_security.py checks it is on every admin route


# =====================================================================================================================
# G. authentication
# =====================================================================================================================
def test_register_login_and_logout_work_with_the_signal(client):
    c = bare()
    assert c.post("/api/auth/register", json={"email": "new@example.com", "password": PASSWORD, "display_name": "N"}, headers=SIGNAL).status_code == 201
    assert c.post("/api/auth/logout", headers=BOTH).status_code == 200 and c.get("/api/auth/me").status_code == 401
    assert c.post("/api/auth/login", json={"email": "new@example.com", "password": PASSWORD}, headers={**SIGNAL, "Origin": SELF}).status_code == 200
    assert c.get("/api/auth/me").status_code == 200


def test_a_cross_site_registration_creates_nothing(client):
    r = bare().post("/api/auth/register", data={"email": "x@example.com", "password": PASSWORD, "display_name": "X"}, headers={"Origin": EVIL})
    assert is_csrf(r)
    with db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM users WHERE email = 'x@example.com'").fetchone()[0] == 0


def test_login_csrf_cannot_sign_a_victim_into_the_attackers_account(client):
    register(bare(), "attacker@example.com")
    c = bare()
    r = c.post("/api/auth/login", content=b'{"email": "attacker@example.com", "password": "correct horse battery"}', headers={"Content-Type": "text/plain", "Origin": EVIL})
    assert is_csrf(r) and "llb_session" not in r.headers.get("set-cookie", "") and c.get("/api/auth/me").status_code == 401


# =====================================================================================================================
# 10. attacks, end to end
# =====================================================================================================================
def test_attack_1_cross_site_form_post(client):
    c = victim()
    r = c.post("/api/confidence", data={"topic": "food", "score": "99"}, headers={"Origin": EVIL})
    assert is_csrf(r) and count("confidence_scores") == 0


def test_attack_2_cross_site_body_less_post(client):
    c = victim()
    r = c.post("/api/profile/parent-link-code", headers={"Origin": EVIL})
    assert is_csrf(r) and count("parent_link_codes") == 0


def test_attack_3_cross_site_json_as_text_plain(client):
    c = victim()
    r = c.put("/api/profile", content=b'{"native_language": "en", "target_language": "hi", "cefr_level": "A2", "date_of_birth": "1990-01-01"}',
              headers={"Content-Type": "text/plain", "Origin": EVIL})
    assert is_csrf(r) and c.get("/api/profile").json()["profile"]["cefr_level"] == "A1"


def test_attack_4_malicious_origin_with_forged_headers(client):
    c = victim()
    r = c.post("/api/confidence", json={"topic": "food", "score": 99}, headers={**SIGNAL, "Origin": EVIL})
    assert is_csrf(r) and count("confidence_scores") == 0


def test_attack_5_forged_referer(client):
    c = victim()
    r = c.post("/api/confidence", json={"topic": "food", "score": 99}, headers={**SIGNAL, "Referer": EVIL + "/lure.html"})
    assert is_csrf(r) and count("confidence_scores") == 0


def test_attack_6_direct_call_without_the_signal(client):
    c = victim()
    r = c.post("/api/confidence", json={"topic": "food", "score": 99})
    assert is_csrf(r) and count("confidence_scores") == 0


def test_attack_7_raw_audio_without_the_signal(speaker):
    c, sid = speaker
    r = c.post(recording_url(sid), content=audio("x"), headers={"Content-Type": "audio/webm", "Origin": EVIL})
    assert is_csrf(r) and stage(c, sid) == "created"


def test_attack_8_admin_write_without_the_signal(client, make_admin):
    c = admin_browser(make_admin)
    r = c.post("/api/admin/content/topics", json={"slug": "pwned", "name": "P", "icon": "p"}, headers={"Origin": EVIL})
    assert is_csrf(r)
    with db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM topics WHERE slug = 'pwned'").fetchone()[0] == 0


def test_attack_9_the_same_origin_frontend_request_succeeds(client):
    c = victim()
    r = c.post("/api/confidence", json={"topic": "food", "score": 40}, headers={**BOTH, "Origin": SELF, "Referer": SELF + "/#/plan"})
    assert r.status_code == 201 and count("confidence_scores") == 1


# =====================================================================================================================
# H + I. security headers and HSTS
# =====================================================================================================================
EXPECTED = {"x-content-type-options": "nosniff", "x-frame-options": "DENY", "referrer-policy": "strict-origin-when-cross-origin",
            "content-security-policy": "object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'"}


def responses(make_admin):
    signed_in = victim()
    admin = admin_browser(make_admin)
    anon = bare()
    return {
        "html page": anon.get("/"),
        "static file": anon.get("/static/app.js"),
        "public api": anon.get("/api/health"),
        "authenticated api": signed_in.get("/api/auth/me"),
        "admin api": admin.get("/api/admin/audit"),
        "api 404": anon.get("/api/no-such-route"),
        "page 404": anon.get("/no-such-page"),
        "405": anon.delete("/api/health", headers=BOTH),
        "401": anon.get("/api/profile"),
        "422": signed_in.put("/api/profile", json={"nope": 1}, headers=BOTH),
        "csrf 403": signed_in.post("/api/profile/parent-link-code"),
    }


def test_every_response_carries_the_security_headers(client, make_admin):
    for name, r in responses(make_admin).items():
        for header, value in EXPECTED.items():
            assert r.headers.get(header) == value, (name, header, r.headers.get(header))


def test_no_hsts_over_plain_http_development(client, make_admin):
    for name, r in responses(make_admin).items():
        assert "strict-transport-security" not in r.headers, name


def test_hsts_when_cookie_secure_says_the_site_is_https(client, monkeypatch):
    monkeypatch.setenv("COOKIE_SECURE", "1")
    for path in ("/", "/api/health", "/static/app.js"):
        assert bare().get(path).headers["strict-transport-security"] == "max-age=31536000; includeSubDomains"


def test_hsts_when_the_request_arrives_over_https(client):
    https = TestClient(main.app, base_url="https://testserver")
    assert https.get("/").headers["strict-transport-security"] == "max-age=31536000; includeSubDomains"
    assert https.post("/api/auth/logout", headers={**BOTH, "Origin": "https://testserver"}).status_code == 200


# =====================================================================================================================
# J. cache
# =====================================================================================================================
def test_security_sensitive_responses_are_never_cached(client, make_admin):
    c = victim()
    handle = c.get("/api/auth/me").json()["user"]["handle"]
    parent = bare()
    register(parent, "parent@example.com", role="parent")
    admin = admin_browser(make_admin)
    login = bare().post("/api/auth/login", json={"email": "victim@example.com", "password": PASSWORD}, headers=SIGNAL)
    checks = {
        "login": login, "register": bare().post("/api/auth/register", json={"email": "r@example.com", "password": PASSWORD, "display_name": "R"}, headers=SIGNAL),
        "me": c.get("/api/auth/me"), "state": c.get(f"/api/state/{handle}"), "profile": c.get("/api/profile"), "lessons": c.get("/api/lessons"),
        "speaking": c.get("/api/speaking/sessions"), "gamification": c.get("/api/gamification"), "parent": parent.get("/api/parent/children"),
        "admin": admin.get("/api/admin/audit"), "admin users": admin.get("/api/admin/users"), "401": bare().get("/api/profile"),
        "csrf 403": c.post("/api/profile/parent-link-code"), "logout": c.post("/api/auth/logout", headers=BOTH),
    }
    for name, r in checks.items():
        assert r.headers.get("cache-control") == "no-store", (name, r.status_code, r.headers.get("cache-control"))


def test_pages_and_static_files_keep_their_caching(client):
    for path in ("/", "/static/app.js", "/static/styles.css"):
        assert "no-store" not in bare().get(path).headers.get("cache-control", "")


# =====================================================================================================================
# the frontend sends the signal from its central helpers
# =====================================================================================================================
def test_the_frontend_helpers_send_the_signal_on_every_write():
    root = main.ROOT / "frontend"
    profile_js, admin_js, voice_js, engine_js = [(root / f).read_text() for f in ("profile.js", "admin.js", "voice.js", "engine.js")]
    assert 'if (method !== "GET") { opts.headers["Content-Type"] = "application/json"; opts.headers["X-Requested-With"] = "XMLHttpRequest"; }' in profile_js
    assert 'opts.headers["X-Requested-With"] = "XMLHttpRequest"' in admin_js
    assert '"X-Requested-With": "XMLHttpRequest" }, body: blob' in voice_js
    assert engine_js.count("headers: WRITE_HEADERS") == 2 and '"X-Requested-With": "XMLHttpRequest"' in engine_js
    others = [p.name for p in root.glob("*.js") if p.name not in ("profile.js", "admin.js", "voice.js", "engine.js") and re.search(r"fetch\([^)]*method", p.read_text())]
    assert others == [], others                                              # every other module writes through LBApi.api
    assert FRONTEND_HEADERS == BOTH                                         # the test "browsers" send what the frontend sends
