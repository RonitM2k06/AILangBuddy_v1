"""Provider-independent audio: decide how an item is played, without the listening (or later speaking) code knowing how.

An *audio source* tells the client what to play:
  * kind "url"          a file to fetch: from a static asset, a generated asset or an external TTS service;
  * kind "browser_tts"  nothing to fetch: the browser speaks `speak_text` itself (the runtime fallback, no API key, no row).

Providers are tried in order and the first that can serve the item wins, so adding a real TTS later means adding a provider
or registering generated assets. Neither touches the listening system. Generation is optional: a `TtsGenerator` can
synthesise audio into a file and the service records only its metadata (never bytes) in `audio_assets`."""
from dataclasses import dataclass
from typing import Optional, Protocol

from ..repositories import audio as repo


@dataclass(frozen=True)
class AudioSource:
    kind: str                       # "url" | "browser_tts"
    provider: str                   # "static" | "generated" | "external_tts" | "browser_tts"
    locale: str
    url: Optional[str] = None
    mime_type: Optional[str] = None
    duration_ms: Optional[int] = None
    voice: Optional[str] = None
    speak_text: Optional[str] = None            # browser_tts only: the client needs the text to speak it
    speak_fallback_text: Optional[str] = None   # browser_tts only: romanised form for devices without a voice for the language

    def as_dict(self):
        """JSON-ready, omitting empty fields (so a file source never carries the spoken text)."""
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass(frozen=True)
class GeneratedAudio:
    source_url: str
    mime_type: str
    duration_ms: Optional[int] = None
    voice: Optional[str] = None


class TtsUnavailable(Exception):
    """No TTS generator is configured (the default: nothing needs an API key)."""


class TtsGenerator(Protocol):
    provider: str   # stored as the asset's provider: "generated" or "external_tts"

    def synthesize(self, text: str, locale: str) -> GeneratedAudio:
        """Produce audio for `text`, store it wherever the generator keeps files, and return where it can be fetched."""


class NullTtsGenerator:
    provider = "generated"

    def synthesize(self, text, locale):
        raise TtsUnavailable("no TTS generator configured")


class AudioProvider(Protocol):
    name: str

    def resolve(self, conn, item) -> Optional[AudioSource]:
        ...


class AssetAudioProvider:
    """Serves the best active stored asset for the item (static, then generated, then external TTS)."""
    name = "assets"

    def resolve(self, conn, item):
        assets = repo.active_assets(conn, item["id"])
        if not assets:
            return None
        a = assets[0]
        return AudioSource(kind="url", provider=a["provider"], locale=a["locale"], url=a["source_url"],
                           mime_type=a["mime_type"], duration_ms=a["duration_ms"], voice=a["voice"])


class BrowserTtsProvider:
    """The always-available fallback: the browser's speech synthesis speaks the item's text."""
    name = "browser_tts"

    def resolve(self, conn, item):
        return AudioSource(kind="browser_tts", provider="browser_tts", locale=item["locale"],
                           speak_text=item["text"], speak_fallback_text=item["pronunciation"])


class AudioService:
    def __init__(self, providers=None, generator=None):
        self.providers = list(providers) if providers is not None else [AssetAudioProvider(), BrowserTtsProvider()]
        self.generator = generator or NullTtsGenerator()

    def resolve(self, conn, item_id):
        """How to play this item, or None if the item does not exist."""
        item = repo.item_speech(conn, item_id)
        if item is None:
            return None
        for provider in self.providers:
            source = provider.resolve(conn, item)
            if source is not None:
                return source
        return None

    def metadata(self, conn, item_id):
        """Everything known about the item's audio: its stored assets and the source it currently resolves to."""
        item = repo.item_speech(conn, item_id)
        if item is None:
            return None
        return {"item_id": item_id, "locale": item["locale"], "assets": repo.all_assets(conn, item_id),
                "resolved": self.resolve(conn, item_id).as_dict()}

    def ensure_asset(self, conn, item_id, created_at):
        """Generate and register an asset for an item that has none (only if a generator is configured). Returns the
        source now in effect, or None when nothing could be generated; the listening flow works either way."""
        item = repo.item_speech(conn, item_id)
        if item is None:
            return None
        if repo.active_assets(conn, item_id):
            return self.resolve(conn, item_id)
        try:
            made = self.generator.synthesize(item["text"], item["locale"])
        except TtsUnavailable:
            return None
        repo.insert_asset(conn, item_id, item["language_id"], self.generator.provider, item["locale"], made.voice,
                          made.source_url, made.mime_type, made.duration_ms, created_at)
        return self.resolve(conn, item_id)


default_service = AudioService()
