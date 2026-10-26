import os
import stat
from pathlib import Path

import pytest

from backend import settings
from backend.speaking.storage import ALLOWED, LocalRecordingStorage, UploadError, default_storage, validate_duration, validate_upload

from .spk import MIMES, SIGNATURES, audio

REPO = Path(__file__).resolve().parent.parent


def rejected(data, ctype, status):
    with pytest.raises(UploadError) as e:
        validate_upload(data, ctype)
    assert e.value.status == status, e.value.message
    return e.value.message


# ---------- content validation ----------
@pytest.mark.parametrize("kind", list(SIGNATURES))
def test_each_supported_format_is_accepted(kind):
    v = validate_upload(audio("x", kind=kind), MIMES[kind])
    assert v.mime == MIMES[kind] and v.ext == {"webm": "webm", "ogg": "ogg", "wav": "wav", "mp4": "mp4", "mp3": "mp3"}[kind]
    assert len(v.sha256) == 64 and v.size == len(audio("x", kind=kind))


def test_codec_parameters_and_case_are_handled():
    assert validate_upload(audio("x"), "Audio/WebM; codecs=opus").mime == "audio/webm"
    assert validate_upload(audio("x", kind="wav"), "audio/x-wav").mime == "audio/wav"      # aliases normalise
    assert validate_upload(audio("x", kind="mp3"), "audio/mpeg").ext == "mp3"


def test_mpeg_frame_sync_is_accepted_too():
    assert validate_upload(b"\xff\xfb" + b"\x00" * 40, "audio/mpeg").mime == "audio/mpeg"


@pytest.mark.parametrize("ctype", ["text/html", "text/plain", "application/octet-stream", "application/javascript", "image/png", "video/webm",
                                   "audio/midi", "audio/", "", None, "multipart/form-data", "audio"])
def test_unsafe_or_unsupported_mime_types_are_rejected(ctype):
    rejected(audio("x"), ctype, 415)


@pytest.mark.parametrize("declared,actual", [("audio/webm", "wav"), ("audio/wav", "webm"), ("audio/ogg", "mp4"), ("audio/mp4", "ogg"), ("audio/mpeg", "webm")])
def test_the_content_must_match_the_declared_type(declared, actual):
    rejected(audio("x", kind=actual), declared, 415)


@pytest.mark.parametrize("payload", [b"<script>alert(1)</script>" + b" " * 30, b"#!/bin/sh\nrm -rf /\n" + b"x" * 30, b"MZ" + b"\x00" * 40, b"%PDF-1.4" + b"x" * 40])
def test_executable_or_markup_content_is_rejected_whatever_it_claims(payload):
    for declared in ("audio/webm", "audio/wav", "audio/mpeg", "audio/ogg", "audio/mp4"):
        rejected(payload, declared, 415)


def test_empty_and_header_only_recordings_are_rejected():
    rejected(b"", "audio/webm", 422)
    rejected(SIGNATURES["webm"], "audio/webm", 422)
    rejected(b"x" * (settings.MIN_RECORDING_BYTES - 1), "audio/webm", 422)
    validate_upload(SIGNATURES["webm"] + b"\x00" * settings.MIN_RECORDING_BYTES, "audio/webm")      # just enough is accepted


def test_size_limit_is_enforced_exactly():
    at_limit = SIGNATURES["webm"] + b"\x00" * (settings.MAX_RECORDING_BYTES - 4)
    assert validate_upload(at_limit, "audio/webm").size == settings.MAX_RECORDING_BYTES
    rejected(at_limit + b"\x00", "audio/webm", 413)
    with pytest.raises(UploadError) as e:
        validate_upload(audio("x"), "audio/webm", max_bytes=10)
    assert e.value.status == 413


def test_duration_validation():
    assert validate_duration(None) is None and validate_duration(1) == 1 and validate_duration(settings.MAX_RECORDING_MS) == settings.MAX_RECORDING_MS
    for bad in (0, -1, settings.MAX_RECORDING_MS + 1, 10**9):
        with pytest.raises(UploadError) as e:
            validate_duration(bad)
        assert e.value.status == 422


def test_allow_list_contains_only_audio_types():
    assert all(k.startswith("audio/") for k in ALLOWED)


# ---------- storage and path safety ----------
@pytest.fixture
def store(tmp_path):
    return LocalRecordingStorage(tmp_path / "rec")


def test_round_trip_and_generated_references(store):
    data = audio("x")
    ref = store.save(data, "webm")
    assert ref.startswith("rec_") and ref.endswith(".webm") and "/" not in ref and ".." not in ref and len(ref) <= 64
    assert store.read(ref) == data
    store.delete(ref)
    with pytest.raises(FileNotFoundError):
        store.read(ref)
    store.delete(ref)                                        # deleting twice is harmless


def test_references_are_random_and_files_are_private(store):
    refs = {store.save(audio("x"), "webm") for _ in range(20)}
    assert len(refs) == 20
    ref = next(iter(refs))
    mode = stat.S_IMODE(os.stat(store.base / ref).st_mode)
    assert mode == 0o600 and stat.S_IMODE(os.stat(store.base).st_mode) == 0o700


@pytest.mark.parametrize("ref", ["../secret.webm", "../../etc/passwd", "/etc/passwd", "rec_" + "a" * 32 + ".webm/../../x", "rec_" + "a" * 32 + ".exe",
                                 "rec_" + "A" * 32 + ".webm", "rec_short.webm", "rec_" + "a" * 32 + ".webm\x00.png", "rec_" + "a" * 32 + ".py",
                                 "..", ".", "", "C:\\windows\\system32", "rec_" + "a" * 32 + "\\..\\x.webm", None, 7])
def test_unsafe_references_are_refused_everywhere(store, ref):
    for operation in (store.read, store.delete):
        with pytest.raises(ValueError):
            operation(ref)


def test_a_planted_file_outside_the_directory_is_never_reachable(tmp_path, store):
    secret = tmp_path / "secret.webm"
    secret.write_bytes(b"top secret")
    store.save(audio("x"), "webm")                           # creates the directory
    for ref in (f"../{secret.name}", str(secret), f"rec_{'a' * 32}.webm/../../{secret.name}"):
        with pytest.raises(ValueError):
            store.read(ref)
    assert secret.read_bytes() == b"top secret"              # not read, not deleted
    with pytest.raises(ValueError):
        store.delete("../secret.webm")
    assert secret.exists()


def test_a_symlink_cannot_redirect_a_reference_outside(tmp_path, store):
    store.save(audio("x"), "webm")
    target = tmp_path / "outside.webm"
    target.write_bytes(b"outside")
    link = store.base / ("rec_" + "c" * 32 + ".webm")
    link.symlink_to(target)
    with pytest.raises(ValueError):
        store.read(link.name)                                # resolves outside the directory, so it is refused
    assert target.read_bytes() == b"outside"


def test_unsupported_extensions_cannot_be_saved(store):
    for ext in ("exe", "py", "sh", "html", "../x", ""):
        with pytest.raises(ValueError):
            store.save(b"x", ext)
    assert not list(store.base.glob("*")) if store.base.exists() else True


def test_saved_content_is_never_interpreted(store):
    ref = store.save(SIGNATURES["webm"] + b"__import__('os').system('touch /tmp/pwned')", "webm")
    assert store.read(ref).startswith(SIGNATURES["webm"]) and not Path("/tmp/pwned").exists()


def test_default_storage_is_outside_the_repository_and_database(monkeypatch):
    monkeypatch.delenv("RECORDINGS_DIR")
    base = default_storage().base.resolve()
    assert REPO not in base.parents and base != REPO
    assert base.parts[-2:] == (".lingobuddy", "recordings")


def test_the_test_suite_never_writes_recordings_inside_the_repo(tmp_path):
    assert REPO not in default_storage().base.resolve().parents and str(tmp_path) in str(default_storage().base)
    assert not list(REPO.glob("**/rec_*.webm")) and not (REPO / "recordings").exists()
