"""The deterministic semantic grader: does the learner's answer MEAN what an accepted answer means?

It is a transparent, rule-based comparison, not a model. For the language's lexicon (see lexicon.py) it works on the "key" words of the
accepted answer (everything except function words and polite address) and asks how many of them the learner covered, allowing
spelling variants, equivalent words, a one-letter slip in longer words and any word order. Extra words the learner added reduce the
score, so listing every word you know cannot pass.

    coverage   = matched key words / key words of the accepted answer
    confidence = coverage * (1 - 0.5 * extra_ratio)        extra_ratio = unmatched learner words / learner words (function words excluded)

Policy (thresholds live in settings.py):  confidence >= SEMANTIC_ACCEPT_AT accepts;  >= SEMANTIC_CLOSE_AT is "close" (not accepted, the hint
says how close);  below that, no match. It is never asked to guess for an unsupported language. The output carries counts only: it can
never reveal the accepted answer."""
from dataclasses import dataclass, field

from .. import settings
from ..textnorm import normalize
from . import lexicon


@dataclass(frozen=True)
class Grade:
    supported: bool
    confidence: float = 0.0
    coverage: float = 0.0
    matched: int = 0
    total: int = 0
    extra: int = 0
    reordered: bool = False
    accepted_by: str = ""                       # which stored answer matched best (server side only: never returned to a client)
    tokens: tuple = field(default=(), compare=False)

    @property
    def semantic_match(self):
        return self.supported and self.confidence >= settings.SEMANTIC_ACCEPT_AT

    @property
    def close(self):
        return self.supported and settings.SEMANTIC_CLOSE_AT <= self.confidence < settings.SEMANTIC_ACCEPT_AT

    @property
    def missing(self):
        return max(0, self.total - self.matched)


def _tokens(text, deva, lex):
    canon = lex.canon_deva if deva else lex.canon_roman
    stop = lex.stop_deva if deva else lex.stop_roman
    return [c for c in (canon(t) for t in normalize(lex.prepare(text)).split()) if c and c not in stop]


def _levenshtein_at_most_one(a, b):
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        return sum(x != y for x, y in zip(a, b)) <= 1
    short, long_ = (a, b) if len(a) < len(b) else (b, a)
    i = 0
    while i < len(short) and short[i] == long_[i]:
        i += 1
    return short[i:] == long_[i + 1:]


def same_word(a, b, deva, lex=None):
    if a == b:
        return True
    lex = lex or lexicon.LEXICONS["hi"]
    groups = lex.group_deva if deva else lex.group_roman
    if a in groups and b in groups and groups[a] == groups[b]:
        return True
    return min(len(a), len(b)) >= 4 and _levenshtein_at_most_one(a, b)


def _grade_one(learner_text, accepted_text, deva, lex):
    keys, mine = _tokens(accepted_text, deva, lex), _tokens(learner_text, deva, lex)
    if not keys or not mine:
        return Grade(supported=True, total=len(keys), tokens=tuple(keys))
    free, matched, order = list(range(len(mine))), 0, []
    for k in keys:
        hit = next((i for i in free if same_word(k, mine[i], deva, lex)), None)
        if hit is not None:
            free.remove(hit)
            matched += 1
            order.append(hit)
    coverage = matched / len(keys)
    extra = len(mine) - matched
    confidence = round(coverage * (1 - 0.5 * extra / len(mine)), 2)
    return Grade(True, confidence, round(coverage, 2), matched, len(keys), extra, reordered=order != sorted(order), accepted_by=accepted_text, tokens=tuple(keys))


def grade(language_code, learner_text, accepted):
    """Best grade over the accepted answers written in the same script as the learner's text. Unsupported language, or no accepted answer in the
    learner's script: Grade(supported=False)."""
    if language_code not in lexicon.SUPPORTED or not isinstance(learner_text, str) or not learner_text.strip():
        return Grade(supported=False)
    lex = lexicon.for_language(language_code)
    deva = lex.native(learner_text)                              # the language's own script (Devanagari, Kannada) or Roman letters
    same_script = [a for a in accepted if lex.native(a) == deva]
    if not same_script:
        return Grade(supported=False)
    best = None
    for a in same_script:
        g = _grade_one(learner_text, a, deva, lex)
        if best is None or (g.confidence, g.coverage) > (best.confidence, best.coverage):
            best = g
    return best


def secret_words(accepted):
    """Every word of every accepted answer (normalised): used to check that explanations do not reveal the key."""
    return {w for a in accepted for w in normalize(a).split()}


def typed_words(learner_text):
    return set(normalize(learner_text).split())


# ---------- the words a client may be told ----------
def explain(g):
    """(explanation, missing_objective, grammar_feedback) made only of counts: never a word of the accepted answer."""
    if not g.supported:
        return "Semantic checking is not available for this language, so only the exact phrase counts.", "", ""
    missing = f"{g.missing} key word{'s' if g.missing != 1 else ''} missing" if g.missing else ""
    if g.semantic_match:
        why = f"Your answer says the same thing ({g.matched} of {g.total} key words matched)."
        grammar = "Your word order is a little different from the usual phrasing, but the meaning is clear." if g.reordered and g.matched == g.total else ""
        return why, "", grammar
    if g.close:
        return f"Close: {g.matched} of {g.total} key words matched.", missing, ""
    return "That does not match the idea of this step.", missing, ""
