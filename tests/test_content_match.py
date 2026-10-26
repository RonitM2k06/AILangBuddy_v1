import pytest

from backend.speaking.content_match import compare, script_of

TEXT, ROMAN = "कितने पैसे होंगे?", "Kitne paise honge?"


def test_all_words_heard_in_devanagari():
    m = compare(TEXT, ROMAN, "कितने पैसे होंगे")
    assert (m.script, m.matched, m.missing, m.changed, m.extra) == ("devanagari", 3, (), (), ()) and len(m.expected) == 3


def test_the_romanised_form_is_used_when_the_transcript_is_in_latin_letters():
    m = compare(TEXT, ROMAN, "kitne paise honge")
    assert (m.script, m.matched, m.expected) == ("latin", 3, ("kitne", "paise", "honge"))


@pytest.mark.parametrize("heard", ["KITNE PAISE HONGE!!", "  kitne   paise honge ?", "Kitne, paise... honge।"])
def test_case_punctuation_and_spacing_are_ignored(heard):
    assert compare(TEXT, ROMAN, heard).matched == 3


def test_missing_changed_and_extra_words():
    m = compare(TEXT, ROMAN, "kitne paisa honge ji")
    assert (m.matched, m.missing, m.changed, m.extra) == (2, (), (("paise", "paisa"),), ("ji",))
    m = compare(TEXT, ROMAN, "kitne honge")
    assert (m.matched, m.missing, m.changed, m.extra) == (2, ("paise",), (), ())
    m = compare(TEXT, ROMAN, "bahut kitne paise honge")
    assert (m.matched, m.extra) == (3, ("bahut",))


def test_nothing_in_common():
    m = compare(TEXT, ROMAN, "मुझे चाय")
    assert m.matched == 0 and len(m.changed) == 2 and m.missing == ("होंगे",)


def test_order_matters_because_alignment_is_in_sequence():
    m = compare(TEXT, ROMAN, "honge paise kitne")
    assert m.matched < 3


def test_the_comparison_is_by_whole_words_not_character_similarity():
    """A near-miss spelling is a different word: this is a word check, not a similarity score."""
    close, far = compare(TEXT, ROMAN, "kitne paisa honge"), compare(TEXT, ROMAN, "kitne zzzzz honge")
    assert close.matched == far.matched == 2 and close.changed[0][1] != far.changed[0][1]


def test_script_detection():
    assert script_of("नमस्ते") == "devanagari" and script_of("namaste") == "latin" and script_of("") == "latin" and script_of("namaste नमस्ते") == "devanagari"


def test_the_danda_and_devanagari_digits_do_not_make_text_devanagari():
    assert script_of("namaste।") == "latin" and script_of("kitne ४५ paise ॥") == "latin" and script_of("नमस्ते।") == "devanagari"


def test_missing_romanised_target_falls_back_to_the_text():
    assert compare("नमस्ते", None, "namaste").matched == 0


def test_the_result_is_deterministic():
    assert compare(TEXT, ROMAN, "kitne paisa honge ji") == compare(TEXT, ROMAN, "kitne paisa honge ji")


def test_empty_transcript_is_all_missing():
    m = compare(TEXT, ROMAN, "")
    assert (m.matched, m.missing) == (0, ("kitne", "paise", "honge"))
