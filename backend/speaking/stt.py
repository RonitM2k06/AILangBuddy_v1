"""Speech-to-text behind one interface, so the speaking system never knows which engine produced a transcript.

A provider turns recorded audio into text and reports what it supports (capabilities). Failures are raised as `SttError`
with a stable, safe `code` (never a provider response body, never a key), so the pipeline can store and show them.

Providers shipped:
  * mock  deterministic, no network, for development and tests (the audio bytes carry the transcript to return);
  * groq  Whisper through Groq's OpenAI-compatible endpoint, using the httpx and GROQ_API_KEY the project already has.
Nothing is selected by default: with STT_PROVIDER unset, speaking sessions can be recorded but not transcribed, and no
audio ever leaves the machine. Adding another engine means writing one class and registering it in `get_provider`."""
from dataclasses import dataclass, field
from typing import Optional, Protocol

import httpx

from .. import settings


class SttError(Exception):
    """A controlled transcription failure. `code` is one of the codes the database accepts for stt_runs.error_code."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class Transcription:
    text: str                                   # may be empty: the pipeline turns "nothing heard" into a no_speech failure
    confidence: Optional[float] = None          # only if the provider supplies one (0..1); never invented
    alternatives: tuple = field(default_factory=tuple)   # further hypotheses, best first (rank 2, 3, ...)


@dataclass(frozen=True)
class SttCapabilities:
    mime_types: frozenset
    languages: Optional[frozenset] = None       # ISO 639-1 codes; None = any language
    max_bytes: int = 25_000_000

    def supports_language(self, locale):
        return self.languages is None or language_of(locale) in self.languages


class STTProvider(Protocol):
    name: str
    capabilities: SttCapabilities

    def transcribe(self, audio: bytes, mime_type: str, locale: str) -> Transcription:
        """Return what was said. Raise SttError for any failure; never let provider details escape."""


def language_of(locale):
    """'hi-IN' -> 'hi'."""
    return locale.split("-")[0].split("_")[0].lower()


# The languages Whisper transcribes (its published list, ISO 639-1). Hindi and Marathi are both on it; accuracy for Marathi is lower than for
# Hindi, so the transcript is shown as what was heard, never as a score.
WHISPER_LANGUAGES = frozenset("""af am ar as az ba be bg bn bo br bs ca cs cy da de el en es et eu fa fi fo fr gl gu ha haw he hi hr ht hu hy id is it
ja jw ka kk km kn ko la lb ln lo lt lv mg mi mk ml mn mr ms mt my ne nl nn no oc pa pl ps pt ro ru sa sd si sk sl sn so sq sr su sv sw ta te tg th tk
tl tr tt uk ur uz vi yi yo zh yue""".split())

_ALL_AUDIO = frozenset({"audio/webm", "audio/ogg", "audio/mp4", "audio/mpeg", "audio/wav"})


class MockSttProvider:
    """Deterministic provider for development and tests. It reads its answer from the audio bytes:
         MOCKSTT:<text>      the transcript to return (first such line)
         MOCKCONF:<0..1>     an optional confidence
         MOCKALT:<text>      an optional further hypothesis (repeatable)
         MOCKFAIL            raise a provider_error
         MOCKSILENCE         return an empty transcript
       Audio without a marker gets a clearly labelled placeholder, so nobody mistakes a mock result for speech recognition."""
    name = "mock"
    capabilities = SttCapabilities(mime_types=_ALL_AUDIO, languages=None)

    def transcribe(self, audio, mime_type, locale):
        lines = audio.split(b"\n")
        if b"MOCKFAIL" in audio:
            raise SttError("provider_error", "The mock provider was told to fail.")
        if b"MOCKSILENCE" in audio:
            return Transcription(text="")
        text, conf, alts = None, None, []
        for raw in lines:
            chunk = raw[raw.find(b"MOCK"):] if b"MOCK" in raw else b""
            if chunk.startswith(b"MOCKSTT:") and text is None:
                text = chunk[len(b"MOCKSTT:"):].decode("utf-8", "replace").strip()
            elif chunk.startswith(b"MOCKCONF:"):
                try:
                    conf = float(chunk[len(b"MOCKCONF:"):].decode("ascii", "replace").strip())
                except ValueError:
                    conf = None
            elif chunk.startswith(b"MOCKALT:"):
                alts.append(chunk[len(b"MOCKALT:"):].decode("utf-8", "replace").strip())
        if text is None:
            text = "[mock transcript]"
        return Transcription(text=text, confidence=conf, alternatives=tuple(a for a in alts if a))


class GroqWhisperProvider:
    """Whisper on Groq. Sends the recording to a third party, so it is only used when STT_PROVIDER=groq is set explicitly."""
    name = "groq"
    capabilities = SttCapabilities(mime_types=_ALL_AUDIO, languages=WHISPER_LANGUAGES, max_bytes=25_000_000)
    URL = "https://api.groq.com/openai/v1/audio/transcriptions"
    _EXT = {"audio/webm": "webm", "audio/ogg": "ogg", "audio/mp4": "mp4", "audio/mpeg": "mp3", "audio/wav": "wav"}

    def __init__(self, api_key, model=None, client=None, timeout=15.0):
        self._key, self._model, self._timeout = api_key, model or settings.stt_model(), timeout
        self._client = client            # injectable (tests use httpx.MockTransport); a short-lived client is made otherwise

    def transcribe(self, audio, mime_type, locale):
        files = {"file": (f"recording.{self._EXT.get(mime_type, 'webm')}", audio, mime_type)}
        data = {"model": self._model, "language": language_of(locale), "response_format": "json", "temperature": "0"}
        headers = {"Authorization": f"Bearer {self._key}"}
        try:
            if self._client is not None:
                resp = self._client.post(self.URL, headers=headers, data=data, files=files, timeout=self._timeout)
            else:
                with httpx.Client() as client:
                    resp = client.post(self.URL, headers=headers, data=data, files=files, timeout=self._timeout)
        except httpx.TimeoutException:
            raise SttError("provider_timeout", "The speech service took too long to answer.")
        except httpx.HTTPError:
            raise SttError("provider_unavailable", "The speech service could not be reached.")
        if resp.status_code in (401, 403):
            raise SttError("provider_unavailable", "The speech service is not authorised; check the configuration.")
        if resp.status_code >= 400:
            raise SttError("provider_error", f"The speech service returned an error ({resp.status_code}).")
        try:
            return Transcription(text=str(resp.json().get("text", "")).strip())     # Whisper gives no usable confidence: none is invented
        except (ValueError, AttributeError):
            raise SttError("provider_error", "The speech service returned an unreadable answer.")


def get_provider(client=None):
    """The configured provider, or None (nothing configured, unknown name, or a required key is missing)."""
    import os
    name = settings.stt_provider_name()
    if name == "mock":
        return MockSttProvider()
    if name == "groq":
        key = os.getenv("GROQ_API_KEY")
        return GroqWhisperProvider(key, client=client, timeout=settings.stt_timeout_seconds()) if key else None
    return None
