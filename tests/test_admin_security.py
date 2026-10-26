"""Phase 13B: who may call /api/admin/*, and how a state-changing call must look. Every test is driven from the application's real route table,
so a route added in any later step is covered automatically (and an unguarded one fails the enumeration test)."""
import inspect
import re

import pytest
from fastapi.routing import APIRoute

from backend import main
from backend.admin.security import admin_only

from . import adm
from .adm import Api, CSRF, admin, demo_browser, register_browser  # noqa: F401  (fixtures)


def _route_objects():
    """Every APIRoute the application can serve: the ones on the app itself plus those of each router module (FastAPI 0.14x includes routers lazily,
    so the app's own route list does not show them)."""
    import importlib
    import pkgutil

    import backend.routers as pkg

    found = [r for r in main.app.routes if isinstance(r, APIRoute)]
    for info in pkgutil.iter_modules(pkg.__path__):
        router = getattr(importlib.import_module(f"backend.routers.{info.name}"), "router", None)
        found += [r for r in getattr(router, "routes", []) if isinstance(r, APIRoute)]
    return found


def admin_routes():
    """The admin routes the app really serves: the mounted paths come from the OpenAPI document, each matched to its route object."""
    mounted = {(path, method.upper()) for path, item in main.app.openapi()["paths"].items() if path.startswith("/api/admin") for method in item}
    objects = _route_objects()
    routes = []
    for path, method in sorted(mounted):
        match = [r for r in objects if r.path == path and method in r.methods]
        assert match, f"{method} {path} is served but no router module defines it"
        routes.append(match[0])
    return routes


def endpoints():
    """[(method, path)] for every admin route, with each path parameter filled in."""
    out = set()
    for r in admin_routes():
        for m in r.methods - {"HEAD", "OPTIONS"}:
            out.add((m, re.sub(r"\{[^}]+\}", "1", r.path)))
    return sorted(out)


def dependency_calls(dependant):
    yield dependant.call
    for d in dependant.dependencies:
        yield from dependency_calls(d)


def required_roles(route):
    """The role tuples of every require_roles() guard in the route's dependency tree."""
    found = []
    for call in dependency_calls(route.dependant):
        if getattr(call, "__qualname__", "").startswith("require_roles."):
            found.append(inspect.getclosurevars(call).nonlocals["roles"])
    return found


# ---------- the route table ----------
def test_there_are_admin_routes_to_check():
    paths = {r.path for r in admin_routes()}
    assert "/api/admin/audit" in paths and "/api/admin/users" in paths and len(endpoints()) >= 3


@pytest.mark.parametrize("route", admin_routes(), ids=lambda r: r.path + str(sorted(r.methods - {"HEAD"})))
def test_every_admin_route_requires_exactly_the_admin_role(route):
    guards = required_roles(route)
    assert guards and set(guards) == {("admin",)}, f"{route.path} must sit behind require_roles('admin') and nothing weaker"


def test_the_shared_guard_is_the_admin_role_plus_a_second_factor():
    """Phase 14D: admin_only = the admin role (unchanged) AND the session's mfa_level >= 1."""
    role_dependency = inspect.signature(admin_only).parameters["user"].default.dependency
    assert inspect.getclosurevars(role_dependency).nonlocals["roles"] == ("admin",)
    assert "mfa_level" in inspect.getsource(admin_only)


def test_every_admin_route_but_the_legacy_one_also_runs_the_csrf_guard():
    for r in admin_routes():
        names = [getattr(c, "__name__", "") for c in dependency_calls(r.dependant)]
        if r.path == "/api/admin/users":
            continue                                    # the Phase 3 read-only listing: a GET, unchanged
        assert "csrf_guard" in names, r.path


def test_only_one_admin_router_module_defines_the_new_routes():
    modules = {r.endpoint.__module__ for r in admin_routes()}
    assert modules == {"backend.routers.admin"}                             # since Phase 14E the account listing is here too


# ---------- authentication and authorization, every route x every caller ----------
@pytest.mark.parametrize("method,path", endpoints())
def test_unauthenticated_callers_get_401(client, method, path):
    r = getattr(Api(), method.lower())(path)
    assert r.status_code == 401, (method, path, r.text)


@pytest.mark.parametrize("method,path", endpoints())
def test_learners_and_parents_get_403(client, method, path):
    for api in (register_browser("learner", "l@example.com"), register_browser("parent", "p@example.com")):
        r = getattr(api, method.lower())(path)
        assert r.status_code == 403 and r.json()["detail"] == "Insufficient permissions", (method, path, r.text)


@pytest.mark.parametrize("method,path", endpoints())
def test_the_demo_learner_gets_403_even_with_a_session(client, method, path):
    assert getattr(demo_browser(), method.lower())(path).status_code == 403


@pytest.mark.parametrize("method,path", endpoints())
def test_anonymous_demo_mode_does_not_open_admin_routes(client, method, path):
    """DEMO_MODE (on by default in tests) lets the prototype run anonymously; it must not reach the admin API."""
    assert getattr(Api(), method.lower())(path).status_code == 401


@pytest.mark.parametrize("method,path", endpoints())
def test_admin_is_never_refused_by_the_guards(admin, method, path):
    r = getattr(admin, method.lower())(path)
    assert r.status_code not in (401, 403), (method, path, r.status_code, r.text)


def test_a_learner_cannot_become_admin_by_sending_a_role(client):
    r = client.post("/api/auth/register", json={"email": "x@example.com", "password": "correct horse battery", "display_name": "X", "role": "admin"})
    assert r.status_code == 422
    assert client.post("/api/auth/register", json={"email": "y@example.com", "password": "correct horse battery", "display_name": "Y", "roles": ["admin"]}).status_code == 422


def test_the_legacy_admin_user_list_still_works_for_admins_only(admin, client):
    assert admin.get("/api/admin/users").status_code == 200
    assert register_browser("learner", "l@example.com").get("/api/admin/users").status_code == 403


# ---------- CSRF: state-changing calls ----------
def write_endpoints():
    return [(m, p) for m, p in endpoints() if m in ("POST", "PUT", "PATCH", "DELETE")]


def test_the_csrf_tests_below_cover_a_real_set_of_write_routes():
    """They iterate the route table, so they only mean something while writes exist: pin a floor so a refactor cannot silently empty them."""
    writes = write_endpoints()
    assert len(writes) >= 18
    assert {m for m, _ in writes} == {"POST", "PATCH", "PUT"}


def test_there_is_no_delete_route_anywhere_in_the_admin_api():
    """Locked design: the CMS deletes nothing. Content is archived, never removed."""
    assert not [(m, p) for m, p in endpoints() if m == "DELETE"]
    assert "DELETE" not in {m for r in admin_routes() for m in r.methods}


@pytest.mark.parametrize("method,path", write_endpoints())
def test_a_write_without_the_csrf_header_is_rejected(admin, method, path):
    r = getattr(admin.c, method.lower())(path, json={})
    assert r.status_code == 403 and "CSRF" in r.json()["detail"], (method, path, r.text)


@pytest.mark.parametrize("value", ["", "xmlhttprequest", "XMLHttpRequest ", "fetch", "true", "1", "XMLHttpRequest2"])
@pytest.mark.parametrize("method,path", write_endpoints())
def test_a_write_with_the_wrong_csrf_header_is_rejected(admin, method, path, value):
    r = getattr(admin.c, method.lower())(path, json={}, headers={"X-Requested-With": value})
    assert r.status_code == 403 and "CSRF" in r.json()["detail"], (method, path, value)


@pytest.mark.parametrize("ctype", ["text/plain", "application/x-www-form-urlencoded", "multipart/form-data; boundary=x", "application/jsonp", "text/json", ""])
@pytest.mark.parametrize("method,path", write_endpoints())
def test_a_write_that_is_not_json_is_rejected_even_with_the_header(admin, method, path, ctype):
    headers = {**CSRF, "Content-Type": ctype} if ctype else dict(CSRF)
    r = getattr(admin.c, method.lower())(path, content=b"{}", headers=headers)
    assert r.status_code == 403 and "CSRF" in r.json()["detail"], (method, path, ctype)


@pytest.mark.parametrize("method,path", write_endpoints())
def test_a_write_with_both_headers_passes_the_csrf_check(admin, method, path):
    r = getattr(admin, method.lower())(path)
    assert r.status_code != 403 or "CSRF" not in r.text, (method, path)


@pytest.mark.parametrize("method,path", write_endpoints())
def test_a_json_content_type_with_a_charset_is_accepted(admin, method, path):
    r = getattr(admin.c, method.lower())(path, content=b"{}", headers={**CSRF, "Content-Type": "application/json; charset=utf-8"})
    assert "CSRF" not in r.text, (method, path)


@pytest.mark.parametrize("method,path", write_endpoints())
def test_the_global_csrf_guard_runs_first_and_a_signalled_write_still_needs_an_admin(client, method, path):
    """Phase 14B: the browser-request check is global and runs before any route, so an unsignalled write is refused as CSRF whoever sends
    it (the rule is the same for every API, so this says nothing admin-specific). With the signal, authentication and the role decide."""
    r = getattr(Api(csrf=False), method.lower())(path)
    assert r.status_code == 403 and "CSRF" in r.json()["detail"]
    assert getattr(Api(), method.lower())(path).status_code == 401
    learner = register_browser("learner", "l@example.com")
    r = getattr(adm.Api(learner.c), method.lower())(path)
    assert r.status_code == 403 and "CSRF" not in r.text                # a signalled non-admin gets the role refusal, nothing more


def test_reads_need_no_csrf_header(admin):
    assert admin.c.get("/api/admin/audit").status_code == 200
    assert admin.c.get("/api/admin/users").status_code == 200


def test_the_csrf_guard_itself_distinguishes_every_case():
    """Direct checks of the guard, independent of any route: only a safe method, or JSON plus the exact header, passes."""
    from fastapi import HTTPException

    from backend.admin.security import csrf_guard

    class Req:
        def __init__(self, method, headers):
            self.method, self.headers = method, {k.lower(): v for k, v in headers.items()}

    ok = {"Content-Type": "application/json", "X-Requested-With": "XMLHttpRequest"}
    for method in ("GET", "HEAD", "OPTIONS"):
        csrf_guard(Req(method, {}))
    for method in ("POST", "PUT", "PATCH", "DELETE"):
        csrf_guard(Req(method, ok))
        csrf_guard(Req(method, {**ok, "Content-Type": "Application/JSON; charset=utf-8"}))
        for bad in ({}, {"Content-Type": "application/json"}, {"X-Requested-With": "XMLHttpRequest"}, {**ok, "X-Requested-With": "x"}, {**ok, "Content-Type": "text/plain"},
                    {**ok, "X-Requested-With": "xmlhttprequest"}, {**ok, "X-Requested-With": "XMLHttpRequest "}, {**ok, "Content-Type": "application/jsonp"},
                    {**ok, "Content-Type": "text/json"}, {**ok, "Content-Type": "application/json-patch+json"}):
            with pytest.raises(HTTPException) as e:
                csrf_guard(Req(method, bad))
            assert e.value.status_code == 403


# ---------- responses ----------
@pytest.mark.parametrize("method,path", endpoints())
def test_every_admin_response_is_no_store_including_errors(admin, client, method, path):
    for api in (admin, Api(), register_browser("learner", "l@example.com")):
        r = getattr(api, method.lower())(path)
        assert r.headers.get("cache-control") == "no-store", (method, path, r.status_code)


def test_no_store_also_covers_404_and_validation_errors(admin):
    assert admin.get("/api/admin/audit/999999").headers["cache-control"] == "no-store"
    r = admin.get("/api/admin/audit?limit=0")
    assert r.status_code == 422 and r.headers["cache-control"] == "no-store"


def test_since_phase_14b_every_api_response_is_no_store_but_pages_are_not(client):
    assert client.get("/api/languages").headers["cache-control"] == "no-store"
    assert "no-store" not in client.get("/").headers.get("cache-control", "")
    assert "no-store" not in client.get("/static/app.js").headers.get("cache-control", "")


# ---------- admins stay out of learner and parent data; no impersonation ----------
def test_an_admin_has_no_access_to_learner_or_parent_apis(admin, client):
    learner = register_browser("learner", "l@example.com")
    for url in ("/api/lessons", "/api/progress/lessons", "/api/situations", "/api/listening", "/api/plan", "/api/gamification", "/api/profile", "/api/parent/children"):
        r = admin.get(url)
        assert r.status_code in (403, 404, 409), (url, r.status_code)
        assert r.status_code != 200, url
    handle = learner.get("/api/auth/me").json()["user"]["handle"]
    assert admin.get(f"/api/state/{handle}").status_code == 403


def test_there_is_no_impersonation_route_anywhere():
    paths = [r.path for r in main.app.routes if hasattr(r, "path")]
    assert not [p for p in paths if re.search(r"imperson|login[-_]?as|become|sudo|act[-_]?as|switch[-_]?user|masquerade", p, re.I)], paths


def test_admin_responses_never_set_a_cookie_or_issue_a_session(admin):
    for url in ("/api/admin/audit", "/api/admin/users"):
        assert "set-cookie" not in admin.get(url).headers
    for method, path in write_endpoints():
        assert "set-cookie" not in getattr(admin, method.lower())(path).headers, (method, path)


def test_admin_session_is_not_a_learner_session(admin):
    me = admin.get("/api/auth/me").json()["user"]
    assert me["roles"] == ["admin"]
