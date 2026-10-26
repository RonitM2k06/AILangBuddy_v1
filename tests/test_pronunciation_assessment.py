"""The assessment rules in isolation: validation of provider output, aggregation, and feedback that states only observed facts."""
import json

import pytest

from backend.speaking import assessment as A
from backend.speaking.content_match import compare
from backend.speaking.pron_providers import COMPONENTS, PronError, PronunciationCapabilities, PronunciationResult

CAPS = PronunciationCapabilities(components=frozenset(COMPONENTS), requires_audio=False, word_scores=True)
NO_WORDS = PronunciationCapabilities(components=frozenset({"fluency"}), requires_audio=False, word_scores=False)


def check(result, caps=CAPS):
    return A.validate_result(result, caps)


def rejected(result, caps=CAPS):
    with pytest.raises(PronError) as e:
        check(result, caps)
    assert e.value.code == "malformed_output"


# ---------- score bounds ----------
@pytest.mark.parametrize("value,stored", [(0, 0), (100, 100), (0.4, 0), (0.5, 1), (49.5, 50), (99.5, 100), (72, 72), (72.49, 72), (72.5, 73), (100.0, 100)])
def test_scores_are_whole_numbers_rounded_half_up(value, stored):
    assert check(PronunciationResult(overall=value))[0] == stored


@pytest.mark.parametrize("bad", [-0.01, -1, 100.01, 101, 1e9, float("nan"), float("inf"), -float("inf"), "80", None.__class__, True, False, [80], {"s": 1}])
def test_out_of_range_or_non_numeric_overall_scores_reject_the_whole_result(bad):
    rejected(PronunciationResult(overall=bad))


@pytest.mark.parametrize("bad", [-1, 101, float("nan"), "50", True, None.__class__])
def test_bad_component_scores_are_rejected_not_clamped(bad):
    rejected(PronunciationResult(overall=80, components={"fluency": bad}))


@pytest.mark.parametrize("bad", [-1, 101, float("nan"), "50", True])
def test_bad_word_scores_are_rejected_not_clamped(bad):
    rejected(PronunciationResult(overall=80, word_scores=[("शब्द", bad)]))


def test_one_bad_value_rejects_everything_even_if_the_rest_is_fine():
    rejected(PronunciationResult(overall=90, components={"fluency": 80, "prosody": 150}, word_scores=[("a", 50)]))


# ---------- structure ----------
def test_unknown_or_undeclared_components_are_rejected():
    rejected(PronunciationResult(overall=80, components={"charisma": 80}))                       # not a known component
    rejected(PronunciationResult(overall=80, components={"prosody": 80}), NO_WORDS)               # known, but this provider does not declare it
    check(PronunciationResult(overall=80, components={"fluency": 80}), NO_WORDS)


def test_word_scores_need_a_provider_that_declares_them():
    rejected(PronunciationResult(overall=80, word_scores=[("a", 50)]), NO_WORDS)


@pytest.mark.parametrize("entry", [("", 50), ("  ", 50), ("w" * 61, 50), (5, 50), ("a",), ("a", 50, 1), "ab", None])
def test_malformed_word_entries_are_rejected(entry):
    rejected(PronunciationResult(overall=80, word_scores=[entry]))


def test_too_many_word_scores_are_rejected():
    rejected(PronunciationResult(overall=80, word_scores=[("w", 50)] * (A.MAX_WORD_SCORES + 1)))
    check(PronunciationResult(overall=80, word_scores=[("w", 50)] * A.MAX_WORD_SCORES))


@pytest.mark.parametrize("not_a_result", [None, {}, {"overall": 80}, 80, "80", (80, {}, [])])
def test_anything_that_is_not_a_result_object_is_rejected(not_a_result):
    rejected(not_a_result)


def test_components_must_be_a_mapping():
    rejected(PronunciationResult(overall=80, components=[("fluency", 80)]))


# ---------- aggregation ----------
def test_the_providers_overall_score_is_authoritative():
    overall, comps, _ = check(PronunciationResult(overall=60, components={"fluency": 100, "prosody": 100}))
    assert A.aggregate(overall, comps) == 60


@pytest.mark.parametrize("comps,expected", [({"fluency": 80}, 80), ({"fluency": 80, "prosody": 60}, 70), ({"fluency": 81, "prosody": 60}, 71),
                                            ({"fluency": 0, "prosody": 0, "confidence": 1}, 0), ({"a": 1}, None)])
def test_without_an_overall_the_mean_of_the_components_is_used(comps, expected):
    comps = {k: v for k, v in comps.items() if k in COMPONENTS}
    if not comps:
        with pytest.raises(PronError) as e:
            A.aggregate(None, comps)
        assert e.value.code == "no_signal"
    else:
        assert A.aggregate(None, comps) == expected


def test_nothing_to_aggregate_is_no_signal_never_a_default_score():
    with pytest.raises(PronError) as e:
        A.aggregate(None, {})
    assert e.value.code == "no_signal"


def test_an_overall_of_zero_is_a_score_not_missing():
    assert A.aggregate(0, {}) == 0


# ---------- feedback: facts only ----------
def content(heard, text="कितने पैसे होंगे?", roman="Kitne paise honge?"):
    m = compare(text, roman, heard)
    return A._content_view(m)


def pron(available=True, method="mock", components=None, words=None, error=None):
    return {"available": available, "method": method, "error_code": error, "components": components or {}, "word_scores": words or []}


def texts(fb):
    return " ".join(f["text"] for f in fb)


def test_a_fully_recognised_phrase_is_reported_as_such():
    fb = A.build_feedback(content("कितने पैसे होंगे"), pron())
    assert fb[0] == {"type": "content", "text": "Speech recognition picked up all 3 words of the phrase."}
    assert not any(f["type"] == "notice" and "pronunciation problem" in f["text"] for f in fb)


def test_missing_changed_and_extra_words_are_described_as_what_the_recogniser_heard():
    fb = A.build_feedback(content("kitne paisa honge ji"), pron(available=False, error="provider_unavailable"))
    t = texts(fb)
    assert "picked up 2 of the 3 words" in t and "heard “paisa” where the phrase has “paise”" in t and "also heard: ji" in t
    assert "does not by itself show a pronunciation problem" in t
    assert "wrong" not in t.lower() and "mispronounc" not in t.lower() and "incorrect" not in t.lower()


def test_words_to_practise_come_only_from_provider_word_scores():
    words = [{"position": 1, "word": "कितने", "score": 90}, {"position": 2, "word": "पैसे", "score": 59}, {"position": 3, "word": "होंगे", "score": 60}]
    fb = A.build_feedback(content("कितने पैसे होंगे"), pron(words=words))
    practise = [f for f in fb if f["type"] == "pronunciation"]
    assert len(practise) == 1 and practise[0]["words"] == ["पैसे"] and "पैसे (59)" in practise[0]["text"]
    assert A.WORD_PRACTISE_BELOW == 60


def test_no_practise_list_without_word_scores_even_if_words_were_missed():
    fb = A.build_feedback(content("kitne honge"), pron())
    assert not [f for f in fb if f["type"] == "pronunciation"]                             # a missed word is not a pronunciation finding
    assert "only an overall score" in texts(fb)                                              # and the learner is told why there is no detail


def test_components_are_listed_only_if_reported():
    fb = A.build_feedback(content("कितने पैसे होंगे"), pron(components={"fluency": 70, "prosody": 55}))
    line = next(f["text"] for f in fb if f["type"] == "pronunciation")
    assert "Fluency 70" in line and "Prosody 55" in line and "Sound accuracy" not in line and "Word accuracy" not in line
    assert not [f for f in A.build_feedback(content("कितने पैसे होंगे"), pron()) if f["type"] == "pronunciation"]


def test_sounds_and_phonemes_are_never_mentioned_unless_a_component_by_that_name_was_reported():
    for heard in ("कितने पैसे होंगे", "kitne honge", "बिल्कुल अलग", ""):
        for p in (pron(), pron(words=[{"position": 1, "word": "x", "score": 10}]), pron(available=False, error="no_signal")):
            t = texts(A.build_feedback(content(heard), p)).lower()
            for banned in ("phoneme", "vowel", "consonant", "stress", "aspirat", "accent", "intonation", "retroflex", "your pronunciation of"):
                assert banned not in t, (heard, banned)
    t = texts(A.build_feedback(content("कितने पैसे होंगे"), pron(components={"phoneme_accuracy": 80})))
    assert "Sound accuracy 80" in t                                                          # reported by the provider, so it may be shown


@pytest.mark.parametrize("method", ["mock", "proxy", "model"])
def test_every_available_assessment_carries_its_limitation(method):
    fb = A.build_feedback(content("कितने पैसे होंगे"), pron(method=method))
    assert A.LIMITATIONS[method] in [f["text"] for f in fb if f["type"] == "notice"]
    assert ("not a measurement" in A.LIMITATIONS["mock"]) and ("proxy" in A.LIMITATIONS["proxy"]) and ("not a human teacher" in A.LIMITATIONS["model"])


@pytest.mark.parametrize("code", sorted(A.ERROR_MESSAGES))
def test_unavailable_pronunciation_is_explained_and_the_word_check_is_not_presented_as_pronunciation(code):
    fb = A.build_feedback(content("कितने पैसे होंगे"), pron(available=False, error=code))
    notice = [f["text"] for f in fb if f["type"] == "notice"][-1]
    assert A.ERROR_MESSAGES[code] in notice and "does not measure pronunciation" in notice
    assert not [f for f in fb if f["type"] == "pronunciation"]


def test_feedback_is_deterministic_and_json_safe():
    args = (content("kitne paisa honge ji"), pron(components={"fluency": 70}, words=[{"position": 1, "word": "paise", "score": 40}]))
    assert A.build_feedback(*args) == A.build_feedback(*args)
    json.dumps(A.build_feedback(*args), ensure_ascii=False)


def test_every_error_code_has_a_message_the_database_accepts():
    import re
    from pathlib import Path
    sql = (Path(__file__).parent.parent / "backend" / "db" / "migrations" / "0019_pronunciation_schema.sql").read_text()
    allowed = set(re.findall(r"'([a-z_]+)'", re.search(r"error_code IN \(([^)]*)\)", sql).group(1)))
    assert set(A.ERROR_MESSAGES) == allowed
