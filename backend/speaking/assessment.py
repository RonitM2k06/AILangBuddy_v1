"""Pronunciation assessment of a transcribed speaking session.

Two DIFFERENT measurements are produced and never merged:

  content match   (always available)  Did speech recognition hear the words of the phrase?  Computed here, see content_match.py.
  pronunciation   (provider only)     How was it pronounced?  Reported by a pronunciation provider, with its method labelled
                                      (mock / proxy / model). With no provider this is "not available", never an estimate.

A good transcript therefore does not raise the pronunciation score, and a poor one does not lower it.

Scoring rules (what this module itself does; the provider supplies the numbers):
  * every provider number must be a finite number from 0 to 100 (not a bool); anything else rejects the WHOLE result as
    malformed_output. Nothing is clamped, because a number outside the scale cannot be trusted;
  * scores are stored as whole numbers (rounded half up);
  * overall = the provider's overall score if it gave one; otherwise the plain mean of the component scores it gave (equal
    weights); with neither the assessment fails as no_signal. No component is ever created on a provider's behalf;
  * components and word scores are stored only if the provider reported them and is declared able to.

Feedback is generated from stored facts only (see build_feedback). Nothing here knows about phonemes, and no phoneme or sound
error is ever stated."""
import concurrent.futures
import logging
import math
import sqlite3

from .. import settings
from ..db import connect
from ..parent import controls as parent_controls
from ..personalization import clock
from ..personalization.context import NotFound, learner_context  # noqa: F401
from ..repositories import audio as audio_repo, pronunciation as repo, situations, speaking as speaking_repo
from . import content_match, pron_providers, service as speaking
from .pron_providers import COMPONENTS, PronError, PronunciationInput, PronunciationResult

log = logging.getLogger(__name__)

STORAGE_FACTORY = speaking.STORAGE_FACTORY
_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix="pron")
MAX_WORD_SCORES = 50
WORD_PRACTISE_BELOW = 60     # a word the provider scored below this is listed as "to practise": a display convention, not a pass mark

METHOD_LABELS = {"mock": "test provider (mock)", "proxy": "proxy measure", "model": "pronunciation model"}
COMPONENT_LABELS = {"phoneme_accuracy": "Sound accuracy", "word_accuracy": "Word accuracy", "fluency": "Fluency", "prosody": "Prosody", "confidence": "Confidence"}
ERROR_MESSAGES = {
    "provider_unavailable": "Pronunciation analysis isn't available on this server.",
    "provider_error": "Pronunciation analysis had a problem. Please try again.",
    "provider_timeout": "Pronunciation analysis took too long. Please try again.",
    "malformed_output": "Pronunciation analysis returned something we can't use, so no score is shown.",
    "unsupported_language": "Pronunciation analysis doesn't support this language yet.",
    "no_signal": "Pronunciation analysis had nothing to report for this recording.",
    "recording_unavailable": "The recording is no longer available, so its pronunciation can't be analysed. Record again to get an assessment.",
}
LIMITATIONS = {
    "mock": "These pronunciation numbers come from a test provider. They are controlled test values, not a measurement of how you said the phrase.",
    "proxy": "These pronunciation numbers come from an indirect proxy measure, not from analysing the sounds you made.",
    "model": "Automated scores are an estimate and are not a human teacher's judgement.",
}


def _half_up(x):
    return int(math.floor(x + 0.5))


# ---------- provider output: validate, aggregate ----------
def _score(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 100:
        raise PronError("malformed_output", "score outside 0-100 or not a number")
    return _half_up(value)


def validate_result(result, capabilities):
    """Strictly check what a provider returned. Returns (overall | None, {component: int}, [(word, int)]) or raises
    PronError('malformed_output'). Nothing is repaired or clamped."""
    if not isinstance(result, PronunciationResult):
        raise PronError("malformed_output", "not a PronunciationResult")
    overall = None if result.overall is None else _score(result.overall)
    components = {}
    if not hasattr(result.components, "items"):
        raise PronError("malformed_output", "components must be a mapping")
    for name, value in result.components.items():
        if name not in COMPONENTS or name not in capabilities.components:
            raise PronError("malformed_output", f"unknown or undeclared component {name!r}")
        components[name] = _score(value)
    words = []
    try:
        entries = list(result.word_scores)
    except TypeError:
        raise PronError("malformed_output", "word scores must be a list")
    if entries and not capabilities.word_scores:
        raise PronError("malformed_output", "word scores from a provider that does not report them")
    if len(entries) > MAX_WORD_SCORES:
        raise PronError("malformed_output", "too many word scores")
    for entry in entries:
        if not isinstance(entry, (tuple, list)) or len(entry) != 2 or not isinstance(entry[0], str) or not entry[0].strip() or len(entry[0]) > 60:
            raise PronError("malformed_output", "bad word score entry")
        words.append((entry[0].strip(), _score(entry[1])))
    return overall, components, words


def aggregate(overall, components):
    """The overall score: the provider's own, else the equal-weight mean of the components it reported, else nothing."""
    if overall is not None:
        return overall
    if components:
        return _half_up(sum(components.values()) / len(components))
    raise PronError("no_signal", "no overall score and no components")


# ---------- feedback ----------
def build_feedback(content, pron):
    """Concise feedback from facts only. `pron` is the stored pronunciation outcome:
    {available, method, error_code, components, word_scores}. Nothing is stated that was not observed: no sound-level error is
    ever claimed, a missing word is described as something the RECOGNISER missed, and a difference never becomes "your
    pronunciation of X is wrong"."""
    out = []
    if content["words_matched"] == content["words_expected"] and not content["extra"]:
        out.append({"type": "content", "text": f"Speech recognition picked up all {content['words_expected']} words of the phrase."})
    else:
        out.append({"type": "content", "text": f"Speech recognition picked up {content['words_matched']} of the {content['words_expected']} words of the phrase."})
        if content["missing"]:
            out.append({"type": "content", "text": "It did not pick up: " + ", ".join(content["missing"]) + ".", "words": list(content["missing"])})
        for change in content["changed"]:
            out.append({"type": "content", "text": f"It heard “{change['heard']}” where the phrase has “{change['expected']}”.", "words": [change["expected"]]})
        if content["extra"]:
            out.append({"type": "content", "text": "It also heard: " + ", ".join(content["extra"]) + ".", "words": list(content["extra"])})
        out.append({"type": "notice", "text": "A difference can come from unclear speech or from the recogniser itself, so it does not by itself show a pronunciation problem."})
    if pron["available"]:
        weak = [w for w in pron["word_scores"] if w["score"] < WORD_PRACTISE_BELOW]
        if weak:
            out.append({"type": "pronunciation", "text": "Words to practise (word scores from the provider): " + ", ".join(f"{w['word']} ({w['score']})" for w in weak) + ".",
                        "words": [w["word"] for w in weak]})
        if pron["components"]:
            out.append({"type": "pronunciation", "text": "Reported by the provider: " + ", ".join(f"{COMPONENT_LABELS[k]} {v}" for k, v in sorted(pron["components"].items())) + "."})
        if not pron["components"] and not pron["word_scores"]:
            out.append({"type": "notice", "text": "This provider reports only an overall score, so there are no word or sound details to show."})
        out.append({"type": "notice", "text": LIMITATIONS[pron["method"]]})
    else:
        out.append({"type": "notice", "text": ERROR_MESSAGES[pron["error_code"]] + " The word check above only compares what was recognised; it does not measure pronunciation."})
    return out


# ---------- views ----------
def _content_view(match):
    return {"words_expected": len(match.expected), "words_matched": match.matched, "missing": list(match.missing),
            "changed": [{"expected": e, "heard": h} for e, h in match.changed], "extra": list(match.extra), "script": match.script,
            "measures": "whether speech recognition heard the words of the phrase; not pronunciation"}


def _view(conn, ctx, user_id, session_row, a):
    transcript = repo.transcript_by_id(conn, user_id, a["session_id"], a["transcript_id"])
    item = speaking._item_view(conn, ctx, session_row["item_id"])
    match = content_match.compare(item["text"], item["pronunciation"], transcript["text"])
    completed = a["status"] == "completed"
    components = repo.components_for(conn, a["id"]) if completed else {}
    words = repo.word_scores_for(conn, a["id"]) if completed else []
    pron = {"available": completed, "score": a["overall_score"] if completed else None, "scale": "0-100",
            "method": a["method"] if completed else None, "method_label": METHOD_LABELS.get(a["method"]) if completed else None,
            "is_measurement": completed and a["method"] == "model", "components": components, "word_scores": words,
            "error": None if completed else {"code": a["error_code"], "message": ERROR_MESSAGES[a["error_code"]]}}
    content = _content_view(match)
    return {"session_id": a["session_id"], "status": a["status"],
            "target": {"text": item["text"], "pronunciation": item["pronunciation"], "meaning": item["meaning"]},
            "heard": {"text": transcript["text"], "confidence": transcript["confidence"]},
            "content_match": content, "pronunciation": pron,
            "feedback": build_feedback(content, {"available": completed, "method": a["method"], "error_code": a["error_code"], "components": components, "word_scores": words}),
            "created_at": a["created_at"]}


# ---------- the assessment ----------
def _call_provider(provider, inp):
    future = _EXECUTOR.submit(provider.assess, inp)
    try:
        return future.result(timeout=settings.pron_timeout_seconds())
    except concurrent.futures.TimeoutError:
        future.cancel()
        raise PronError("provider_timeout", "timeout")
    except PronError:
        raise
    except Exception:                                   # a provider bug must not reach the learner or crash the request
        log.exception("pronunciation provider %s failed unexpectedly", getattr(provider, "name", "?"))
        raise PronError("provider_error", "unexpected provider failure")


def _fail(conn, user_id, session_id, transcript_id, provider_name, method, code, match, locale, now):
    return repo.insert_assessment(conn, session_id, user_id, transcript_id, provider_name, method, "failed", code, None, len(match.expected), match.matched, locale, now)


def assess(db_path, user_id, session_id):
    """Assess a transcribed session. Idempotent: a session that already has a completed assessment returns it unchanged, and the
    provider is not asked again. A failed attempt is stored (a controlled outcome, HTTP 200) and may be retried, up to a cap."""
    speaking.sweep_expired(db_path)   # housekeeping first: recordings past their grace period are gone before we look for one
    # --- step 1: read, validate, content match, maybe fail early ---
    with connect(db_path) as conn:
        ctx = learner_context(conn, user_id)
        row = speaking._owned(conn, user_id, session_id)                       # someone else's session is "not found"
        done = repo.completed_assessment(conn, user_id, session_id)
        if done:
            return _view(conn, ctx, user_id, row, done)
        parent_controls.require_voice(conn, ctx, user_id)       # a new analysis of audio needs voice to be allowed
        transcript = repo.best_transcript(conn, user_id, session_id)
        if row["stage"] != "completed" or transcript is None:
            raise speaking.Conflict("There is no transcript to assess yet. Record and transcribe first.")
        if repo.attempt_count(conn, user_id, session_id) >= settings.PRON_MAX_ATTEMPTS:
            raise speaking.Conflict("Too many assessment attempts for this recording.")
        item = speaking._item_view(conn, ctx, row["item_id"])
        match = content_match.compare(item["text"], item["pronunciation"], transcript["text"])
        provider, now = pron_providers.configured(), clock.now()
        early, audio = None, None
        if provider is None:
            early = "provider_unavailable"
        elif not provider.capabilities.supports_language(row["locale"]):
            early = "unsupported_language"
        elif provider.capabilities.requires_audio:
            try:
                audio = STORAGE_FACTORY().read(row["audio_ref"]) if row["audio_ref"] else None
            except (OSError, ValueError):
                audio = None
            if audio is None:
                early = "recording_unavailable"
        if early is not None:
            _fail(conn, user_id, session_id, transcript["id"], provider.name if provider else "none", provider.method if provider else None, early, match, row["locale"], now)
            return _view(conn, ctx, user_id, row, repo.latest_assessment(conn, user_id, session_id))
        inp = PronunciationInput(target_text=item["text"], target_romanised=item["pronunciation"], locale=row["locale"], transcript_text=transcript["text"],
                                 transcript_confidence=transcript["confidence"], audio=audio, mime_type=row["audio_mime"], recording_ms=row["recording_ms"])

    # --- step 2 (no transaction): the provider call, time-limited, output validated ---
    outcome, failure = None, None
    try:
        outcome = validate_result(_call_provider(provider, inp), provider.capabilities)
        overall, components, words = outcome
        outcome = (aggregate(overall, components), components, words)
    except PronError as e:
        failure = e.code

    # --- step 3 (transaction): store the outcome ---
    purge = None
    with connect(db_path) as conn:
        ctx = learner_context(conn, user_id)
        row = speaking._owned(conn, user_id, session_id)
        now = clock.now()
        if failure is not None:
            _fail(conn, user_id, session_id, transcript["id"], provider.name, provider.method, failure, match, row["locale"], now)
        else:
            overall, components, words = outcome
            try:
                aid = repo.insert_assessment(conn, session_id, user_id, transcript["id"], provider.name, provider.method, "completed", None, overall,
                                             len(match.expected), match.matched, row["locale"], now)
            except sqlite3.IntegrityError:                                    # a concurrent request completed it first: return that one
                existing = repo.completed_assessment(conn, user_id, session_id)
                if existing is None:
                    raise
                return _view(conn, ctx, user_id, row, existing)
            repo.insert_components(conn, aid, components)
            repo.insert_word_scores(conn, aid, words)
            if not settings.keep_recordings() and row["audio_ref"]:           # the recording was only kept for this step
                purge = row["audio_ref"]
                speaking_repo.clear_recording(conn, user_id, session_id, now)
        view = _view(conn, ctx, user_id, row, repo.latest_assessment(conn, user_id, session_id))
    if purge:
        STORAGE_FACTORY().delete(purge)
    return view


def get_assessment(db_path, user_id, session_id):
    """The session's assessment (completed one, else the latest failed attempt), or None if it has not been assessed."""
    with connect(db_path) as conn:
        ctx = learner_context(conn, user_id)
        row = speaking._owned(conn, user_id, session_id)
        a = repo.latest_assessment(conn, user_id, session_id)
        return _view(conn, ctx, user_id, row, a) if a else None


def history(db_path, user_id, limit=20):
    with connect(db_path) as conn:
        ctx = learner_context(conn, user_id)
        rows = repo.history(conn, user_id, ctx["target_language_id"], limit)
        out = []
        for r in rows:
            item = speaking._item_view(conn, ctx, r["item_id"])
            out.append({"session_id": r["session_id"], "prompt": {"text": item["text"], "pronunciation": item["pronunciation"]}, "status": r["status"],
                        "pronunciation_score": r["overall_score"], "method": r["method"], "words_expected": r["words_expected"],
                        "words_matched": r["words_matched"], "created_at": r["created_at"]})
    return out


def progress(db_path, user_id):
    with connect(db_path) as conn:
        ctx = learner_context(conn, user_id)
        totals, by_method = repo.stats(conn, user_id, ctx["target_language_id"])
    return {"attempts": totals["attempts"], "failed": totals["failed"] or 0, "assessed_sessions": totals["assessed"],
            "content_match": {"words_expected": totals["expected"], "words_matched": totals["matched"]},
            # averages are kept per method so test or proxy scores are never blended with real measurements
            "pronunciation": [{"method": m["method"], "label": METHOD_LABELS[m["method"]], "assessments": m["n"], "average_score": round(m["average"], 1),
                               "is_measurement": m["method"] == "model"} for m in by_method]}
