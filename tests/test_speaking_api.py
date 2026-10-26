import json
import threading
import time

import pytest
from fastapi.testclient import TestClient

from backend import main, settings
from backend.personalization import clock
from backend.speaking import service as speaking_service
from backend.speaking.stt import SttCapabilities, SttError, Transcription

from .conftest import PASSWORD, register
from .spk import PROFILE, audio, cancel, create, db, get, prompt_items, recordings, run_flow, transcribe, upload

ALL_MIMES = {"audio/webm", "audio/ogg", "audio/mp4", "audio/mpeg", "audio/wav"}


@pytest.fixture
def speaker(client, monkeypatch):
    monkeypatch.setenv("STT_PROVIDER", "mock")
    register(client, "l@example.com")
    assert client.put("/api/profile", json=PROFILE).status_code == 200
    return client


class Stub:
    name = "stub"

    def __init__(self, fn, languages=None, mimes=ALL_MIMES, max_bytes=25_000_000):
        self.fn = fn
        self.capabilities = SttCapabilities(mime_types=frozenset(mimes), languages=languages, max_bytes=max_bytes)

    def transcribe(self, audio_bytes, mime_type, locale):
        return self.fn(audio_bytes, mime_type, locale)


def use(monkeypatch, provider):
    monkeypatch.setattr(speaking_service, "STT_FACTORY", lambda: provider)


def raising(err):
    def fn(*args):
        raise err
    return fn


def assert_in_step(session_id):
    """The generic audio_sessions row must always agree with the speaking stage."""
    with db() as conn:
        r = conn.execute("SELECT ss.stage, a.status, a.kind, a.ended_at, a.started_at, a.duration_ms FROM speaking_sessions ss JOIN audio_sessions a ON a.id = ss.session_id WHERE ss.session_id = ?", (session_id,)).fetchone()
    expected = {"created": "started", "recorded": "started", "processing": "started", "completed": "completed", "failed": "failed", "cancelled": "abandoned"}[r["stage"]]
    assert r["status"] == expected and r["kind"] == "speaking"
    assert (r["ended_at"] is None) == (expected == "started")
    if r["ended_at"]:
        assert r["ended_at"] >= r["started_at"] and r["duration_ms"] is not None and r["duration_ms"] >= 0


# ---------- access control ----------
def _call(c, method, path, body):
    if method == "post_raw":
        return c.post(path, content=audio("x"), headers={"content-type": "audio/webm"})
    return getattr(c, method)(path, **({"json": body} if body is not None else {}))


ENDPOINTS = [("get", "/api/speaking/prompts", None), ("get", "/api/speaking/progress", None), ("post", "/api/speaking/sessions", {}),
             ("get", "/api/speaking/sessions", None), ("get", "/api/speaking/sessions/1", None), ("post_raw", "/api/speaking/sessions/1/recording", None),
             ("post", "/api/speaking/sessions/1/transcribe", None), ("post", "/api/speaking/sessions/1/cancel", None)]


@pytest.mark.parametrize("method,path,body", ENDPOINTS)
def test_anonymous_rejected_even_in_demo_mode(client, method, path, body):
    assert _call(client, method, path, body).status_code == 401


@pytest.mark.parametrize("method,path,body", ENDPOINTS)
def test_parent_rejected(client, method, path, body):
    register(client, "p@example.com", role="parent")
    assert _call(client, method, path, body).status_code == 403


@pytest.mark.parametrize("method,path,body", ENDPOINTS)
def test_admin_rejected(client, client2, make_admin, method, path, body):
    make_admin()
    client2.post("/api/auth/login", json={"email": "admin@example.com", "password": PASSWORD})
    assert _call(client2, method, path, body).status_code == 403


@pytest.mark.parametrize("method,path,body", ENDPOINTS)
def test_profile_required(client, method, path, body):
    register(client, "noprofile@example.com")
    assert _call(client, method, path, body).status_code == 409


@pytest.mark.parametrize("method,path,body", ENDPOINTS)
def test_access_ends_at_logout(speaker, method, path, body):
    speaker.post("/api/auth/logout")
    assert _call(speaker, method, path, body).status_code == 401


# ---------- prompts and session creation ----------
def test_prompts_are_existing_phrases_only(speaker):
    body = speaker.get("/api/speaking/prompts").json()
    prompts = body["prompts"]
    assert len(prompts) == 35                                               # 30 pack phrases + the 5 Help-me-now phrases
    assert prompts[0]["item"]["pronunciation"] == "Namaste, aap kaise hain?" and all(not p["practised"] for p in prompts)
    assert set(prompts[0]["item"]) == {"id", "text", "pronunciation", "meaning", "natural"}
    assert any(p["item"]["pronunciation"] == "Mujhe madad chahiye!" for p in prompts)                # from the Emergency situation
    assert not any(p["item"]["pronunciation"] in ("namaste", "bhaiya") for p in prompts)            # single words are not prompts
    assert body["stt"] == {"provider": "mock", "available": True, "max_recording_ms": settings.MAX_RECORDING_MS, "max_bytes": settings.MAX_RECORDING_BYTES}


def test_stt_availability_is_reported_honestly(speaker, monkeypatch):
    monkeypatch.delenv("STT_PROVIDER")
    assert speaker.get("/api/speaking/prompts").json()["stt"]["available"] is False
    assert speaker.get("/api/speaking/prompts").json()["stt"]["provider"] is None


def test_no_prompts_for_a_language_without_content(speaker):
    speaker.put("/api/profile", json={**PROFILE, "target_language": "hinglish"})
    assert speaker.get("/api/speaking/prompts").json()["prompts"] == []
    assert speaker.post("/api/speaking/sessions", json={}).status_code == 422


def test_create_session_picks_the_first_unpractised_phrase(speaker):
    s = create(speaker)
    assert s["stage"] == "created" and s["prompt"]["item"]["pronunciation"] == "Namaste, aap kaise hain?"
    assert s["recording"] is None and s["transcript"] is None and s["error"] is None and s["attempts"] == 0
    assert s["prompt"]["audio"]["kind"] == "browser_tts" and s["prompt"]["locale"] == "hi-IN"       # a model to listen to first
    assert set(s) == {"id", "stage", "prompt", "recording", "transcript", "error", "attempts", "created_at", "updated_at"}
    assert_in_step(s["id"])
    run_flow(speaker, "x")
    assert create(speaker)["prompt"]["item"]["pronunciation"] == "Mera naam Alex hai."             # the next phrase, not the same one again


def test_create_with_an_explicit_available_phrase(speaker):
    target = prompt_items(speaker)[7]["item"]
    assert create(speaker, target["id"])["prompt"]["item"]["id"] == target["id"]


@pytest.mark.parametrize("make_body", [lambda s: {"item_id": 999999}, lambda s: {"item_id": 0}, lambda s: {"item_id": "x"},
                                       lambda s: {"item_id": s["word"]},                                   # a single word is not a speaking prompt
                                       lambda s: {"user_id": 1}, lambda s: {"stage": "completed"}, lambda s: {"transcript": "cheat"}])
def test_invalid_session_requests_are_rejected(speaker, make_body):
    with db() as conn:
        word = conn.execute("SELECT id FROM vocabulary_items WHERE kind='word' LIMIT 1").fetchone()[0]
    assert speaker.post("/api/speaking/sessions", json=make_body({"word": word})).status_code == 422
    with db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM speaking_sessions").fetchone()[0] == 0 and conn.execute("SELECT COUNT(*) FROM audio_sessions").fetchone()[0] == 0


def test_a_phrase_of_another_language_is_not_available(speaker):
    with db() as conn:
        es = conn.execute("SELECT id FROM languages WHERE code='es'").fetchone()[0]
        conn.execute("INSERT INTO language_levels(language_id, cefr_code) VALUES (?, 'A1')", (es,))
        conn.execute("INSERT INTO vocabulary_items(language_id, cefr_code, kind, text) VALUES (?, 'A1', 'phrase', 'hola amigo')", (es,))
        item = conn.execute("SELECT id FROM vocabulary_items WHERE text='hola amigo'").fetchone()[0]
    assert speaker.post("/api/speaking/sessions", json={"item_id": item}).status_code == 422


def test_unpublished_content_does_not_offer_prompts(speaker):
    with db() as conn:
        conn.execute("UPDATE lessons SET status='draft'")
        conn.execute("UPDATE situations SET status='draft'")
    assert speaker.get("/api/speaking/prompts").json()["prompts"] == []


# ---------- the happy path ----------
def test_full_pipeline_with_the_mock_provider(speaker, tmp_path, monkeypatch):
    monkeypatch.setenv("SPEAKING_KEEP_AUDIO", "1")
    s = create(speaker)
    sid = s["id"]
    up = upload(speaker, sid, audio("नमस्ते, आप कैसे हैं?", conf=0.88), duration_ms=2300)
    assert up.status_code == 200
    rec = up.json()["session"]
    assert rec["stage"] == "recorded" and rec["recording"] == {"mime_type": "audio/webm", "bytes": len(audio("नमस्ते, आप कैसे हैं?", conf=0.88)),
                                                            "duration_ms": 2300, "recorded_at": rec["recording"]["recorded_at"], "kept": True}
    assert_in_step(sid)
    assert len(recordings(tmp_path)) == 1
    done = transcribe(speaker, sid).json()["session"]
    assert done["stage"] == "completed" and done["error"] is None and done["attempts"] == 1
    assert done["transcript"] == {"text": "नमस्ते, आप कैसे हैं?", "confidence": 0.88, "provider": "mock", "locale": "hi-IN"}
    assert_in_step(sid)
    assert get(speaker, sid).json()["session"] == done
    with db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM stt_runs WHERE status='completed'").fetchone()[0] == 1
        assert conn.execute("SELECT text FROM speaking_transcripts").fetchone()[0] == "नमस्ते, आप कैसे हैं?"
        assert conn.execute("SELECT duration_ms FROM audio_sessions WHERE id=?", (sid,)).fetchone()[0] == 2300        # the recording length


def test_the_response_shows_what_was_heard_not_a_verdict(speaker):
    done = run_flow(speaker, "something completely different")
    text = json.dumps(done, ensure_ascii=False)
    assert done["transcript"]["text"] == "something completely different" and done["prompt"]["item"]["text"] != done["transcript"]["text"]
    for forbidden in ("score", "correct", "match", "accuracy", "pronunciation_quality", "similarity", "grade", "passed"):
        assert f'"{forbidden}"' not in text


def test_no_confidence_unless_the_provider_supplies_one(speaker):
    assert run_flow(speaker, "x")["transcript"]["confidence"] is None


def test_alternatives_are_stored_as_further_ranks_and_only_the_best_is_shown(speaker):
    done = run_flow(speaker, "best", alts=("second", "third"))
    assert done["transcript"]["text"] == "best"
    with db() as conn:
        assert [tuple(r) for r in conn.execute("SELECT rank, text FROM speaking_transcripts ORDER BY rank")] == [(1, "best"), (2, "second"), (3, "third")]


def test_provider_output_is_sanitised_before_storing(speaker, monkeypatch):
    use(monkeypatch, Stub(lambda *a: Transcription(text="x" * 5000, confidence=1.7)))
    s = create(speaker)
    upload(speaker, s["id"])
    done = transcribe(speaker, s["id"]).json()["session"]
    assert done["stage"] == "completed" and len(done["transcript"]["text"]) == 2000 and done["transcript"]["confidence"] is None    # nonsense confidence is dropped
    use(monkeypatch, Stub(lambda *a: Transcription(text="ok", confidence=True)))
    s = create(speaker)
    upload(speaker, s["id"])
    assert transcribe(speaker, s["id"]).json()["session"]["transcript"]["confidence"] is None


# ---------- recordings: storage and retention ----------
def test_the_recording_is_deleted_after_transcription_by_default(speaker, tmp_path):
    s = create(speaker)
    upload(speaker, s["id"], audio("hello"))
    assert len(recordings(tmp_path)) == 1
    done = transcribe(speaker, s["id"]).json()["session"]
    assert recordings(tmp_path) == [] and done["recording"]["kept"] is False and done["transcript"]["text"] == "hello"
    with db() as conn:
        row = conn.execute("SELECT audio_ref, audio_deleted_at, audio_bytes, audio_sha256 FROM speaking_sessions").fetchone()
    assert row["audio_ref"] is None and row["audio_deleted_at"] and row["audio_bytes"] and row["audio_sha256"]       # metadata stays, the voice data goes


def test_keeping_recordings_is_opt_in(speaker, tmp_path, monkeypatch):
    monkeypatch.setenv("SPEAKING_KEEP_AUDIO", "1")
    s = create(speaker)
    upload(speaker, s["id"])
    transcribe(speaker, s["id"])
    assert len(recordings(tmp_path)) == 1


def test_cancelling_deletes_the_recording(speaker, tmp_path):
    s = create(speaker)
    upload(speaker, s["id"])
    assert len(recordings(tmp_path)) == 1
    assert cancel(speaker, s["id"]).json()["session"]["stage"] == "cancelled"
    assert recordings(tmp_path) == []
    assert_in_step(s["id"])


def test_a_failed_session_keeps_its_recording_for_a_retry(speaker, tmp_path, monkeypatch):
    use(monkeypatch, Stub(raising(SttError("provider_error", "x"))))
    s = create(speaker)
    upload(speaker, s["id"])
    assert transcribe(speaker, s["id"]).json()["session"]["stage"] == "failed"
    assert len(recordings(tmp_path)) == 1


def test_no_raw_audio_is_stored_in_sqlite(speaker, tmp_path, monkeypatch):
    monkeypatch.setenv("SPEAKING_KEEP_AUDIO", "1")
    marker = b"UNIQUE-RAW-AUDIO-MARKER-7f3a9c"
    s = create(speaker)
    upload(speaker, s["id"], audio("hello", extra=marker * 20))
    transcribe(speaker, s["id"])
    assert marker in (tmp_path / "recordings" / recordings(tmp_path)[0]).read_bytes()        # the audio is in the file...
    assert marker not in main.DB_PATH.read_bytes()                                            # ...and nowhere in the database file
    for wal in main.DB_PATH.parent.glob(main.DB_PATH.name + "-*"):
        assert marker not in wal.read_bytes()


def test_uploads_get_generated_names_whatever_the_client_says(speaker, tmp_path):
    s = create(speaker)
    r = speaker.post(f"/api/speaking/sessions/{s['id']}/recording?duration_ms=1500", content=audio("x"),
                     headers={"content-type": "audio/webm", "content-disposition": 'attachment; filename="../../evil.webm"', "x-filename": "../../../etc/passwd"})
    assert r.status_code == 200
    (name,) = recordings(tmp_path)
    assert name.startswith("rec_") and "evil" not in name and "passwd" not in name
    assert not (tmp_path / "evil.webm").exists() and not (tmp_path.parent / "evil.webm").exists()


# ---------- upload validation over HTTP ----------
def untouched(speaker, tmp_path, sid):
    assert recordings(tmp_path) == [] and get(speaker, sid).json()["session"]["stage"] == "created"


@pytest.mark.parametrize("ctype", ["text/html", "application/octet-stream", "application/javascript", "video/webm", "image/png", ""])
def test_unsafe_mime_types_are_rejected(speaker, tmp_path, ctype):
    s = create(speaker)
    assert upload(speaker, s["id"], content_type=ctype).status_code == 415
    untouched(speaker, tmp_path, s["id"])


def test_content_that_does_not_match_the_declared_type_is_rejected(speaker, tmp_path):
    s = create(speaker)
    assert upload(speaker, s["id"], audio("x", kind="wav"), "audio/webm").status_code == 415
    assert upload(speaker, s["id"], b"<script>alert(1)</script>" + b" " * 30, "audio/webm").status_code == 415
    untouched(speaker, tmp_path, s["id"])


def test_empty_recordings_are_rejected(speaker, tmp_path):
    s = create(speaker)
    assert upload(speaker, s["id"], b"").status_code == 422
    assert upload(speaker, s["id"], b"\x1a\x45\xdf\xa3").status_code == 422
    untouched(speaker, tmp_path, s["id"])


def test_oversized_uploads_are_rejected(speaker, tmp_path, monkeypatch):
    s = create(speaker)
    monkeypatch.setattr(settings, "MAX_RECORDING_BYTES", 300)
    assert upload(speaker, s["id"], audio("x", pad=600)).status_code == 413
    assert upload(speaker, s["id"], audio("x", pad=200)).status_code == 200            # under the limit is fine
    untouched_after = get(speaker, s["id"]).json()["session"]["stage"]
    assert untouched_after == "recorded"


def test_the_real_size_limit_rejects_a_6_mb_upload(speaker, tmp_path):
    s = create(speaker)
    big = b"\x1a\x45\xdf\xa3" + b"\x00" * 6_000_000
    assert upload(speaker, s["id"], big).status_code == 413
    untouched(speaker, tmp_path, s["id"])


@pytest.mark.parametrize("duration", [0, -5, settings.MAX_RECORDING_MS + 1, 10**9])
def test_out_of_range_durations_are_rejected(speaker, tmp_path, duration):
    s = create(speaker)
    assert upload(speaker, s["id"], duration_ms=duration).status_code == 422
    untouched(speaker, tmp_path, s["id"])


def test_a_malformed_duration_is_rejected_and_a_missing_one_is_allowed(speaker):
    s = create(speaker)
    assert speaker.post(f"/api/speaking/sessions/{s['id']}/recording?duration_ms=abc", content=audio("x"), headers={"content-type": "audio/webm"}).status_code == 422
    r = upload(speaker, s["id"], duration_ms=None)
    assert r.status_code == 200 and r.json()["session"]["recording"]["duration_ms"] is None


def test_session_ids_in_the_url_are_validated(speaker):
    for bad in ("abc", "../../etc/passwd", "1.5", "-"):
        assert speaker.get(f"/api/speaking/sessions/{bad}").status_code in (404, 422)
    assert speaker.get("/api/speaking/sessions/99999").status_code == 404
    assert upload(speaker, 99999).status_code == 404 and transcribe(speaker, 99999).status_code == 404 and cancel(speaker, 99999).status_code == 404


# ---------- state machine ----------
def test_transcribing_before_recording_is_refused(speaker):
    s = create(speaker)
    assert transcribe(speaker, s["id"]).status_code == 409
    assert get(speaker, s["id"]).json()["session"]["stage"] == "created"


def test_a_second_recording_is_refused(speaker, tmp_path):
    s = create(speaker)
    assert upload(speaker, s["id"]).status_code == 200
    assert upload(speaker, s["id"], audio("other")).status_code == 409
    assert len(recordings(tmp_path)) == 1                                   # the refused upload left nothing behind


def test_a_finished_session_accepts_nothing_more(speaker, tmp_path):
    done = run_flow(speaker, "x")
    sid = done["id"]
    assert upload(speaker, sid).status_code == 409 and transcribe(speaker, sid).status_code == 409 and cancel(speaker, sid).status_code == 409
    assert get(speaker, sid).json()["session"]["stage"] == "completed" and recordings(tmp_path) == []


def test_a_cancelled_session_is_final(speaker):
    s = create(speaker)
    assert cancel(speaker, s["id"]).json()["session"]["stage"] == "cancelled"
    assert upload(speaker, s["id"]).status_code == 409 and transcribe(speaker, s["id"]).status_code == 409 and cancel(speaker, s["id"]).status_code == 409
    assert_in_step(s["id"])


def test_cancelling_before_recording_is_allowed(speaker):
    s = create(speaker)
    v = cancel(speaker, s["id"]).json()["session"]
    assert v["stage"] == "cancelled" and v["recording"] is None
    assert_in_step(s["id"])


def test_a_session_being_processed_cannot_be_claimed_again_or_cancelled(speaker):
    s = create(speaker)
    upload(speaker, s["id"])
    with db() as conn:
        conn.execute("UPDATE speaking_sessions SET stage='processing'")
        conn.execute("INSERT INTO stt_runs(session_id, user_id, provider, locale, status, started_at) SELECT session_id, user_id, 'mock', 'hi-IN', 'processing', '2999-01-01 00:00:00' FROM speaking_sessions")
    assert transcribe(speaker, s["id"]).status_code == 409 and cancel(speaker, s["id"]).status_code == 409 and upload(speaker, s["id"]).status_code == 409


def test_each_transition_keeps_the_audio_session_in_step(speaker, monkeypatch):
    s = create(speaker)
    assert_in_step(s["id"])
    upload(speaker, s["id"])
    assert_in_step(s["id"])
    use(monkeypatch, Stub(raising(SttError("provider_error", "x"))))
    transcribe(speaker, s["id"])
    assert_in_step(s["id"])
    use(monkeypatch, Stub(lambda *a: Transcription(text="ok")))
    transcribe(speaker, s["id"])
    assert_in_step(s["id"])


# ---------- provider failure handling ----------
def failed_view(speaker, monkeypatch, provider, **audio_kw):
    use(monkeypatch, provider)
    s = create(speaker)
    upload(speaker, s["id"], audio("x", **audio_kw))
    r = transcribe(speaker, s["id"])
    assert r.status_code == 200, r.text                                      # a provider failure is a normal, stored outcome: never a 500
    return r.json()["session"]


def test_a_failing_provider_is_handled_safely(speaker, monkeypatch):
    v = failed_view(speaker, monkeypatch, Stub(raising(SttError("provider_error", "boom"))))
    assert v["stage"] == "failed" and v["transcript"] is None
    assert v["error"] == {"code": "provider_error", "message": speaking_service.ERROR_MESSAGES["provider_error"]}
    with db() as conn:
        r = conn.execute("SELECT status, error_code, finished_at, duration_ms FROM stt_runs").fetchone()
        assert (r["status"], r["error_code"]) == ("failed", "provider_error") and r["finished_at"] is not None
        assert conn.execute("SELECT COUNT(*) FROM speaking_transcripts").fetchone()[0] == 0
    assert_in_step(v["id"])


def test_an_unexpected_provider_exception_never_leaks(speaker, monkeypatch):
    v = failed_view(speaker, monkeypatch, Stub(raising(RuntimeError("SECRET-INTERNAL-DETAIL sk-123"))))
    assert v["stage"] == "failed" and v["error"]["code"] == "provider_error"
    assert "SECRET" not in json.dumps(v) and "sk-123" not in json.dumps(v)


def test_the_provider_call_is_time_limited(speaker, monkeypatch):
    monkeypatch.setenv("STT_TIMEOUT_SECONDS", "0.1")
    started = time.monotonic()
    v = failed_view(speaker, monkeypatch, Stub(lambda *a: (time.sleep(1.0), Transcription(text="late"))[1]))
    assert time.monotonic() - started < 0.9                                  # the request did not wait for the slow provider
    assert v["stage"] == "failed" and v["error"]["code"] == "provider_timeout"


def test_no_provider_configured_is_a_controlled_state(speaker, monkeypatch):
    monkeypatch.delenv("STT_PROVIDER")
    s = create(speaker)
    upload(speaker, s["id"])
    v = transcribe(speaker, s["id"]).json()["session"]
    assert v["stage"] == "failed" and v["error"]["code"] == "provider_unavailable"
    with db() as conn:
        assert conn.execute("SELECT provider FROM stt_runs").fetchone()[0] == "none"
    monkeypatch.setenv("STT_PROVIDER", "mock")                               # configured later: the same recording can be retried
    assert transcribe(speaker, s["id"]).json()["session"]["stage"] == "completed"


def test_a_provider_without_the_language_or_format_fails_before_being_called(speaker, monkeypatch):
    calls = []
    def fn(*a):
        calls.append(a)
        return Transcription(text="x")
    assert failed_view(speaker, monkeypatch, Stub(fn, languages=frozenset({"fr"})))["error"]["code"] == "unsupported_language"
    assert failed_view(speaker, monkeypatch, Stub(fn, mimes={"audio/wav"}))["error"]["code"] == "unsupported_format"
    assert failed_view(speaker, monkeypatch, Stub(fn, max_bytes=5))["error"]["code"] == "unsupported_format"
    assert calls == []


def test_silence_is_reported_as_no_speech_not_as_a_transcript(speaker):
    s = create(speaker)
    upload(speaker, s["id"], audio(extra=b"MOCKSILENCE"))
    v = transcribe(speaker, s["id"]).json()["session"]
    assert v["stage"] == "failed" and v["error"]["code"] == "no_speech" and v["transcript"] is None
    with db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM speaking_transcripts").fetchone()[0] == 0


def test_a_missing_recording_file_is_reported(speaker, tmp_path):
    s = create(speaker)
    upload(speaker, s["id"])
    for f in (tmp_path / "recordings").iterdir():
        f.unlink()
    v = transcribe(speaker, s["id"]).json()["session"]
    assert v["stage"] == "failed" and v["error"]["code"] == "recording_unavailable"


def test_a_corrupted_reference_in_the_database_cannot_escape_the_directory(speaker, tmp_path):
    s = create(speaker)
    upload(speaker, s["id"])
    (tmp_path / "outside.webm").write_bytes(audio("stolen"))
    with db() as conn:
        with pytest.raises(Exception):
            conn.execute("UPDATE speaking_sessions SET audio_ref = '../outside.webm'")          # the database itself refuses such a reference
    with db() as conn:
        conn.execute("PRAGMA ignore_check_constraints = ON")                                      # even if a check were bypassed...
        conn.execute("UPDATE speaking_sessions SET audio_ref = 'rec_" + "9" * 32 + ".webm/../../outside.webm'")
    v = transcribe(speaker, s["id"]).json()["session"]
    assert v["stage"] == "failed" and v["error"]["code"] == "recording_unavailable"               # ...the storage layer still refuses to read it
    assert (tmp_path / "outside.webm").exists()


def test_a_failed_session_can_be_retried_and_the_history_is_kept(speaker, monkeypatch):
    use(monkeypatch, Stub(raising(SttError("provider_timeout", "t"))))
    s = create(speaker)
    upload(speaker, s["id"])
    assert transcribe(speaker, s["id"]).json()["session"]["stage"] == "failed"
    use(monkeypatch, Stub(raising(SttError("provider_error", "t"))))
    assert transcribe(speaker, s["id"]).json()["session"]["error"]["code"] == "provider_error"
    use(monkeypatch, Stub(lambda *a: Transcription(text="finally")))
    done = transcribe(speaker, s["id"]).json()["session"]
    assert done["stage"] == "completed" and done["transcript"]["text"] == "finally" and done["attempts"] == 3 and done["error"] is None
    with db() as conn:
        assert [r[0] for r in conn.execute("SELECT status FROM stt_runs ORDER BY id")] == ["failed", "failed", "completed"]
    assert_in_step(s["id"])


def test_a_stuck_processing_run_is_closed_as_a_timeout(speaker, monkeypatch):
    s = create(speaker)
    upload(speaker, s["id"])
    with db() as conn:
        conn.execute("UPDATE speaking_sessions SET stage='processing'")
        conn.execute("INSERT INTO stt_runs(session_id, user_id, provider, locale, status, started_at) SELECT session_id, user_id, 'mock', 'hi-IN', 'processing', '2026-01-01 00:00:00' FROM speaking_sessions")
    monkeypatch.setattr(clock, "now", lambda: "2026-01-01 00:00:30")
    assert get(speaker, s["id"]).json()["session"]["stage"] == "processing"            # not stale yet
    monkeypatch.setattr(clock, "now", lambda: "2026-01-01 00:05:00")
    v = get(speaker, s["id"]).json()["session"]
    assert v["stage"] == "failed" and v["error"]["code"] == "provider_timeout"
    assert_in_step(s["id"])
    assert transcribe(speaker, s["id"]).json()["session"]["stage"] == "completed"       # and the session is usable again


# ---------- concurrency ----------
def test_a_slow_provider_does_not_block_other_requests(speaker, monkeypatch):
    gate, inside = threading.Event(), threading.Event()

    def slow(*a):
        inside.set()
        gate.wait(5)
        return Transcription(text="done")

    use(monkeypatch, Stub(slow))
    monkeypatch.setenv("STT_TIMEOUT_SECONDS", "10")
    s = create(speaker)
    upload(speaker, s["id"])
    result = {}
    worker = threading.Thread(target=lambda: result.update(r=transcribe(speaker, s["id"])))
    worker.start()
    assert inside.wait(5)
    t = time.monotonic()
    assert speaker.get("/api/speaking/progress").status_code == 200 and create(speaker)["stage"] == "created"      # the write lock is not held during the provider call
    assert time.monotonic() - t < 2
    assert get(speaker, s["id"]).json()["session"]["stage"] == "processing"
    gate.set()
    worker.join(5)
    assert result["r"].json()["session"]["stage"] == "completed"


def test_two_simultaneous_transcriptions_run_the_provider_once(speaker, client2, monkeypatch):
    client2.post("/api/auth/login", json={"email": "l@example.com", "password": PASSWORD})
    gate, inside, calls = threading.Event(), threading.Event(), []

    def slow(*a):
        calls.append(1)
        inside.set()
        gate.wait(5)
        return Transcription(text="once")

    use(monkeypatch, Stub(slow))
    monkeypatch.setenv("STT_TIMEOUT_SECONDS", "10")
    s = create(speaker)
    upload(speaker, s["id"])
    out = {}
    first = threading.Thread(target=lambda: out.update(a=transcribe(speaker, s["id"])))
    first.start()
    assert inside.wait(5)
    second = transcribe(client2, s["id"])                                      # arrives while the first is still running
    gate.set()
    first.join(5)
    assert second.status_code == 409 and out["a"].json()["session"]["stage"] == "completed" and len(calls) == 1
    with db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM stt_runs").fetchone()[0] == 1


# ---------- listing and progress ----------
def test_listing_and_progress(speaker, monkeypatch):
    run_flow(speaker, "one")
    s2 = create(speaker)
    cancel(speaker, s2["id"])
    s3 = create(speaker)
    upload(speaker, s3["id"])
    use(monkeypatch, Stub(raising(SttError("provider_error", "x"))))
    transcribe(speaker, s3["id"])
    create(speaker)
    rows = speaker.get("/api/speaking/sessions").json()["sessions"]
    assert [r["stage"] for r in rows] == ["created", "failed", "cancelled", "completed"]                 # newest first
    assert set(rows[3]) == {"id", "stage", "prompt", "transcript", "created_at"} and rows[3]["transcript"] == "one" and rows[0]["transcript"] is None
    assert len(speaker.get("/api/speaking/sessions?limit=2").json()["sessions"]) == 2
    for bad in ("?limit=0", "?limit=101", "?limit=x"):
        assert speaker.get("/api/speaking/sessions" + bad).status_code == 422
    p = speaker.get("/api/speaking/progress").json()["progress"]
    assert (p["sessions_total"], p["completed"], p["failed"], p["cancelled"], p["in_progress"]) == (4, 1, 1, 1, 1)
    assert p["prompts_available"] == 35 and p["prompts_practised"] == 1 and p["last_session_at"]
    assert "score" not in p and "accuracy" not in p                                                       # progress counts practice, it does not grade it
    assert sum(1 for x in speaker.get("/api/speaking/prompts").json()["prompts"] if x["practised"]) == 1


def test_a_failed_attempt_does_not_count_as_practised(speaker, monkeypatch):
    use(monkeypatch, Stub(raising(SttError("provider_error", "x"))))
    s = create(speaker)
    upload(speaker, s["id"])
    transcribe(speaker, s["id"])
    assert speaker.get("/api/speaking/progress").json()["progress"]["prompts_practised"] == 0
    assert create(speaker)["prompt"]["item"]["pronunciation"] == "Namaste, aap kaise hain?"               # still the first unpractised phrase


# ---------- learner isolation and ownership ----------
@pytest.fixture
def two(speaker, client2):
    register(client2, "b@example.com")
    client2.put("/api/profile", json=PROFILE)
    return speaker, client2


def test_other_learners_sessions_are_invisible_and_untouchable(two, tmp_path):
    a, b = two
    mine = run_flow(a, "a-secret-words")
    fresh = create(a)
    for call in (lambda: get(b, mine["id"]), lambda: upload(b, fresh["id"]), lambda: transcribe(b, mine["id"]), lambda: cancel(b, fresh["id"])):
        assert call().status_code == 404
    assert get(a, fresh["id"]).json()["session"]["stage"] == "created" and get(a, mine["id"]).json()["session"]["transcript"]["text"] == "a-secret-words"
    assert recordings(tmp_path) == []                                        # B's upload attempt stored nothing for A's session


def test_transcripts_belong_to_their_learner(two):
    a, b = two
    mine = run_flow(a, "alpha private transcript")
    theirs = run_flow(b, "beta own transcript")
    assert mine["id"] != theirs["id"]
    assert "alpha" not in json.dumps(b.get("/api/speaking/sessions").json()) and "beta" not in json.dumps(a.get("/api/speaking/sessions").json())
    assert get(b, theirs["id"]).json()["session"]["transcript"]["text"] == "beta own transcript"
    assert get(a, theirs["id"]).status_code == 404
    with db() as conn:
        owners = {r["text"]: r["user_id"] for r in conn.execute("SELECT text, user_id FROM speaking_transcripts")}
    assert owners["alpha private transcript"] != owners["beta own transcript"]


def test_lists_and_progress_are_per_learner(two):
    a, b = two
    run_flow(a, "x")
    assert b.get("/api/speaking/sessions").json()["sessions"] == []
    assert b.get("/api/speaking/progress").json()["progress"]["sessions_total"] == 0
    assert a.get("/api/speaking/progress").json()["progress"]["sessions_total"] == 1
    assert all(not p["practised"] for p in b.get("/api/speaking/prompts").json()["prompts"])


def test_the_client_cannot_choose_the_owner(two):
    a, b = two
    with db() as conn:
        a_id = conn.execute("SELECT id FROM users WHERE email='l@example.com'").fetchone()[0]
    assert b.post("/api/speaking/sessions", json={"user_id": a_id}).status_code == 422
    assert b.post(f"/api/speaking/sessions?user_id={a_id}", json={}).status_code == 201                  # a query parameter is ignored
    with db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM speaking_sessions WHERE user_id=?", (a_id,)).fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM audio_sessions WHERE user_id=?", (a_id,)).fetchone()[0] == 0


# ---------- response hygiene ----------
def test_responses_never_expose_paths_hashes_or_identities(speaker, tmp_path, monkeypatch):
    monkeypatch.setenv("SPEAKING_KEEP_AUDIO", "1")
    done = run_flow(speaker, "x")
    blob = json.dumps([done, speaker.get("/api/speaking/sessions").json(), speaker.get("/api/speaking/progress").json(), speaker.get("/api/speaking/prompts").json()])
    for forbidden in ("audio_ref", "rec_", str(tmp_path), "recordings", "sha256", "user_id", "l@example.com", ".webm", "/Users/", "password"):
        assert forbidden not in blob, forbidden
    assert set(done["recording"]) == {"mime_type", "bytes", "duration_ms", "recorded_at", "kept"}


def test_nothing_the_learner_said_leaks_into_the_error_responses(speaker):
    s = create(speaker)
    r = upload(speaker, s["id"], audio("my private sentence", kind="wav"), "audio/webm")
    assert r.status_code == 415 and "private" not in r.text


def test_prototype_and_earlier_phases_unchanged(client):
    assert client.get("/api/state/demo-alex").status_code == 401          # Phase 14A: no shared demo state
    assert client.put("/api/state/demo-alex", json={"v": 1}).status_code == 401
    assert client.get("/api/cities").json()["cities"][0]["slug"] == "delhi" and client.get("/static/content.js").status_code == 200
    register(client, "l@example.com")
    client.put("/api/profile", json=PROFILE)
    assert (len(client.get("/api/lessons").json()["lessons"]), len(client.get("/api/situations").json()["situations"]), len(client.get("/api/listening").json()["activities"])) == (7, 8, 15)
