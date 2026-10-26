"""Helpers for Phase 9 tests: parents, children and the link between them."""
import json

from backend import main
from backend.auth import service as auth_service
from backend.db import connect
from backend.parent import service as parent_service

from .agekids import make_learner
from .conftest import browser as conftest_browser, register


def db():
    return connect(main.DB_PATH)


def browser():
    return conftest_browser()


def make_parent(c, email="p@example.com"):
    return register(c, email, role="parent")


def make_child(c, email, age=14):
    return make_learner(c, email, age)


def code_for(child):
    r = child.post("/api/profile/parent-link-code")
    assert r.status_code == 201, r.text
    return r.json()["code"]


def link(parent, child):
    """The parent links the child through a code the child's session made. Returns the link id."""
    r = parent.post("/api/parent/children", json={"code": code_for(child)})
    assert r.status_code == 201, r.text
    return r.json()["child"]["id"]


def uid(email):
    with db() as conn:
        return conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()[0]


def all_keys(obj, found=None):
    found = set() if found is None else found
    if isinstance(obj, dict):
        for k, v in obj.items():
            found.add(k)
            all_keys(v, found)
    elif isinstance(obj, list):
        for v in obj:
            all_keys(v, found)
    return found


PARENT_GETS = ["overview", "progress", "weaknesses", "confidence", "activity", "controls"]
