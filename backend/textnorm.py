"""Answer normalisation shared by every grader (lessons, situations)."""
import unicodedata


def normalize(text):
    """Case-insensitive comparison that ignores punctuation but keeps letters, combining marks (Devanagari vowel
    signs) and digits."""
    kept = [ch if (unicodedata.category(ch)[0] in "LMN" or ch.isspace()) else " " for ch in unicodedata.normalize("NFKC", text)]
    return " ".join("".join(kept).casefold().split())


def answer_key(text, language_code=None):
    """The key a typed answer is compared by. For most languages (Hindi included) exactly `normalize`, as before. For a language with
    documented romanisation variants (Marathi, Kannada, Tamil, Bengali, Telugu, Urdu, Kashmiri, Dogri, French accents), each word is also folded the way its lexicon folds it, so "zhale", "jhale" and "zale", or
    "aahe" and "ahe", are the same answer; nothing else becomes equal. See backend/adaptive/lexicon.py."""
    if language_code not in _FOLDED:
        return normalize(text)
    from .adaptive import lexicon                                  # imported here: lexicon imports nothing from this module's callers
    lex = lexicon.for_language(language_code)
    base = normalize(lex.prepare(text))
    return " ".join(lex.canon_deva(w) if lex.native(w) else lex.canon_roman(w) for w in base.split())


_FOLDED = {"mr", "kn", "ta", "fr", "bn", "te", "ur", "ks", "doi"}                       # Hindi keeps exact matching: its spelling variants are handled by the semantic grader only
