"""Recording upload validation and file storage. Audio never goes into SQLite: the database keeps only a generated file
reference (a name, never a path), the MIME type, the size and a SHA-256.

Validation does not trust the client: the declared Content-Type must be on the allow-list AND the file's own leading bytes
must match it, the size is measured here, and file names are generated here. Uploaded bytes are only ever written to disk and
read back; they are never executed, parsed as code, or served."""
import hashlib
import os
import re
import uuid
from dataclasses import dataclass
from pathlib import Path

from .. import settings


class UploadError(Exception):
    """A rejected upload. `status` is the HTTP status the router should use; `message` is safe to show."""

    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


# declared MIME type -> (canonical MIME, file extension). Anything else is rejected.
ALLOWED = {
    "audio/webm": ("audio/webm", "webm"),
    "audio/ogg": ("audio/ogg", "ogg"),
    "audio/mp4": ("audio/mp4", "mp4"),
    "audio/mpeg": ("audio/mpeg", "mp3"),
    "audio/wav": ("audio/wav", "wav"),
    "audio/x-wav": ("audio/wav", "wav"),
    "audio/wave": ("audio/wav", "wav"),
}

_REF = re.compile(r"rec_[0-9a-f]{32}\.(webm|ogg|mp4|mp3|wav)")


def _matches_signature(mime, data):
    """Does the content start like the type it claims to be?"""
    if mime == "audio/webm":
        return data[:4] == b"\x1a\x45\xdf\xa3"                       # EBML header (WebM / Matroska)
    if mime == "audio/ogg":
        return data[:4] == b"OggS"
    if mime == "audio/wav":
        return data[:4] == b"RIFF" and data[8:12] == b"WAVE"
    if mime == "audio/mp4":
        return data[4:8] == b"ftyp"
    if mime == "audio/mpeg":
        return data[:3] == b"ID3" or (len(data) > 1 and data[0] == 0xFF and (data[1] & 0xE0) == 0xE0)
    return False


@dataclass(frozen=True)
class ValidatedRecording:
    mime: str
    ext: str
    size: int
    sha256: str


def validate_upload(data, content_type, max_bytes=None):
    """Raises UploadError (413 too big, 415 unsupported/mismatched type, 422 empty) or returns what was verified."""
    max_bytes = max_bytes or settings.MAX_RECORDING_BYTES
    if len(data) > max_bytes:
        raise UploadError(413, f"The recording is too large (limit {max_bytes // 1_000_000} MB).")
    if len(data) < settings.MIN_RECORDING_BYTES:
        raise UploadError(422, "The recording is empty.")
    declared = (content_type or "").split(";")[0].strip().lower()        # drop parameters such as ;codecs=opus
    if declared not in ALLOWED:
        raise UploadError(415, "That audio type is not supported.")
    mime, ext = ALLOWED[declared]
    if not _matches_signature(mime, data):
        raise UploadError(415, "The file does not look like the audio type it claims to be.")
    return ValidatedRecording(mime=mime, ext=ext, size=len(data), sha256=hashlib.sha256(data).hexdigest())


def validate_duration(duration_ms):
    """Client-reported duration: optional, but if given it must be a sensible positive number within the maximum."""
    if duration_ms is None:
        return None
    if not 1 <= duration_ms <= settings.MAX_RECORDING_MS:
        raise UploadError(422, f"The recording length must be between 1 ms and {settings.MAX_RECORDING_MS // 1000} seconds.")
    return duration_ms


class LocalRecordingStorage:
    """Recordings as files in one directory. References are generated here and re-validated on every use, so a reference
    coming from anywhere (even a corrupted database row) can never point outside the directory."""

    def __init__(self, base_dir):
        self.base = Path(base_dir)

    def _path(self, ref):
        if not isinstance(ref, str) or not _REF.fullmatch(ref):
            raise ValueError("invalid recording reference")
        path = (self.base / ref).resolve()
        if path.parent != self.base.resolve():
            raise ValueError("recording reference escapes the storage directory")
        return path

    def save(self, data, ext):
        if ext not in {e for _, e in ALLOWED.values()}:
            raise ValueError("unsupported extension")
        self.base.mkdir(mode=0o700, parents=True, exist_ok=True)
        ref = f"rec_{uuid.uuid4().hex}.{ext}"
        fd = os.open(self._path(ref), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)   # exclusive, owner-only
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        return ref

    def read(self, ref):
        return self._path(ref).read_bytes()

    def delete(self, ref):
        try:
            self._path(ref).unlink()
        except FileNotFoundError:
            pass


def default_storage():
    return LocalRecordingStorage(settings.recordings_dir())
