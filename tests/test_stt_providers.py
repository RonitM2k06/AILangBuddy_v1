import httpx
import pytest

from backend.speaking import stt
from .spk import audio
from backend.speaking.stt import GroqWhisperProvider, MockSttProvider, SttCapabilities, SttError, Transcription, get_provider, language_of


def mock(audio, locale="hi-IN"):
    return MockSttProvider().transcribe(audio, "audio/webm", locale)


# ---------- the interface ----------
def test_providers_expose_name_and_capabilities():
    for p in (MockSttProvider(), GroqWhisperProvider("key")):
        assert isinstance(p.name, str) and p.name
        assert isinstance(p.capabilities, SttCapabilities) and "audio/webm" in p.capabilities.mime_types
        assert callable(p.transcribe)


def test_capability_language_matching():
    any_lang = SttCapabilities(mime_types=frozenset({"audio/webm"}))
    only_hi = SttCapabilities(mime_types=frozenset({"audio/webm"}), languages=frozenset({"hi"}))
    assert any_lang.supports_language("fr-FR") and only_hi.supports_language("hi-IN") and only_hi.supports_language("hi")
    assert not only_hi.supports_language("es-ES")
    assert [language_of(x) for x in ("hi-IN", "en_IN", "ja", "ZH-cn")] == ["hi", "en", "ja", "zh"]


def test_a_custom_provider_only_needs_the_interface():
    class Echo:
        name = "echo"
        capabilities = SttCapabilities(mime_types=frozenset({"audio/webm"}))

        def transcribe(self, audio, mime_type, locale):
            return Transcription(text=audio.decode("ascii", "ignore"), confidence=1.0)

    assert Echo().transcribe(b"hi", "audio/webm", "en").text == "hi"


# ---------- deterministic mock ----------
def test_mock_reads_its_answer_from_the_audio_bytes():
    r = mock(audio("नमस्ते", conf=0.91, alts=("नमस्कार", "हेलो")))
    assert r == Transcription(text="नमस्ते", confidence=0.91, alternatives=("नमस्कार", "हेलो"))


def test_mock_is_deterministic():
    data = b"\x1a\x45\xdf\xa3MOCKSTT:hello\n"
    assert mock(data) == mock(data) == mock(bytes(data))


def test_mock_without_a_marker_returns_a_clearly_labelled_placeholder_and_no_confidence():
    r = mock(b"\x1a\x45\xdf\xa3 some unmarked audio")
    assert r.text == "[mock transcript]" and r.confidence is None and r.alternatives == ()


def test_mock_can_fail_or_hear_nothing():
    with pytest.raises(SttError) as e:
        mock(b"\x1a\x45\xdf\xa3 MOCKFAIL")
    assert e.value.code == "provider_error"
    assert mock(b"\x1a\x45\xdf\xa3 MOCKSILENCE").text == ""


def test_mock_ignores_a_malformed_confidence():
    assert mock(b"\x1a\x45\xdf\xa3MOCKSTT:x\nMOCKCONF:high\n").confidence is None


# ---------- Groq adapter, tested against a fake transport (no network, no key) ----------
def groq(handler, **kw):
    return GroqWhisperProvider("sk-test-secret", client=httpx.Client(transport=httpx.MockTransport(handler)), **kw)


def test_groq_request_shape_and_success():
    seen = {}

    def handler(request):
        seen.update(url=str(request.url), auth=request.headers.get("authorization"), ctype=request.headers.get("content-type"), body=request.content)
        return httpx.Response(200, json={"text": " नमस्ते "})

    r = groq(handler).transcribe(b"\x1a\x45\xdf\xa3AUDIO", "audio/webm", "hi-IN")
    assert r == Transcription(text="नमस्ते") and r.confidence is None              # no confidence is invented
    assert seen["url"] == "https://api.groq.com/openai/v1/audio/transcriptions" and seen["auth"] == "Bearer sk-test-secret"
    assert seen["ctype"].startswith("multipart/form-data")
    assert b'name="model"' in seen["body"] and b"whisper-large-v3-turbo" in seen["body"]
    assert b'name="language"' in seen["body"] and b"\r\n\r\nhi\r\n" in seen["body"]      # 'hi-IN' is sent as 'hi'
    assert b'filename="recording.webm"' in seen["body"] and b"AUDIO" in seen["body"]


@pytest.mark.parametrize("status,code", [(401, "provider_unavailable"), (403, "provider_unavailable"), (429, "provider_error"), (500, "provider_error"), (400, "provider_error")])
def test_groq_http_errors_map_to_safe_codes(status, code):
    with pytest.raises(SttError) as e:
        groq(lambda req: httpx.Response(status, json={"error": {"message": "secret detail sk-test-secret"}})).transcribe(b"x" * 20, "audio/webm", "hi-IN")
    assert e.value.code == code
    assert "sk-test-secret" not in e.value.message and "secret detail" not in e.value.message      # neither the key nor the body leaks


def test_groq_network_failures():
    def timeout(request):
        raise httpx.ReadTimeout("slow", request=request)

    def refused(request):
        raise httpx.ConnectError("no route", request=request)

    with pytest.raises(SttError) as e:
        groq(timeout).transcribe(b"x" * 20, "audio/webm", "hi-IN")
    assert e.value.code == "provider_timeout"
    with pytest.raises(SttError) as e:
        groq(refused).transcribe(b"x" * 20, "audio/webm", "hi-IN")
    assert e.value.code == "provider_unavailable"


def test_groq_unreadable_answers():
    for resp in (httpx.Response(200, content=b"not json"), httpx.Response(200, json=["a list"])):
        with pytest.raises(SttError) as e:
            groq(lambda req, r=resp: r).transcribe(b"x" * 20, "audio/webm", "hi-IN")
        assert e.value.code == "provider_error"
    assert groq(lambda req: httpx.Response(200, json={})).transcribe(b"x" * 20, "audio/webm", "hi-IN").text == ""


# ---------- choosing a provider ----------
def test_nothing_is_configured_by_default():
    assert get_provider() is None


@pytest.mark.parametrize("name", ["mock", "MOCK", " Mock "])
def test_mock_is_selected_explicitly(monkeypatch, name):
    monkeypatch.setenv("STT_PROVIDER", name)
    assert get_provider().name == "mock"


def test_groq_needs_both_the_explicit_choice_and_a_key(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "k")
    assert get_provider() is None                                  # a key alone never sends anyone's voice anywhere
    monkeypatch.setenv("STT_PROVIDER", "groq")
    assert get_provider().name == "groq"
    monkeypatch.delenv("GROQ_API_KEY")
    assert get_provider() is None                                  # chosen but unusable: unavailable, not a crash


@pytest.mark.parametrize("name", ["", "whisper", "google", "none"])
def test_unknown_or_none_means_unavailable(monkeypatch, name):
    monkeypatch.setenv("STT_PROVIDER", name)
    assert get_provider() is None
