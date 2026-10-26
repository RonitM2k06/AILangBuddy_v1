"""Phase 14D, frontend: the real profile, two-factor and admin-console code in JavaScriptCore against a live test server (temp database):
setup with the local QR code and the manual key, recovery codes shown once, the sign-in code step, recovery-code sign-in, new codes and
turning it off, and the admin console's mandatory enrollment. Skipped automatically where osascript or curl is not available."""
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest

from .conftest import PASSWORD, SHARED_ADDRESS_LIMITS

ROOT = Path(__file__).resolve().parent.parent
HARNESS = ROOT / "tests" / "frontend" / "twofactor_harness.js"
REAL_DB = (ROOT / "buddy.db").resolve()

pytestmark = pytest.mark.skipif(sys.platform != "darwin" or not shutil.which("osascript") or not shutil.which("curl"),
                                reason="needs macOS osascript (JavaScriptCore) and curl")


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def server(tmp_path_factory):
    work = tmp_path_factory.mktemp("tfsrv")
    db_path = (work / "test.db").resolve()
    assert db_path != REAL_DB and ROOT not in db_path.parents
    env = {**os.environ, **SHARED_ADDRESS_LIMITS, "DB_PATH": str(db_path), "RECORDINGS_DIR": str(work / "recordings")}
    assert env.get("GROQ_API_KEY") == "" and env.get("TOTP_ENC_KEY")                 # no provider; the test-only TOTP key
    port = free_port()
    proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", str(port)], cwd=ROOT, env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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
        yield base, db_path
    finally:
        proc.terminate()
        proc.wait(timeout=10)


def run(server, scenario, tmp_path, **extra):
    base, _ = server
    env = {**os.environ, "BASE": base, "ROOT": str(ROOT), "WORKDIR": str(tmp_path), "SCENARIO": scenario, "PASSWORD": PASSWORD, **extra}
    r = subprocess.run(["osascript", "-l", "JavaScript", str(HARNESS)], capture_output=True, text=True, timeout=240, env=env)
    lines = [l for l in (r.stdout + r.stderr).splitlines() if l.startswith("## ")]
    assert lines, f"the harness produced no result:\n{r.stdout}\n{r.stderr}"
    return json.loads(lines[-1][3:])["checks"]


def assert_all(checks):
    failed = {k: v for k, v in checks.items() if v is not True}
    assert checks and not failed, f"failed checks: {failed}"


SCENARIOS = re.findall(r"^  async (\w+)\(\) \{", HARNESS.read_text(), re.M)


def test_every_scenario_is_listed():
    assert len(SCENARIOS) == 6 and "an_admin_must_turn_it_on_before_the_console_opens" in SCENARIOS


@pytest.mark.parametrize("scenario", [s for s in SCENARIOS if s != "an_admin_must_turn_it_on_before_the_console_opens"])
def test_two_factor_pages(scenario, server, tmp_path):
    assert_all(run(server, scenario, tmp_path))


def test_the_admin_console_requires_enrollment(server, tmp_path):
    from backend.manage import create_admin
    email = f"admin{time.monotonic_ns()}@example.com"
    create_admin(server[1], email, PASSWORD, "Console Admin")
    assert_all(run(server, "an_admin_must_turn_it_on_before_the_console_opens", tmp_path, ADMIN_EMAIL=email))


def test_the_page_loads_the_two_factor_script_and_never_logs_or_stores_secrets():
    index = (ROOT / "frontend" / "index.html").read_text()
    assert index.index("/static/profile.js") < index.index("/static/twofactor.js") < index.index("/static/admin.js") < index.index("/static/app.js")
    source = (ROOT / "frontend" / "twofactor.js").read_text()
    assert not re.search(r"\bconsole\.(log|info|warn|error|debug)\(", source) and "localStorage" not in source and "sessionStorage" not in source and "http" not in source.replace("https://", "")
