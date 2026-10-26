"""Helpers for speaking tests: tiny synthetic audio (never a real recording) and API shortcuts."""
from pathlib import Path

from backend import main
from backend.db import connect

SIGNATURES = {"webm": b"\x1a\x45\xdf\xa3", "ogg": b"OggS", "wav": b"RIFF\x00\x00\x00\x00WAVE", "mp4": b"\x00\x00\x00\x20ftyp", "mp3": b"ID3"}
MIMES = {"webm": "audio/webm", "ogg": "audio/ogg", "wav": "audio/wav", "mp4": "audio/mp4", "mp3": "audio/mpeg"}
PROFILE = {"native_language": "en", "target_language": "hi", "cefr_level": "A1", "date_of_birth": "2000-05-20"}


def db():
    return connect(main.DB_PATH)


def audio(text=None, kind="webm", conf=None, alts=(), extra=b"", pad=40, pron=None):
    """Synthetic audio: the right leading bytes for the format, then a payload the MOCK provider reads its answer from."""
    body = b""
    if text is not None:
        body += b"MOCKSTT:" + text.encode("utf-8") + b"\n"
    if conf is not None:
        body += b"MOCKCONF:" + str(conf).encode() + b"\n"
    for a in alts:
        body += b"MOCKALT:" + a.encode("utf-8") + b"\n"
    if pron:  # controlled pronunciation signal for the MOCK pronunciation provider: {"overall": 80, "components": {...}, "words": [(w, n)], "fail": True}
        if pron.get("overall") is not None:
            body += b"MOCKPRON:" + str(pron["overall"]).encode() + b"\n"
        for name, score in (pron.get("components") or {}).items():
            body += b"MOCKPRONC:" + name.encode() + b"=" + str(score).encode() + b"\n"
        for word, score in (pron.get("words") or []):
            body += b"MOCKPRONW:" + word.encode("utf-8") + b"=" + str(score).encode() + b"\n"
        if pron.get("fail"):
            body += b"MOCKPRONFAIL\n"
    return SIGNATURES[kind] + body + extra + b"\x00" * pad


def prompt_items(client):
    return client.get("/api/speaking/prompts").json()["prompts"]


def create(client, item_id=None):
    r = client.post("/api/speaking/sessions", json={} if item_id is None else {"item_id": item_id})
    assert r.status_code == 201, r.text
    return r.json()["session"]


def upload(client, session_id, data=None, content_type="audio/webm", duration_ms=2000):
    data = audio("hello") if data is None else data
    url = f"/api/speaking/sessions/{session_id}/recording" + ("" if duration_ms is None else f"?duration_ms={duration_ms}")
    return client.post(url, content=data, headers={"content-type": content_type})


def transcribe(client, session_id):
    return client.post(f"/api/speaking/sessions/{session_id}/transcribe")


def cancel(client, session_id):
    return client.post(f"/api/speaking/sessions/{session_id}/cancel")


def get(client, session_id):
    return client.get(f"/api/speaking/sessions/{session_id}")


def run_flow(client, text="नमस्ते", item_id=None, **audio_kw):
    """create -> upload -> transcribe with the mock provider; returns the final session view."""
    s = create(client, item_id)
    assert upload(client, s["id"], audio(text, **audio_kw)).status_code == 200
    r = transcribe(client, s["id"])
    assert r.status_code == 200, r.text
    return r.json()["session"]


def recordings(tmp_dir):
    d = Path(tmp_dir) / "recordings"
    return sorted(p.name for p in d.iterdir()) if d.exists() else []


def assess(client, session_id):
    return client.post(f"/api/speaking/sessions/{session_id}/assess-pronunciation")


def pronunciation(client, session_id):
    return client.get(f"/api/speaking/sessions/{session_id}/pronunciation")


def transcribed(client, text="नमस्ते", pron=None, item_id=None, **audio_kw):
    """create -> upload (with optional pronunciation markers) -> transcribe; returns the completed session view."""
    s = create(client, item_id)
    assert upload(client, s["id"], audio(text, pron=pron, **audio_kw)).status_code == 200
    r = transcribe(client, s["id"])
    assert r.status_code == 200 and r.json()["session"]["stage"] == "completed", r.text
    return r.json()["session"]
