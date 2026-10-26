"""Phase 13H: the admin console, tested by running the real frontend JavaScript (agemode.js, admin.js) in JavaScriptCore against a live server with a temporary database.
Skipped automatically where macOS osascript / curl are not available, like the other frontend tests. Every scenario asserts what the page RENDERED and what it SENT."""
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest

from backend.db import connect
from backend.manage import create_admin

from . import adm
from .agekids import dob_for_age
from .conftest import SHARED_ADDRESS_LIMITS, PASSWORD

ROOT = Path(__file__).resolve().parent.parent
HARNESS = ROOT / "tests" / "frontend" / "admin_harness.js"
REAL_DB = (ROOT / "buddy.db").resolve()
ADMIN_EMAIL = "console-admin@example.com"

pytestmark = pytest.mark.skipif(sys.platform != "darwin" or not shutil.which("osascript") or not shutil.which("curl"), reason="needs macOS osascript (JavaScriptCore) and curl")


def js(expression):
    return subprocess.run(["osascript", "-l", "JavaScript", "-e", expression], capture_output=True, text=True, timeout=60)


@pytest.mark.parametrize("path", ["frontend/admin.js", "frontend/agemode.js", "frontend/app.js", "tests/frontend/admin_harness.js"])
def test_the_files_parse(path):
    expr = f"var s=$.NSString.stringWithContentsOfFileEncodingError('{ROOT / path}',4,null).js; try{{new Function(s);'OK'}}catch(e){{'ERR '+e}}"
    assert js(expr).stdout.strip() == "OK"


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def server(tmp_path_factory):
    work = tmp_path_factory.mktemp("adminsrv")
    db_path = (work / "test.db").resolve()
    assert db_path != REAL_DB and ROOT not in db_path.parents                       # a test server never touches the real database
    env = {**os.environ, **SHARED_ADDRESS_LIMITS, "DB_PATH": str(db_path), "RECORDINGS_DIR": str(work / "recordings"), "GROQ_API_KEY": "CANARY-HEALTH-KEY", "OLLAMA_URL": "http://canary-host.internal:11434",
           "ADMIN_REF_SECRET": "frontend-test-reference-key"}
    for k in ("STT_PROVIDER", "PRONUNCIATION_PROVIDER"):
        env.pop(k, None)
    port = free_port()
    proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", str(port)], cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = f"http://127.0.0.1:{port}"
    try:
        for _ in range(100):
            try:
                if httpx.get(f"{base}/api/health", timeout=1).status_code == 200:
                    break
            except httpx.HTTPError:
                time.sleep(0.15)
        else:
            raise RuntimeError("test server did not start")
        create_admin(db_path, ADMIN_EMAIL, PASSWORD, "Console Admin")
        ids = seed(db_path)
        yield base, work, ids
    finally:
        proc.terminate()
        proc.wait(timeout=10)


def seed(db_path):
    """Real-looking activity (timestamped now) so the dashboard has figures, plus enough drafts to need a second page."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    with connect(db_path) as conn:
        people = adm.learners(conn, 6, created=now)
        lid, sid, aid = adm.lesson_id(conn), adm.situation_id(conn), adm.activity_id(conn)
        for n, u in enumerate(people):
            adm.lesson_progress(conn, u, lid, started=now, completed=now if n < 5 else None)
            adm.exercise_attempt(conn, u, adm.first_exercise(conn, lid), correct=n % 2, at=now)
            adm.xp(conn, u, 4000 + n, earned=now)
            adm.situation_progress(conn, u, sid, started=now)
        small = adm.learners(conn, 3, created=now)                                  # a cohort of three: its figures must be hidden on the dashboard
        for u in small:
            adm.roleplay_session(conn, u, sid, status="completed", missed=0, at=now)
        for u in small[:2]:
            adm.pronunciation(conn, u, now)                                         # two learners' pronunciation checks: a count that must be hidden
        for k in range(30):
            adm.make_lesson(conn, f"bulk-{k:02d}", exercises=1, title=f"Bulk lesson {k:02d}")
        item = adm.usable_items(conn, 1)[0]
        return {"item": item, "lesson": lid, "situation": sid, "activity": aid, "search": "bulk"}


def admin_sessions(db_path, count=6):
    """Fresh sessions for the console admin that have passed a second factor (Phase 14D: the admin API requires one). The harness uses one
    per sign-in instead of the password; the real enrollment and code sign-in are tested by the two-factor harness."""
    from backend.auth import service
    from backend.db import connect
    with connect(db_path) as conn:
        uid = conn.execute("SELECT id FROM users WHERE email = ?", (ADMIN_EMAIL,)).fetchone()[0]
        return [service._start_session(conn, uid, service.utcnow(), mfa_level=1, auth_method="password+totp")[0] for _ in range(count)]


def run(server, scenario, tmp_path):
    base, work, ids = server
    env = {**os.environ, "BASE": base, "ROOT": str(ROOT), "WORKDIR": str(tmp_path), "SCENARIO": scenario, "ADMIN_EMAIL": ADMIN_EMAIL, "PASSWORD": PASSWORD, "LEARNER_DOB": dob_for_age(30), "IDS": json.dumps(ids),
           "ADMIN_SESSIONS": json.dumps(admin_sessions(work / "test.db"))}
    r = subprocess.run(["osascript", "-l", "JavaScript", str(HARNESS)], capture_output=True, text=True, timeout=240, env=env)
    lines = [l for l in (r.stdout + r.stderr).splitlines() if l.startswith("## ")]
    assert lines, f"the harness produced no result:\n{r.stdout}\n{r.stderr}"
    return json.loads(lines[-1][3:])["checks"]


def assert_all(checks):
    failed = {k: v for k, v in checks.items() if v is not True}
    assert not failed, f"failed checks: {failed}"


SCENARIOS = re.findall(r"^  async (\w+)\(\) \{", HARNESS.read_text(), re.M)


def test_every_scenario_is_listed():
    assert len(SCENARIOS) >= 19 and "nav_modes" in SCENARIOS and "revision_conflict_is_handled" in SCENARIOS and "archive_needs_confirmation_and_never_deletes" in SCENARIOS


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_admin_console(scenario, server, tmp_path):
    assert_all(run(server, scenario, tmp_path))


def test_the_page_is_wired_into_the_app():
    index, app, agemode = [(ROOT / "frontend" / n).read_text() for n in ("index.html", "app.js", "agemode.js")]
    assert "/static/admin.js" in index and "/static/admin.css" in index and index.index("admin.js") < index.index("app.js")
    assert 'admin: () => AdminView.page()' in app and "#/admin" in app
    assert "admin" in agemode


def test_the_admin_console_never_issues_a_delete():
    source = (ROOT / "frontend" / "admin.js").read_text()
    assert "DELETE" not in source and not re.search(r'call\("DELETE"', source) and 'method: "DELETE"' not in source
