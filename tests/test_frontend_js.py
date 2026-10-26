"""Frontend tests without a browser: the real frontend JavaScript runs in JavaScriptCore (macOS `osascript`) with a stubbed
microphone/MediaRecorder/clock against a live test server (temp database, temp recordings directory, mock STT provider).
Skipped automatically where osascript or curl is not available."""
import json
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest

from .conftest import SHARED_ADDRESS_LIMITS

ROOT = Path(__file__).resolve().parent.parent
HARNESS = ROOT / "tests" / "frontend" / "voice_harness.js"
REAL_DB = (ROOT / "buddy.db").resolve()

pytestmark = pytest.mark.skipif(sys.platform != "darwin" or not shutil.which("osascript") or not shutil.which("curl"),
                                reason="needs macOS osascript (JavaScriptCore) and curl")

FRONTEND_FILES = ["app", "engine", "content", "bits", "profile", "twofactor", "lessons", "situations", "plan", "listening", "voice", "agemode", "kids", "teen", "parent", "gamify", "ai", "adaptive"]


def js(path, expression):
    return subprocess.run(["osascript", "-l", "JavaScript", "-e", expression], capture_output=True, text=True, timeout=60)


@pytest.mark.parametrize("name", FRONTEND_FILES)
def test_frontend_javascript_parses(name):
    path = ROOT / "frontend" / f"{name}.js"
    expr = f"var s=$.NSString.stringWithContentsOfFileEncodingError('{path}',4,null).js; try{{new Function(s);'OK'}}catch(e){{'ERR '+e}}"
    r = js(path, expr)
    assert r.stdout.strip() == "OK", r.stdout + r.stderr


def test_the_voice_harness_itself_parses():
    expr = f"var s=$.NSString.stringWithContentsOfFileEncodingError('{HARNESS}',4,null).js; try{{new Function(s);'OK'}}catch(e){{'ERR '+e}}"
    assert js(HARNESS, expr).stdout.strip() == "OK"


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def start_server(tmp_path_factory):
    procs = []

    def start(stt_provider, pron_provider=None):
        work = tmp_path_factory.mktemp("srv")
        db_path = (work / "test.db").resolve()
        assert db_path != REAL_DB and ROOT not in db_path.parents                # a test server never touches the real database
        env = {**os.environ, **SHARED_ADDRESS_LIMITS, "DB_PATH": str(db_path), "RECORDINGS_DIR": str(work / "recordings")}
        env.pop("STT_PROVIDER", None)
        env.pop("PRONUNCIATION_PROVIDER", None)
        if stt_provider:
            env["STT_PROVIDER"] = stt_provider
        if pron_provider:
            env["PRONUNCIATION_PROVIDER"] = pron_provider
        port = free_port()
        p = subprocess.Popen([sys.executable, "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", str(port)],
                             cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        procs.append(p)
        for _ in range(100):
            try:
                if httpx.get(f"http://127.0.0.1:{port}/api/health", timeout=1).status_code == 200:
                    return f"http://127.0.0.1:{port}", work
            except httpx.HTTPError:
                time.sleep(0.15)
        raise RuntimeError("test server did not start")

    yield start
    for p in procs:
        p.terminate()
        p.wait(timeout=10)


@pytest.fixture(scope="module")
def mock_server(start_server):
    return start_server("mock")


@pytest.fixture(scope="module")
def pron_server(start_server):
    return start_server("mock", "mock")


@pytest.fixture(scope="module")
def bare_server(start_server):
    return start_server(None)


def run_scenario(base, scenario, tmp_path):
    env = {**os.environ, "BASE": base, "ROOT": str(ROOT), "WORKDIR": str(tmp_path), "SCENARIO": scenario}
    r = subprocess.run(["osascript", "-l", "JavaScript", str(HARNESS)], capture_output=True, text=True, timeout=120, env=env)
    lines = [l for l in (r.stdout + r.stderr).splitlines() if l.startswith("## ")]
    assert lines, f"the harness produced no result:\n{r.stdout}\n{r.stderr}"
    return json.loads(lines[-1][3:])["checks"]


def assert_all(checks):
    failed = {k: v for k, v in checks.items() if v is not True}
    assert not failed, f"failed checks: {failed}"


SCENARIOS = ["signed_out", "unsupported_browser", "permission_denied", "no_microphone", "successful_recording", "empty_recording", "too_short_recording",
             "maximum_duration", "cancel_and_retry", "stt_failure_is_shown_safely", "upload_rejected_by_server", "recorder_failure", "recorder_cannot_start",
             "choosing_another_phrase"]


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_voice_page_scenarios(scenario, mock_server, tmp_path):
    assert_all(run_scenario(mock_server[0], scenario, tmp_path))


PRONUNCIATION_SCENARIOS = ["pronunciation_is_a_separate_result", "poor_transcript_with_high_pronunciation_is_shown_as_is", "pronunciation_failure_can_be_retried",
                           "no_signal_is_reported_without_inventing_a_score"]


@pytest.mark.parametrize("scenario", PRONUNCIATION_SCENARIOS)
def test_pronunciation_results_page(scenario, pron_server, tmp_path):
    assert_all(run_scenario(pron_server[0], scenario, tmp_path))


def test_pronunciation_is_reported_as_unavailable_when_no_provider_is_configured(mock_server, tmp_path):
    assert_all(run_scenario(mock_server[0], "pronunciation_unavailable_on_a_server_without_a_provider", tmp_path))


def test_voice_page_when_no_speech_provider_is_configured(bare_server, tmp_path):
    assert_all(run_scenario(bare_server[0], "stt_unavailable", tmp_path))


def test_no_recordings_were_left_in_the_repository_by_the_frontend_runs(mock_server):
    assert not (ROOT / "recordings").exists() and not list(ROOT.glob("**/rec_*.webm")) and not list(ROOT.glob("**/rec_*.ogg"))


# ---------- Phase 8: age-aware experience (kids adventure, teen path, mode switching) ----------
KIDS_HARNESS = ROOT / "tests" / "frontend" / "kids_harness.js"


def test_the_kids_harness_itself_parses():
    expr = f"var s=$.NSString.stringWithContentsOfFileEncodingError('{KIDS_HARNESS}',4,null).js; try{{new Function(s);'OK'}}catch(e){{'ERR '+e}}"
    assert js(KIDS_HARNESS, expr).stdout.strip() == "OK"


def run_kids(server, scenario, tmp_path):
    from .agekids import answer_key, dob_for_age
    base, work = server
    env = {**os.environ, "BASE": base, "ROOT": str(ROOT), "WORKDIR": str(tmp_path), "SCENARIO": scenario, "KEY": json.dumps(answer_key(work / "test.db")),
           "DOB_CHILD": dob_for_age(6), "DOB_TEEN": dob_for_age(14), "DOB_ADULT": dob_for_age(30)}
    r = subprocess.run(["osascript", "-l", "JavaScript", str(KIDS_HARNESS)], capture_output=True, text=True, timeout=180, env=env)
    lines = [l for l in (r.stdout + r.stderr).splitlines() if l.startswith("## ")]
    assert lines, f"the harness produced no result:\n{r.stdout}\n{r.stderr}"
    return json.loads(lines[-1][3:])["checks"]


KIDS_SCENARIOS = ["signed_out", "not_a_child", "map_and_lives", "question_screen", "playing_audio_speaks_the_phrase", "wrong_answer_loses_a_life",
                  "correct_answer_keeps_lives", "no_hearts_left_blocks_play", "map_shows_sleeping_state_without_hearts", "finishing_a_level_unlocks_the_next",
                  "locked_level_is_explained", "child_navigation_is_small_and_simple", "teen_gets_a_path_page_and_keeps_navigation", "teen_page_is_not_for_children",
                  "adult_is_unchanged", "signed_out_is_unchanged", "leaving_childhood_changes_the_mode"]


@pytest.mark.parametrize("scenario", KIDS_SCENARIOS)
def test_age_aware_pages(scenario, mock_server, tmp_path):
    assert_all(run_kids(mock_server, scenario, tmp_path))


# ---------- Phase 9: parent portal ----------
PARENT_HARNESS = ROOT / "tests" / "frontend" / "parent_harness.js"


def test_the_parent_harness_itself_parses():
    expr = f"var s=$.NSString.stringWithContentsOfFileEncodingError('{PARENT_HARNESS}',4,null).js; try{{new Function(s);'OK'}}catch(e){{'ERR '+e}}"
    assert js(PARENT_HARNESS, expr).stdout.strip() == "OK"


def run_parent(server, scenario, tmp_path):
    from .agekids import answer_key, dob_for_age
    base, work = server
    env = {**os.environ, "BASE": base, "ROOT": str(ROOT), "WORKDIR": str(tmp_path), "SCENARIO": scenario, "KEY": json.dumps(answer_key(work / "test.db")),
           "DOB_CHILD": dob_for_age(6), "DOB_TEEN": dob_for_age(14), "DOB_ADULT": dob_for_age(30)}
    r = subprocess.run(["osascript", "-l", "JavaScript", str(PARENT_HARNESS)], capture_output=True, text=True, timeout=180, env=env)
    lines = [l for l in (r.stdout + r.stderr).splitlines() if l.startswith("## ")]
    assert lines, f"the harness produced no result:\n{r.stdout}\n{r.stderr}"
    return json.loads(lines[-1][3:])["checks"]


PARENT_SCENARIOS = ["signed_out", "a_learner_is_told_this_is_for_parents", "empty_list_offers_to_add_a_child", "linking_with_the_childs_code", "a_wrong_code_gives_a_calm_message",
                    "an_empty_code_is_not_sent", "dashboard_shows_the_childs_activity", "child_voice_cannot_be_turned_on", "parent_can_switch_a_teens_voice_off_and_on",
                    "a_failed_control_change_is_reported", "unknown_child", "another_parents_child_looks_like_an_unknown_child", "stop_following", "parent_navigation",
                    "learners_are_unaffected_by_the_parent_entry"]


@pytest.mark.parametrize("scenario", PARENT_SCENARIOS)
def test_parent_dashboard_pages(scenario, mock_server, tmp_path):
    assert_all(run_parent(mock_server, scenario, tmp_path))


# ---------- Phase 10: rewards and friends ----------
GAMIFY_HARNESS = ROOT / "tests" / "frontend" / "gamify_harness.js"


def test_the_gamify_harness_itself_parses():
    expr = f"var s=$.NSString.stringWithContentsOfFileEncodingError('{GAMIFY_HARNESS}',4,null).js; try{{new Function(s);'OK'}}catch(e){{'ERR '+e}}"
    assert js(GAMIFY_HARNESS, expr).stdout.strip() == "OK"


def run_gamify(server, scenario, tmp_path):
    from .agekids import dob_for_age
    base, work = server
    env = {**os.environ, "BASE": base, "ROOT": str(ROOT), "WORKDIR": str(tmp_path), "SCENARIO": scenario,
           "DOB_CHILD": dob_for_age(6), "DOB_TEEN": dob_for_age(14), "DOB_ADULT": dob_for_age(30)}
    r = subprocess.run(["osascript", "-l", "JavaScript", str(GAMIFY_HARNESS)], capture_output=True, text=True, timeout=240, env=env)
    lines = [l for l in (r.stdout + r.stderr).splitlines() if l.startswith("## ")]
    assert lines, f"the harness produced no result:\n{r.stdout}\n{r.stderr}"
    return json.loads(lines[-1][3:])["checks"]


GAMIFY_SCENARIOS = ["rewards_signed_out", "rewards_new_learner", "rewards_after_activity", "claiming_a_challenge", "the_page_never_sends_an_amount", "timezone_button",
                    "a_child_gets_no_friends", "friends_signed_out", "friends_empty_page", "sending_a_request_and_accepting_it", "rejecting_a_request",
                    "a_wrong_code_gets_a_calm_message", "an_empty_code_is_not_sent", "removing_a_friend", "leaderboard_period_toggle",
                    "navigation_is_not_changed_for_children_or_parents"]


@pytest.mark.parametrize("scenario", GAMIFY_SCENARIOS)
def test_rewards_and_friends_pages(scenario, mock_server, tmp_path):
    assert_all(run_gamify(mock_server, scenario, tmp_path))


# ---------- Phase 11: AI tutor and roleplay pages ----------
AI_HARNESS = ROOT / "tests" / "frontend" / "ai_harness.js"


def test_the_ai_harness_itself_parses():
    expr = f"var s=$.NSString.stringWithContentsOfFileEncodingError('{AI_HARNESS}',4,null).js; try{{new Function(s);'OK'}}catch(e){{'ERR '+e}}"
    assert js(AI_HARNESS, expr).stdout.strip() == "OK"


def run_ai(server, scenario, tmp_path):
    from .agekids import dob_for_age
    from .aih import script as roleplay_script
    from backend.db import connect
    base, work = server
    import tests.aih as aih
    saved = aih.main.DB_PATH
    aih.main.DB_PATH = work / "test.db"
    try:
        key = {"transport": [texts for _, _, texts in roleplay_script("transport")]}
    finally:
        aih.main.DB_PATH = saved
    env = {**os.environ, "BASE": base, "ROOT": str(ROOT), "WORKDIR": str(tmp_path), "SCENARIO": scenario, "KEY": json.dumps(key),
           "DOB_CHILD": dob_for_age(6), "DOB_TEEN": dob_for_age(14), "DOB_ADULT": dob_for_age(30)}
    env.pop("AI_PROVIDER", None)
    r = subprocess.run(["osascript", "-l", "JavaScript", str(AI_HARNESS)], capture_output=True, text=True, timeout=240, env=env)
    lines = [l for l in (r.stdout + r.stderr).splitlines() if l.startswith("## ")]
    assert lines, f"the harness produced no result:\n{r.stdout}\n{r.stderr}"
    return json.loads(lines[-1][3:])["checks"]


AI_SCENARIOS = ["tutor_signed_out", "tutor_list_and_start", "tutor_conversation_and_reply", "tutor_shows_stored_facts_apart", "tutor_failure_keeps_the_text_and_a_retry_is_safe",
                "tutor_empty_message_is_not_sent", "tutor_child_gets_only_helper_questions", "tutor_someone_elses_conversation_looks_missing", "roleplay_list_and_start",
                "roleplay_a_turn_with_hint_and_progress", "roleplay_never_shows_an_unresolved_answer", "roleplay_complete_and_feedback",
                "roleplay_reopening_a_finished_session_shows_its_feedback", "roleplay_empty_reply_is_not_sent_and_errors_are_shown", "roleplay_someone_elses_session_looks_missing",
                "roleplay_signed_out", "navigation_for_parents_has_no_ai_pages",
                "adaptive_signed_out", "adaptive_new_learner_is_told_when_there_is_not_enough_evidence", "adaptive_shows_suggestions_with_the_evidence_behind_them",
                "adaptive_applying_a_suggestion", "adaptive_answering_a_drill", "adaptive_labels_a_model_ranking", "adaptive_for_a_child_is_the_same_page_without_a_model",
                "tutor_shows_the_current_suggestion_apart_from_the_chat", "tutor_for_a_child_has_no_suggestion_card", "roleplay_shows_how_an_answer_was_understood",
                "roleplay_offers_practice_for_missed_phrases"]


@pytest.mark.parametrize("scenario", AI_SCENARIOS)
def test_tutor_and_roleplay_pages(scenario, mock_server, tmp_path):
    assert_all(run_ai(mock_server, scenario, tmp_path))
