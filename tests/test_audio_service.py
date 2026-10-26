import pytest

from backend.audio.service import (AssetAudioProvider, AudioService, AudioSource, BrowserTtsProvider, GeneratedAudio, NullTtsGenerator,
                                   TtsUnavailable, default_service)
from backend.db import connect
from backend.repositories import audio as repo

ITEM_ROMAN = "Paani milega?"


def item_id(conn, roman=ITEM_ROMAN):
    return conn.execute("SELECT id FROM vocabulary_items WHERE pronunciation = ?", (roman,)).fetchone()[0]


def add_asset(conn, item, provider="static", url="/static/audio/a.mp3", mime="audio/mpeg", dur=1500, voice=None, active=True):
    aid = repo.insert_asset(conn, item, conn.execute("SELECT language_id FROM vocabulary_items WHERE id=?", (item,)).fetchone()[0], provider, "hi-IN", voice, url, mime, dur, "2026-01-01 00:00:00")
    if not active:
        conn.execute("UPDATE audio_assets SET is_active = 0 WHERE id = ?", (aid,))
    return aid


# ---------- fallback ----------
def test_item_without_assets_falls_back_to_browser_tts(db_path):
    with connect(db_path) as conn:
        src = default_service.resolve(conn, item_id(conn))
    assert (src.kind, src.provider, src.locale) == ("browser_tts", "browser_tts", "hi-IN")
    assert src.speak_text == "पानी मिलेगा?" and src.speak_fallback_text == ITEM_ROMAN and src.url is None
    assert src.as_dict() == {"kind": "browser_tts", "provider": "browser_tts", "locale": "hi-IN", "speak_text": "पानी मिलेगा?", "speak_fallback_text": ITEM_ROMAN}


def test_locale_comes_from_the_language_not_from_code(db_path):
    with connect(db_path) as conn:
        conn.execute("UPDATE languages SET tts_locale = 'hi-XX' WHERE code = 'hi'")
        assert default_service.resolve(conn, item_id(conn)).locale == "hi-XX"


def test_unknown_item_resolves_to_nothing(db_path):
    with connect(db_path) as conn:
        assert default_service.resolve(conn, 999999) is None and default_service.metadata(conn, 999999) is None
        assert default_service.ensure_asset(conn, 999999, "2026-01-01 00:00:00") is None


# ---------- stored assets ----------
def test_a_stored_asset_is_preferred_and_carries_no_spoken_text(db_path):
    with connect(db_path) as conn:
        i = item_id(conn)
        add_asset(conn, i, dur=2300, voice="asha")
        src = default_service.resolve(conn, i)
    assert (src.kind, src.provider, src.url, src.mime_type, src.duration_ms, src.voice) == ("url", "static", "/static/audio/a.mp3", "audio/mpeg", 2300, "asha")
    assert "speak_text" not in src.as_dict() and "speak_fallback_text" not in src.as_dict()


def test_asset_provider_priority_static_then_generated_then_external(db_path):
    with connect(db_path) as conn:
        i = item_id(conn)
        add_asset(conn, i, "external_tts", "https://tts.example.com/a.mp3")
        assert default_service.resolve(conn, i).provider == "external_tts"
        add_asset(conn, i, "generated", "/generated/a.ogg", "audio/ogg")
        assert default_service.resolve(conn, i).provider == "generated"
        static = add_asset(conn, i, "static", "/static/audio/a.mp3")
        assert default_service.resolve(conn, i).provider == "static"
        conn.execute("UPDATE audio_assets SET is_active = 0 WHERE id = ?", (static,))        # switching an asset off falls to the next best
        assert default_service.resolve(conn, i).provider == "generated"
        conn.execute("UPDATE audio_assets SET is_active = 0")
        assert default_service.resolve(conn, i).kind == "browser_tts"                         # nothing active: back to the fallback


def test_assets_belong_to_their_own_item(db_path):
    with connect(db_path) as conn:
        a, b = item_id(conn), item_id(conn, "Bill de dijiye.")
        add_asset(conn, a)
        assert default_service.resolve(conn, a).kind == "url" and default_service.resolve(conn, b).kind == "browser_tts"


def test_metadata_lists_assets_and_the_current_source(db_path):
    with connect(db_path) as conn:
        i = item_id(conn)
        live = add_asset(conn, i)
        add_asset(conn, i, "generated", "/generated/a.ogg", "audio/ogg", active=False)
        meta = default_service.metadata(conn, i)
    assert meta["item_id"] == i and meta["locale"] == "hi-IN"
    assert [(a["provider"], a["is_active"]) for a in meta["assets"]] == [("static", 1), ("generated", 0)] and meta["assets"][0]["id"] == live
    assert meta["resolved"]["provider"] == "static"


# ---------- the provider interface ----------
def test_providers_are_tried_in_order(db_path):
    class Fixed:
        name = "fixed"

        def resolve(self, conn, item):
            return AudioSource(kind="url", provider="external_tts", locale="hi-IN", url="https://tts.example.com/fixed.mp3", mime_type="audio/mpeg")

    with connect(db_path) as conn:
        i = item_id(conn)
        add_asset(conn, i)
        assert AudioService(providers=[Fixed(), AssetAudioProvider(), BrowserTtsProvider()]).resolve(conn, i).url.endswith("fixed.mp3")   # a new provider slots in first
        assert AudioService(providers=[AssetAudioProvider()]).resolve(conn, item_id(conn, "Bill de dijiye.")) is None                   # no fallback configured
        assert AudioService(providers=[]).resolve(conn, i) is None
        assert AudioService(providers=[BrowserTtsProvider()]).resolve(conn, i).kind == "browser_tts"                                     # a stored asset is ignored without its provider


# ---------- optional generation ----------
class FakeGenerator:
    provider = "generated"

    def __init__(self):
        self.calls = []

    def synthesize(self, text, locale):
        self.calls.append((text, locale))
        return GeneratedAudio(source_url="/generated/fake.mp3", mime_type="audio/mpeg", duration_ms=900, voice="fake")


def test_without_a_generator_nothing_is_generated_and_nothing_breaks(db_path):
    with connect(db_path) as conn:
        i = item_id(conn)
        assert AudioService().ensure_asset(conn, i, "2026-01-01 00:00:00") is None
        assert conn.execute("SELECT COUNT(*) FROM audio_assets").fetchone()[0] == 0
        assert default_service.resolve(conn, i).kind == "browser_tts"                         # listening still works
    with pytest.raises(TtsUnavailable):
        NullTtsGenerator().synthesize("x", "hi-IN")


def test_a_generator_registers_metadata_only_and_is_used_once(db_path):
    gen = FakeGenerator()
    service = AudioService(generator=gen)
    with connect(db_path) as conn:
        i = item_id(conn)
        src = service.ensure_asset(conn, i, "2026-01-01 00:00:00")
        assert (src.kind, src.provider, src.url, src.duration_ms, src.voice) == ("url", "generated", "/generated/fake.mp3", 900, "fake")
        assert gen.calls == [("पानी मिलेगा?", "hi-IN")]
        assert service.ensure_asset(conn, i, "2026-01-01 00:00:00").url == "/generated/fake.mp3"
        assert len(gen.calls) == 1 and conn.execute("SELECT COUNT(*) FROM audio_assets").fetchone()[0] == 1


def test_a_generator_cannot_register_an_unsafe_url(db_path):
    class Bad(FakeGenerator):
        def synthesize(self, text, locale):
            return GeneratedAudio(source_url="javascript:alert(1)", mime_type="audio/mpeg")

    import sqlite3
    with pytest.raises(sqlite3.IntegrityError):
        with connect(db_path) as conn:
            AudioService(generator=Bad()).ensure_asset(conn, item_id(conn), "2026-01-01 00:00:00")
