"""Phase 14A, frontend: the legacy prototype (engine.js + app.js) runs in JavaScriptCore against a live test server (temp database).

  * anonymous visitors never read or write server-side state (a demo state planted in the database is never loaded);
  * a signed-in user reads and writes only their own state, and signing in or out switches identity without carrying state across;
  * attacker-controlled state values render as text: no markup, no attribute or style injection, nothing planted reaches an onclick;
  * the legacy pages still render, and the AI requests carry only what /api/ai accepts.
Skipped automatically where osascript or curl is not available."""
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

from backend.db import connect

from .conftest import SHARED_ADDRESS_LIMITS, PASSWORD, register

ROOT = Path(__file__).resolve().parent.parent
HARNESS = ROOT / "tests" / "frontend" / "legacy_harness.js"
REAL_DB = (ROOT / "buddy.db").resolve()
PAYLOAD = "<img src=x onerror=alert(1)>"
TOPIC = "x');alert(1);//\"><img src=x onerror=alert(2)>"

pytestmark = pytest.mark.skipif(sys.platform != "darwin" or not shutil.which("osascript") or not shutil.which("curl"),
                                reason="needs macOS osascript (JavaScriptCore) and curl")


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def server(tmp_path_factory):
    work = tmp_path_factory.mktemp("legacysrv")
    db_path = (work / "test.db").resolve()
    assert db_path != REAL_DB and ROOT not in db_path.parents                       # a test server never touches the real database
    env = {**os.environ, **SHARED_ADDRESS_LIMITS, "DB_PATH": str(db_path), "RECORDINGS_DIR": str(work / "recordings")}
    for k in ("GROQ_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OLLAMA_URL"):
        assert env.get(k) == "", f"{k} must be blank for a test server (see conftest.py)"
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
        assert httpx.get(f"{base}/api/health").json()["ai"] is False                 # no provider is configured in the test server
        with connect(db_path) as conn:                                             # what a pre-14A database may hold: an attacker's shared demo state
            conn.execute("INSERT INTO state(user_id, data) VALUES ('demo-alex', ?)", (json.dumps({"v": 1, "level": PAYLOAD, "name": PAYLOAD}),))
        yield base, db_path
    finally:
        proc.terminate()
        proc.wait(timeout=10)


def account(base, db_path, planted=None):
    """A fresh learner account; `planted` is written straight into its stored state (bypassing the API's validation, as an old row would)."""
    email = f"legacy{time.monotonic_ns()}@example.com"
    with httpx.Client(base_url=base) as c:
        handle = register(c, email)["handle"]
    if planted is not None:
        with connect(db_path) as conn:
            conn.execute("INSERT INTO state(user_id, data) VALUES (?, ?)", (handle, json.dumps(planted)))
    return email


def run(server, scenario, tmp_path, **extra):
    base, db_path = server
    env = {**os.environ, "BASE": base, "ROOT": str(ROOT), "WORKDIR": str(tmp_path), "SCENARIO": scenario, "PAYLOAD": PAYLOAD, "PASSWORD": PASSWORD, **extra}
    r = subprocess.run(["osascript", "-l", "JavaScript", str(HARNESS)], capture_output=True, text=True, timeout=240, env=env)
    lines = [l for l in (r.stdout + r.stderr).splitlines() if l.startswith("## ")]
    assert lines, f"the harness produced no result:\n{r.stdout}\n{r.stderr}"
    return json.loads(lines[-1][3:])["checks"]


def assert_all(checks):
    failed = {k: v for k, v in checks.items() if v is not True}
    assert checks and not failed, f"failed checks: {failed}"


def test_the_harness_parses():
    expr = f"var s=$.NSString.stringWithContentsOfFileEncodingError('{HARNESS}',4,null).js; try{{new Function(s);'OK'}}catch(e){{'ERR '+e}}"
    r = subprocess.run(["osascript", "-l", "JavaScript", "-e", expr], capture_output=True, text=True, timeout=60)
    assert r.stdout.strip() == "OK", r.stdout + r.stderr


def test_every_scenario_is_run():
    found = set(re.findall(r"^  async (\w+)\(\) \{", HARNESS.read_text(), re.M))
    assert found == {"anonymous_is_local_only", "signed_in_uses_own_identity", "malicious_state_renders_as_text", "legacy_ui_still_works",
                     "ai_requests_carry_only_the_allowed_fields", "sign_in_and_out_switch_identity", "the_account_copy_wins_over_this_browsers",
                     "mumbai_pack_works", "mumbai_in_marathi_works", "bengaluru_in_kannada_works", "chennai_in_tamil_works", "puducherry_works", "jaipur_and_lucknow_work", "kolkata_in_bengali_works", "hyderabad_works", "jammu_kashmir_works",
                     "an_old_invalid_city_language_pair_is_repaired", "each_pack_keeps_its_own_progress",
                     "learn_tools_follow_the_city_and_language"}


def test_anonymous_is_local_only(server, tmp_path):
    assert_all(run(server, "anonymous_is_local_only", tmp_path))


def test_signed_in_uses_own_identity(server, tmp_path):
    assert_all(run(server, "signed_in_uses_own_identity", tmp_path, EMAIL=account(*server)))


def test_malicious_state_renders_as_text(server, tmp_path):
    planted = {"v": 1, "level": PAYLOAD, "name": "Alex", "tutor": [{"role": "me", "text": "hi"},
               {"role": "ai", "intro": "Try:", "topic": TOPIC, "phrases": [{"roman": "Namaste", "hi": "नमस्ते", "en": "Hello"}]}]}
    assert_all(run(server, "malicious_state_renders_as_text", tmp_path, EMAIL=account(*server, planted=planted)))


def test_the_account_copy_wins_over_this_browsers(server, tmp_path):
    planted = {"v": 1, "confidence": {"greetings": 90, "transport": 100, "food": 33, "shopping": 50, "directions": 80, "college": 65, "smalltalk": 40}}
    assert_all(run(server, "the_account_copy_wins_over_this_browsers", tmp_path, EMAIL=account(*server, planted=planted)))


def test_the_mumbai_pack_works(server, tmp_path):
    assert_all(run(server, "mumbai_pack_works", tmp_path, EMAIL=account(*server)))


def test_mumbai_can_be_learnt_in_marathi(server, tmp_path):
    assert_all(run(server, "mumbai_in_marathi_works", tmp_path, EMAIL=account(*server), FAKE_AI="1"))


def test_bengaluru_can_be_learnt_in_kannada(server, tmp_path):
    """Bengaluru's Kannada pack, roleplays, tutor, prices and voice language, the English view of it, and a language Bengaluru does not
    offer falling back to Kannada; Mumbai's Marathi and Delhi's Hindi are unchanged."""
    assert_all(run(server, "bengaluru_in_kannada_works", tmp_path, EMAIL=account(*server), FAKE_AI="1"))


def test_chennai_can_be_learnt_in_tamil(server, tmp_path):
    """Chennai's Tamil pack, roleplays, tutor, prices and voice language, the English view of it, and a language Chennai does not offer
    falling back to Tamil; Bengaluru's Kannada and Delhi's Hindi are unchanged."""
    assert_all(run(server, "chennai_in_tamil_works", tmp_path, EMAIL=account(*server), FAKE_AI="1"))


def test_puducherry_can_be_learnt_in_tamil_and_french(server, tmp_path):
    """Puducherry in Tamil (its own pack) and in French (its second pack, with accents, a pronunciation guide and accent-blind roleplays), each
    with its own progress; Chennai is never given French."""
    assert_all(run(server, "puducherry_works", tmp_path, EMAIL=account(*server), FAKE_AI="1"))


def test_jaipur_and_lucknow_can_be_learnt_in_hindi(server, tmp_path):
    """Jaipur's, Lucknow's and Bhopal's Hindi packs, roleplays, tutor, review notes and voice language, a language they do not offer falling back to
    Hindi; Delhi's and Mumbai's Hindi are unchanged."""
    assert_all(run(server, "jaipur_and_lucknow_work", tmp_path, EMAIL=account(*server), FAKE_AI="1"))


def test_kolkata_can_be_learnt_in_bengali(server, tmp_path):
    """Kolkata's Bengali pack, roleplays, tutor, voice language and AI label, the English view of it, and a language Kolkata does not offer
    falling back to Bengali; Delhi's Hindi is unchanged."""
    assert_all(run(server, "kolkata_in_bengali_works", tmp_path, EMAIL=account(*server), FAKE_AI="1"))


def test_hyderabad_can_be_learnt_in_telugu_and_urdu(server, tmp_path):
    """Hyderabad in Telugu (its own pack) and in Urdu (its second pack, in Urdu script with a feminine form), each with its own progress and
    voice language; Lucknow is never given Urdu."""
    assert_all(run(server, "hyderabad_works", tmp_path, EMAIL=account(*server), FAKE_AI="1"))


def test_jammu_kashmir_can_be_learnt_in_kashmiri_dogri_and_urdu(server, tmp_path):
    """Jammu & Kashmir's three packs, each with its own voice language, tutor and roleplays; the Kashmiri says it is a draft; Hyderabad's Urdu is
    unchanged and Delhi is never given Kashmiri."""
    assert_all(run(server, "jammu_kashmir_works", tmp_path, EMAIL=account(*server), FAKE_AI="1"))


def test_learn_tools_follow_the_city_and_language(server, tmp_path):
    """Readings, the level check, achievement names and the tutor are Mumbai's (in Hindi or Marathi) for Mumbai and unchanged for Delhi."""
    assert_all(run(server, "learn_tools_follow_the_city_and_language", tmp_path, EMAIL=account(*server)))


def test_each_pack_keeps_its_own_progress(server, tmp_path):
    """Finishing a day or reviewing a card in one pack never marks it in another; switching back loses nothing (Delhi keeps its keys)."""
    assert_all(run(server, "each_pack_keeps_its_own_progress", tmp_path, EMAIL=account(*server)))


def test_an_old_invalid_city_language_pair_is_repaired(server, tmp_path):
    planted = {"v": 1, "name": "Test User", "city": "delhi", "language": "mr", "level": "A1", "xp": 40,
               "confidence": {"greetings": 50, "transport": 50, "food": 50, "shopping": 50, "directions": 50, "college": 50, "smalltalk": 50}}
    assert_all(run(server, "an_old_invalid_city_language_pair_is_repaired", tmp_path, EMAIL=account(*server, planted=planted)))


def test_legacy_ui_still_works(server, tmp_path):
    assert_all(run(server, "legacy_ui_still_works", tmp_path, EMAIL=account(*server)))


def test_ai_requests_carry_only_the_allowed_fields(server, tmp_path):
    assert_all(run(server, "ai_requests_carry_only_the_allowed_fields", tmp_path, FAKE_AI="1"))


def test_sign_in_and_out_switch_identity(server, tmp_path):
    assert_all(run(server, "sign_in_and_out_switch_identity", tmp_path, EMAIL=account(*server)))


def test_the_roleplay_page_sends_the_scene_by_id():
    app = (ROOT / "frontend" / "app.js").read_text()
    assert 'E.askAI({ mode: "roleplay", scenario: RP.sid, history: RP.msgs })' in app and "scenario: sc," not in app
    engine = (ROOT / "frontend" / "engine.js").read_text()
    assert "demo-alex" not in engine and "USER" not in engine
