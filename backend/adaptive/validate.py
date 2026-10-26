"""Strict validators for everything a model can return in Phase 12. Nothing a model says is stored or shown until it passes here, and a
failure is a plain `AiError`: callers then use the deterministic result. The rules are deliberately narrow:
  * only the documented keys (any extra key, e.g. an "xp" or "level" field, makes the whole output invalid);
  * numbers inside the documented range, never booleans or NaN;
  * text is plain, bounded, link-free;
  * a model may not introduce numbers that are not in the evidence it was given;
  * a grader's explanation may not contain words of the answer key the learner has not typed."""
import math
import re

from ..ai.base import AiError, clean

_NUMBER = re.compile(r"\d+(?:[.,]\d+)?")
_URL = re.compile(r"(https?://|www\.|\S+@\S+\.\S+|<[^>]+>|\[[^\]]*\]\([^)]*\))", re.I)


def numbers_in(text):
    return set(_NUMBER.findall(text))


def plain(value, limit, allow_empty=False):
    if allow_empty and (value is None or (isinstance(value, str) and not value.strip())):
        return ""
    text = clean(value, limit)
    if _URL.search(text):
        raise AiError("invalid_response")
    return text


def _number(value, low, high):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise AiError("invalid_response")
    if math.isnan(value) or math.isinf(value) or not low <= value <= high:
        raise AiError("invalid_response")
    return float(value)


# ---------- semantic grade ----------
GRADE_KEYS = {"semantic_match", "confidence", "explanation", "missing_objective", "grammar_feedback"}


def validate_grade(data, secret_tokens=(), typed_tokens=()):
    """-> {semantic_match: bool, confidence: float 0..1, explanation, missing_objective, grammar_feedback}."""
    if not isinstance(data, dict) or not {"semantic_match", "confidence", "explanation"} <= set(data) or set(data) - GRADE_KEYS:
        raise AiError("invalid_response")
    if not isinstance(data["semantic_match"], bool):
        raise AiError("invalid_response")
    out = {"semantic_match": data["semantic_match"], "confidence": _number(data["confidence"], 0.0, 1.0),                  # NOT rounded: a threshold compares the real value
           "explanation": plain(data["explanation"], 200), "missing_objective": plain(data.get("missing_objective"), 100, True),
           "grammar_feedback": plain(data.get("grammar_feedback"), 200, True)}
    hidden = {t for t in secret_tokens if len(t) >= 3} - set(typed_tokens)
    blob = " ".join((out["explanation"], out["missing_objective"], out["grammar_feedback"])).casefold()
    if hidden & set(re.findall(r"\w+", blob)):                                    # never reveal a word of the key that the learner has not typed
        raise AiError("invalid_response")
    return out


# ---------- ranking ----------
def validate_ranking(data, candidates):
    """candidates: {id: [evidence texts]}. -> [(id, note)] ids unique and all known; notes may only use numbers from that candidate's evidence."""
    if not isinstance(data, list) or not data or len(data) > len(candidates):
        raise AiError("invalid_response")
    out, seen = [], set()
    for row in data:
        if not isinstance(row, dict) or set(row) - {"id", "note"} or "id" not in row:
            raise AiError("invalid_response")
        cid = row["id"]
        if not isinstance(cid, str) or cid not in candidates or cid in seen:
            raise AiError("invalid_response")
        seen.add(cid)
        note = row.get("note")
        note = plain(note, 300, True) if note is not None else ""
        allowed = set()
        for text in candidates[cid]:
            allowed |= numbers_in(text)
        if numbers_in(note) - allowed:
            raise AiError("invalid_response")
        out.append((cid, note))
    return out


# ---------- insight rewrite ----------
def validate_rewrite(text, base_text, evidence_texts):
    """A rewrite of a server-made claim may not add numbers (or drop the claim's numbers: that would change what is claimed)."""
    text = plain(text, 300)
    allowed = numbers_in(base_text)
    for e in evidence_texts:
        allowed |= numbers_in(e)
    if numbers_in(text) - allowed or numbers_in(base_text) - numbers_in(text):
        raise AiError("invalid_response")
    return text


# ---------- micro-lessons ----------
MICRO_KEYS = {"question", "options", "answer_index", "answers"}


def validate_micro_lesson(data, kind, canonical, allowed_wrong=()):
    """canonical: {answer: the one correct option text, accepted: tuple of accepted typed answers}. -> {question, options: [(text, is_correct)]}.
    The correct answer must BE the canonical one, so a model can write the question but not change what is right."""
    from ..textnorm import normalize
    if not isinstance(data, dict) or set(data) - MICRO_KEYS or "question" not in data:
        raise AiError("invalid_response")
    question = plain(data["question"], 300)
    if kind == "translation":
        answers = data.get("answers")
        if not isinstance(answers, list) or not 1 <= len(answers) <= 4 or "options" in data or "answer_index" in data:
            raise AiError("invalid_response")
        texts = [plain(a, 200) for a in answers]
        if {normalize(t) for t in texts} != {normalize(a) for a in canonical["accepted"]}:
            raise AiError("invalid_response")
        return {"question": question, "options": [(t, 1) for t in texts]}
    options, idx = data.get("options"), data.get("answer_index")
    if not isinstance(options, list) or not 3 <= len(options) <= 4 or isinstance(idx, bool) or not isinstance(idx, int) or not 0 <= idx < len(options) or "answers" in data:
        raise AiError("invalid_response")
    texts = [plain(o, 200) for o in options]
    if len({normalize(t) for t in texts}) != len(texts) or normalize(texts[idx]) != normalize(canonical["answer"]):
        raise AiError("invalid_response")
    allowed = {normalize(t) for t in allowed_wrong}                              # wrong options must be other canonical items, never the answer again
    for i, t in enumerate(texts):
        if i != idx and normalize(t) not in allowed:
            raise AiError("invalid_response")
    return {"question": question, "options": [(t, 1 if i == idx else 0) for i, t in enumerate(texts)]}
