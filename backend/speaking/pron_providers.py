"""Pronunciation providers behind one interface, so the assessment system never knows how a score was produced.

A provider receives the target phrase, what speech recognition heard and (if it needs it) the recording, and returns only
what it can honestly measure: an overall score, any component scores, any word-level scores. Everything is optional except
that SOMETHING must be returned; a provider that cannot measure a thing leaves it out and the system shows nothing for it.
Nothing is ever filled in on a provider's behalf.

`method` states what kind of measurement the provider's numbers are:
    mock   a controlled test signal read from the input, not a measurement of speech;
    proxy  an indirect measure (for example the recogniser's own confidence), not a pronunciation measure;
    model  a real acoustic pronunciation model (phoneme/word level). None is shipped yet.

Shipped: `mock` only. With PRONUNCIATION_PROVIDER unset there is no provider and the assessment reports pronunciation as
unavailable (the word check still works). No real provider adapter exists because none can be built from the dependencies and
configuration the project already has (the speech provider, Groq Whisper, returns text, not a pronunciation analysis)."""
from dataclasses import dataclass, field
from typing import Mapping, Optional, Protocol, Sequence

from .. import settings
from .stt import language_of

COMPONENTS = ("phoneme_accuracy", "word_accuracy", "fluency", "prosody", "confidence")


class PronError(Exception):
    """A controlled assessment failure. `code` is one of the codes the database accepts for pronunciation_assessments.error_code."""

    def __init__(self, code, message=""):
        super().__init__(message or code)
        self.code = code


@dataclass(frozen=True)
class PronunciationInput:
    target_text: str                         # the phrase the learner was asked to say (script of the language)
    target_romanised: Optional[str]
    locale: str
    transcript_text: str                     # what speech recognition heard
    transcript_confidence: Optional[float]
    audio: Optional[bytes] = None            # only present for providers that need the recording
    mime_type: Optional[str] = None
    recording_ms: Optional[int] = None


@dataclass(frozen=True)
class PronunciationResult:
    overall: Optional[float] = None
    components: Mapping[str, float] = field(default_factory=dict)
    word_scores: Sequence = field(default_factory=tuple)      # [(word, score), ...] in phrase order


@dataclass(frozen=True)
class PronunciationCapabilities:
    components: frozenset                     # which components this provider can report
    requires_audio: bool
    languages: Optional[frozenset] = None     # ISO 639-1 codes; None = any
    word_scores: bool = False

    def supports_language(self, locale):
        return self.languages is None or language_of(locale) in self.languages


class PronunciationProvider(Protocol):
    name: str
    method: str                               # 'mock' | 'proxy' | 'model'
    capabilities: PronunciationCapabilities

    def assess(self, inp: PronunciationInput) -> PronunciationResult:
        """Return what could be measured. Raise PronError for any failure; never let provider details escape."""


class MockPronunciationProvider:
    """Deterministic provider for development and tests. Its scores are NOT derived from the speech: they are read from controlled
    markers in the (synthetic) audio bytes, so a test decides exactly what the 'provider' reports:
        MOCKPRON:<0..100>             the overall score
        MOCKPRONC:<component>=<n>     a component score (repeatable)
        MOCKPRONW:<word>=<n>          a word score (repeatable, phrase order)
        MOCKPRONFAIL                  fail with a provider error
    Audio with no marker at all gives `no_signal` (a mock has nothing to report), never an invented score."""
    name = "mock"
    method = "mock"
    capabilities = PronunciationCapabilities(components=frozenset(COMPONENTS), requires_audio=True, word_scores=True)

    def assess(self, inp):
        audio = inp.audio or b""
        if b"MOCKPRONFAIL" in audio:
            raise PronError("provider_error", "The mock provider was told to fail.")
        overall, components, words, seen = None, {}, [], False
        for raw in audio.split(b"\n"):
            i = raw.find(b"MOCKPRON")
            if i < 0:
                continue
            line = raw[i:]
            try:
                if line.startswith(b"MOCKPRONC:"):
                    key, _, value = line[len(b"MOCKPRONC:"):].decode("utf-8", "replace").partition("=")
                    components[key.strip()] = float(value)
                elif line.startswith(b"MOCKPRONW:"):
                    word, _, value = line[len(b"MOCKPRONW:"):].decode("utf-8", "replace").rpartition("=")
                    words.append((word.strip(), float(value)))
                elif line.startswith(b"MOCKPRON:"):
                    overall = float(line[len(b"MOCKPRON:"):].decode("ascii", "replace").strip())
                else:
                    continue
            except ValueError:
                raise PronError("provider_error", "The mock provider could not read its own marker.")
            seen = True
        if not seen:
            raise PronError("no_signal", "The recording carries no mock pronunciation signal.")
        return PronunciationResult(overall=overall, components=components, word_scores=tuple(words))


def get_provider():
    """The configured pronunciation provider, or None (the default)."""
    return MockPronunciationProvider() if settings.pron_provider_name() == "mock" else None


_factory = get_provider   # replaceable in tests; everything asks `configured()` so they all see the same provider


def configured():
    return _factory()
