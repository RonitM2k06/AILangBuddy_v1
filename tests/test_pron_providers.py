import pytest

from backend.speaking import pron_providers
from backend.speaking.pron_providers import (COMPONENTS, MockPronunciationProvider, PronError, PronunciationCapabilities, PronunciationInput,
                                             PronunciationResult, configured, get_provider)

from .spk import audio


def inp(data, **kw):
    base = dict(target_text="कितने पैसे होंगे?", target_romanised="Kitne paise honge?", locale="hi-IN", transcript_text="x", transcript_confidence=None, audio=data)
    return PronunciationInput(**{**base, **kw})


def mock(pron=None, text="x", **kw):
    return MockPronunciationProvider().assess(inp(audio(text, pron=pron), **kw))


# ---------- the interface ----------
def test_the_mock_declares_what_it_is_and_what_it_can_report():
    p = MockPronunciationProvider()
    assert p.name == "mock" and p.method == "mock" and isinstance(p.capabilities, PronunciationCapabilities)
    assert p.capabilities.requires_audio and p.capabilities.word_scores and set(COMPONENTS) == set(p.capabilities.components)


def test_capability_language_matching():
    any_lang = PronunciationCapabilities(components=frozenset(), requires_audio=False)
    only_hi = PronunciationCapabilities(components=frozenset(), requires_audio=False, languages=frozenset({"hi"}))
    assert any_lang.supports_language("fr-FR") and only_hi.supports_language("hi-IN") and not only_hi.supports_language("es-ES")


def test_a_custom_provider_only_needs_the_interface():
    class Fixed:
        name, method = "fixed", "proxy"
        capabilities = PronunciationCapabilities(components=frozenset({"fluency"}), requires_audio=False)

        def assess(self, i):
            return PronunciationResult(overall=50.0)

    assert Fixed().assess(inp(None)).overall == 50.0


# ---------- the deterministic mock ----------
def test_scores_come_from_controlled_markers_not_from_the_speech():
    r = mock({"overall": 82, "components": {"fluency": 70, "prosody": 55}, "words": [("कितने", 90), ("पैसे", 48)]})
    assert r.overall == 82.0 and dict(r.components) == {"fluency": 70.0, "prosody": 55.0} and list(r.word_scores) == [("कितने", 90.0), ("पैसे", 48.0)]


def test_the_same_input_always_gives_the_same_result():
    data = audio("x", pron={"overall": 61, "components": {"fluency": 40}})
    assert MockPronunciationProvider().assess(inp(data)) == MockPronunciationProvider().assess(inp(bytes(data)))


def test_the_transcript_does_not_influence_the_score():
    """Same audio signal, perfectly matching vs unrelated transcript text: identical pronunciation result."""
    data = audio("anything", pron={"overall": 33})
    a = MockPronunciationProvider().assess(inp(data, transcript_text="कितने पैसे होंगे"))
    b = MockPronunciationProvider().assess(inp(data, transcript_text="completely unrelated words"))
    assert a == b and a.overall == 33.0


def test_only_what_is_marked_is_reported():
    r = mock({"overall": 70})
    assert dict(r.components) == {} and list(r.word_scores) == []                      # nothing is added on the provider's behalf
    r = mock({"components": {"fluency": 60}})
    assert r.overall is None and dict(r.components) == {"fluency": 60.0}


def test_audio_without_any_marker_has_no_signal():
    with pytest.raises(PronError) as e:
        MockPronunciationProvider().assess(inp(audio("plain recording")))
    assert e.value.code == "no_signal"
    with pytest.raises(PronError) as e:
        MockPronunciationProvider().assess(inp(None))
    assert e.value.code == "no_signal"


def test_the_mock_can_be_told_to_fail():
    with pytest.raises(PronError) as e:
        mock({"fail": True, "overall": 90})
    assert e.value.code == "provider_error"


def test_unreadable_markers_are_a_provider_error():
    with pytest.raises(PronError) as e:
        MockPronunciationProvider().assess(inp(b"OggSMOCKPRON:abc\n"))
    assert e.value.code == "provider_error"


def test_word_markers_may_contain_equals_signs_in_the_word():
    r = MockPronunciationProvider().assess(inp(b"OggSMOCKPRONW:a=b=77\n"))
    assert list(r.word_scores) == [("a=b", 77.0)]


# ---------- choosing a provider ----------
def test_there_is_no_provider_by_default():
    assert get_provider() is None and configured() is None


@pytest.mark.parametrize("name", ["mock", "MOCK", " Mock "])
def test_the_mock_must_be_chosen_explicitly(monkeypatch, name):
    monkeypatch.setenv("PRONUNCIATION_PROVIDER", name)
    assert get_provider().name == "mock"


@pytest.mark.parametrize("name", ["", "none", "azure", "whisper", "model"])
def test_anything_else_means_unavailable(monkeypatch, name):
    monkeypatch.setenv("PRONUNCIATION_PROVIDER", name)
    assert get_provider() is None


def test_an_stt_provider_alone_does_not_enable_pronunciation(monkeypatch):
    monkeypatch.setenv("STT_PROVIDER", "mock")
    monkeypatch.setenv("GROQ_API_KEY", "k")
    assert get_provider() is None


def test_the_factory_can_be_replaced_for_tests(monkeypatch):
    sentinel = object()
    monkeypatch.setattr(pron_providers, "_factory", lambda: sentinel)
    assert configured() is sentinel
