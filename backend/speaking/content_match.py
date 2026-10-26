"""Content match: did speech recognition hear the words of the target phrase?

This is a comparison of WORDS, computed here from the transcript, with no provider and no model. It is deliberately not a
pronunciation measure: a recogniser can miss or change a word because the speech was unclear, or simply because it is imperfect
(especially for Hindi, which may come back in Devanagari or Roman letters), and it can pick up every word of a phrase that was
pronounced poorly. The result feeds the "words recognised" part of the feedback and nothing else.

Method: normalise both texts (case, punctuation and the danda are ignored; Devanagari vowel signs are kept), split into words,
choose the target in the same script the transcript came back in (Devanagari text, or the romanised form), and align the two
word lists in order (difflib). Equal runs are matched; the rest are missing (in the phrase, not heard), changed (a different word
heard in the same place) or extra (heard, not in the phrase). Spelling variants of romanised Hindi (accha / achha) are different
words here: that is a stated limitation, not something to tune away."""
import difflib
import unicodedata
from dataclasses import dataclass

from ..textnorm import normalize

_DEVANAGARI_BLOCK = range(0x0900, 0x0980)
_KANNADA_BLOCK = range(0x0C80, 0x0D00)
_TAMIL_BLOCK = range(0x0B80, 0x0C00)
_BENGALI_BLOCK = range(0x0980, 0x0A00)
_TELUGU_BLOCK = range(0x0C00, 0x0C80)
_URDU_BLOCK = range(0x0600, 0x0700)
_KASHMIRI_MARKS = set("\u0620\u0655\u065A\u065B\u0672\u06C4")


@dataclass(frozen=True)
class ContentMatch:
    script: str                   # 'devanagari' | 'kannada' | 'tamil' | 'bengali' | 'telugu' | 'urdu' | 'kashmiri' | 'latin': which form of the target was compared
    expected: tuple               # the target's words
    matched: int                  # how many of them were heard, in order
    missing: tuple                # target words not heard
    changed: tuple                # ((target word, heard word), ...)
    extra: tuple                  # heard words that are not in the phrase


def script_of(text):
    """Devanagari if the text contains a Devanagari LETTER or vowel sign. Punctuation inside the Devanagari block (the danda) and
    digits do not count, so a Latin-letter transcript that ends in "।" is still Latin."""
    for ch in text or "":
        if unicodedata.category(ch)[0] in ("L", "M"):
            if ord(ch) in _DEVANAGARI_BLOCK:
                return "devanagari"
            if ord(ch) in _KANNADA_BLOCK:                         # Kannada script: compared with the phrase's own text, as Devanagari is
                return "kannada"
            if ord(ch) in _TAMIL_BLOCK:
                return "tamil"
            if ord(ch) in _BENGALI_BLOCK:
                return "bengali"
            if ord(ch) in _TELUGU_BLOCK:
                return "telugu"
            if ord(ch) in _URDU_BLOCK:
                return "kashmiri" if _KASHMIRI_MARKS & set(text) else "urdu"   # the same block; Kashmiri has letters and vowel signs of its own
    return "latin"


def _no_accents(text):
    """Latin letters without their accents (French "café" heard as "cafe" is the same word); used for Roman-letter comparisons only."""
    return "".join(ch for ch in unicodedata.normalize("NFD", text) if unicodedata.category(ch) != "Mn")


def compare(target_text, target_romanised, heard):
    script = script_of(heard)
    target = target_text if script != "latin" else (target_romanised or target_text)
    if script == "latin":
        target, heard = _no_accents(target), _no_accents(heard)
    expected, got = normalize(target).split(), normalize(heard).split()
    matched, missing, changed, extra = 0, [], [], []
    for op, a0, a1, b0, b1 in difflib.SequenceMatcher(None, expected, got, autojunk=False).get_opcodes():
        if op == "equal":
            matched += a1 - a0
        elif op == "delete":
            missing += expected[a0:a1]
        elif op == "insert":
            extra += got[b0:b1]
        else:  # replace: pair them up in order, the surplus on either side is missing / extra
            pairs = min(a1 - a0, b1 - b0)
            changed += list(zip(expected[a0:a0 + pairs], got[b0:b0 + pairs]))
            missing += expected[a0 + pairs:a1]
            extra += got[b0 + pairs:b1]
    return ContentMatch(script=script, expected=tuple(expected), matched=matched, missing=tuple(missing), changed=tuple(changed), extra=tuple(extra))
