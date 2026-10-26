"""Speaking sessions for the authenticated learner: prompt -> recording -> speech-to-text -> transcript.

Pipeline stages (speaking_sessions.stage), with the only transitions the service allows:

    created --(recording stored)--> recorded --(transcribe)--> processing --> completed
        |                              |   ^                        |
        |                              |   '-- (retry transcribe) --+--> failed
        '-------- cancel --------------'---------- cancel ---------'

`completed` and `cancelled` are final. A failed transcription can be retried (a new STT run) or cancelled. The coarse
audio_sessions.status is kept in step: started while in flight, then completed / failed / abandoned.

The provider call happens OUTSIDE any database transaction (so a slow provider never holds the write lock), is bounded by a
timeout, and every failure becomes a stored, learner-safe error code. Nothing here scores pronunciation: the transcript is
only what the recogniser heard."""
import concurrent.futures
import logging
from datetime import datetime, timedelta

from .. import settings
from ..audio.service import default_service
from ..db import connect
from ..personalization import clock
from ..parent import controls as parent_controls
from ..personalization.context import Forbidden, InvalidInput, NeedsProfile, NotFound, learner_context  # noqa: F401  (re-exported)
from ..repositories import audio as audio_repo, situations, speaking as repo
from . import pron_providers, storage as storage_mod, stt

log = logging.getLogger(__name__)

AUDIO = default_service                 # how a model pronunciation is played (same abstraction as listening)
STT_FACTORY = stt.get_provider          # the provider in use (tests replace it); None means "not configured"
STORAGE_FACTORY = storage_mod.default_storage
_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=4, thread_name_prefix="stt")
_TIME = "%Y-%m-%d %H:%M:%S"
_AUDIO_STATUS = {"created": "started", "recorded": "started", "processing": "started",
                 "completed": "completed", "failed": "failed", "cancelled": "abandoned"}

ERROR_MESSAGES = {
    "provider_unavailable": "Speech recognition isn't available right now.",
    "provider_timeout": "Speech recognition took too long. Please try again.",
    "provider_error": "Speech recognition had a problem. Please try again.",
    "no_speech": "We couldn't hear any speech in that recording. Try again a little closer to the microphone.",
    "unsupported_language": "Speech recognition doesn't support this language yet.",
    "unsupported_format": "This recording format isn't supported.",
    "recording_unavailable": "The recording is no longer available. Please record again.",
}


class Conflict(Exception):
    """The session is not in a stage that allows this operation."""


def _parse(ts):
    return datetime.strptime(ts, _TIME)


def _sync(conn, user_id, session_id, stage, now):
    """Bring audio_sessions in line with the stage. Ended sessions get an end time and a duration (the recording length
    if known, else the elapsed time)."""
    status = _AUDIO_STATUS[stage]
    if status == "started":
        repo.sync_audio_session(conn, user_id, session_id, status, None, None)
        return
    row = repo.get_session(conn, user_id, session_id)
    started = conn.execute("SELECT started_at FROM audio_sessions WHERE id = ? AND user_id = ?", (session_id, user_id)).fetchone()[0]
    ended = max(now, started)          # never end before the start, whatever the clock does
    elapsed = int((_parse(ended) - _parse(started)).total_seconds() * 1000)
    repo.sync_audio_session(conn, user_id, session_id, status, ended, row["recording_ms"] or elapsed)


def _item_view(conn, ctx, item_id):
    it = situations.items_by_ids(conn, [item_id], ctx["native_language_id"], ctx["fallback_id"])[item_id]
    return {"id": it["id"], "text": it["text"], "pronunciation": it["pronunciation"], "meaning": it["meaning"], "natural": it["natural"]}


def _view(conn, ctx, user_id, row):
    """The learner-facing session. Never contains a file name, path, hash or user id."""
    source = AUDIO.resolve(conn, row["item_id"])
    run = repo.latest_run(conn, user_id, row["id"])
    transcript = repo.transcript_for(conn, user_id, row["id"])
    error = None
    if row["stage"] == "failed" and run and run["error_code"]:
        error = {"code": run["error_code"], "message": ERROR_MESSAGES[run["error_code"]]}
    return {
        "id": row["id"], "stage": row["stage"],
        "prompt": {"item": _item_view(conn, ctx, row["item_id"]), "audio": source.as_dict() if source else None, "locale": row["locale"]},
        "recording": None if not row["audio_mime"] else {"mime_type": row["audio_mime"], "bytes": row["audio_bytes"], "duration_ms": row["recording_ms"],
                                                         "recorded_at": row["recorded_at"], "kept": row["audio_ref"] is not None},
        "transcript": None if not transcript else {"text": transcript["text"], "confidence": transcript["confidence"],
                                                   "provider": transcript["provider"], "locale": transcript["locale"]},
        "error": error, "attempts": repo.run_count(conn, user_id, row["id"]),
        "created_at": row["created_at"], "updated_at": row["updated_at"],
    }


def _owned(conn, user_id, session_id):
    row = repo.get_session(conn, user_id, session_id)   # scoped by user: someone else's session is simply "not found"
    if row is None:
        raise NotFound()
    return row


def _expire_stale(conn, user_id, session_id):
    """A run still 'processing' long after it started (the server died mid-call) is closed as a timeout, so a session can
    never be stuck."""
    now = clock.now()
    cutoff = (_parse(now) - timedelta(seconds=settings.STT_STALE_PROCESSING_SECONDS)).strftime(_TIME)
    run_id = repo.stale_run(conn, user_id, session_id, cutoff)
    if run_id is not None:
        repo.finish_run(conn, run_id, "failed", "provider_timeout", now, None)
        repo.end_processing(conn, user_id, session_id, "failed", now)
        _sync(conn, user_id, session_id, "failed", now)


# ---------- prompts ----------
def list_prompts(db_path, user_id):
    sweep_expired(db_path)          # the page every practice starts from also keeps old recordings from lingering
    with connect(db_path) as conn:
        ctx = learner_context(conn, user_id)
        lang = ctx["target_language_id"]
        ids = repo.available_prompts(conn, lang, ctx["max_rank"], ctx["age_group_id"])
        done = repo.practised_items(conn, user_id, lang)
        items = situations.items_by_ids(conn, ids, ctx["native_language_id"], ctx["fallback_id"])
        lang_row = conn.execute("SELECT code, name, tts_locale FROM languages WHERE id = ?", (lang,)).fetchone()
        provider = STT_FACTORY()
        pron = pron_providers.configured()
    return {"pronunciation": {"available": pron is not None, "method": pron.method if pron else None},
            "prompts": [{"item": {k: items[i][k] for k in ("id", "text", "pronunciation", "meaning", "natural")}, "practised": i in done} for i in ids],
            "stt": {"provider": provider.name if provider else None, "available": provider is not None,
                    "max_recording_ms": settings.MAX_RECORDING_MS, "max_bytes": settings.MAX_RECORDING_BYTES},
            "capabilities": capabilities(lang_row, provider, pron)}


def _support(provider, locale):
    if provider is None:
        return "not_configured"
    return "available" if provider.capabilities.supports_language(locale) else "unsupported_language"


def capabilities(lang_row, stt_provider, pron_provider):
    """What can be done with the learner's language, BEFORE they record: so a page can offer an honest alternative up front instead of a
    failure afterwards. transcription / pronunciation: "available", "unsupported_language" (the configured engine does not handle this
    language) or "not_configured" (no engine at all). The typed check is always there: it compares typed words, never sound."""
    locale = lang_row["tts_locale"]
    transcription, pronunciation = _support(stt_provider, locale), _support(pron_provider, locale)
    alternatives = ["typed"]                                        # what the voice page offers whatever the engines (frontend/voice.js typed check)
    return {"language": lang_row["code"], "language_name": lang_row["name"], "locale": locale, "transcription": transcription,
            "pronunciation": pronunciation, "alternatives": alternatives}


# ---------- sessions ----------
def create_session(db_path, user_id, item_id=None):
    sweep_expired(db_path)          # housekeeping: never let old recordings pile up
    with connect(db_path) as conn:  # one transaction: the audio session and its speaking detail together
        ctx = learner_context(conn, user_id)
        parent_controls.require_voice(conn, ctx, user_id)     # child age group (Phase 8) or a parent's switch (Phase 9)
        lang = ctx["target_language_id"]
        if item_id is None:
            prompts = repo.available_prompts(conn, lang, ctx["max_rank"], ctx["age_group_id"])
            if not prompts:
                raise InvalidInput("item_id", "There are no speaking prompts for your language and level yet")
            done = repo.practised_items(conn, user_id, lang)
            item_id = next((i for i in prompts if i not in done), prompts[0])       # the next phrase not yet practised
        elif not repo.is_available_prompt(conn, item_id, lang, ctx["max_rank"], ctx["age_group_id"]):
            raise InvalidInput("item_id", "That phrase is not available for speaking practice")
        locale = audio_repo.item_speech(conn, item_id)["locale"]
        now = clock.now()
        session_id = repo.create_audio_session(conn, user_id, lang, now)
        repo.create_speaking_session(conn, session_id, user_id, lang, item_id, locale, now)
        return _view(conn, ctx, user_id, repo.get_session(conn, user_id, session_id))


def get_session(db_path, user_id, session_id):
    with connect(db_path) as conn:
        ctx = learner_context(conn, user_id)
        _owned(conn, user_id, session_id)
        _expire_stale(conn, user_id, session_id)
        return _view(conn, ctx, user_id, _owned(conn, user_id, session_id))


def store_recording(db_path, user_id, session_id, data, content_type, duration_ms=None):
    """Validate and store the learner's recording for a session that is waiting for one. The audio goes to the recordings
    directory; the database gets only metadata."""
    ref = None
    try:
        with connect(db_path) as conn:
            ctx = learner_context(conn, user_id)
            parent_controls.require_voice(conn, ctx, user_id)
            row = _owned(conn, user_id, session_id)
            if row["stage"] != "created":
                raise Conflict("This session already has a recording or is finished.")
            recording_ms = storage_mod.validate_duration(duration_ms)
            verified = storage_mod.validate_upload(data, content_type)
            ref = STORAGE_FACTORY().save(data, verified.ext)
            now = clock.now()
            if repo.mark_recorded(conn, user_id, session_id, ref, verified.mime, verified.size, verified.sha256, recording_ms, now) != 1:
                raise Conflict("This session already has a recording or is finished.")
            _sync(conn, user_id, session_id, "recorded", now)
            view = _view(conn, ctx, user_id, repo.get_session(conn, user_id, session_id))
        return view
    except BaseException:
        if ref is not None:
            STORAGE_FACTORY().delete(ref)       # never leave a file that the database does not know about
        raise


def _call_provider(provider, audio, mime, locale):
    """Run the provider with a hard time limit. Any failure becomes an SttError with a safe code."""
    future = _EXECUTOR.submit(provider.transcribe, audio, mime, locale)
    try:
        return future.result(timeout=settings.stt_timeout_seconds())
    except concurrent.futures.TimeoutError:
        future.cancel()
        raise stt.SttError("provider_timeout", "timeout")
    except stt.SttError:
        raise
    except Exception:                               # a bug in a provider must not reach the learner or crash the request
        log.exception("STT provider %s failed unexpectedly", getattr(provider, "name", "?"))
        raise stt.SttError("provider_error", "unexpected provider failure")


def _fail(conn, user_id, session_id, run_id, code, now, started):
    repo.finish_run(conn, run_id, "failed", code, now, int((_parse(now) - _parse(started)).total_seconds() * 1000))
    repo.end_processing(conn, user_id, session_id, "failed", now)
    _sync(conn, user_id, session_id, "failed", now)


def transcribe(db_path, user_id, session_id):
    """Transcribe a recorded (or previously failed) session. Returns the session; a failure is a normal, stored outcome
    (stage 'failed' with an error code), not an exception."""
    # --- step 1 (transaction): validate, claim the session, open a run ---
    with connect(db_path) as conn:
        ctx = learner_context(conn, user_id)
        parent_controls.require_voice(conn, ctx, user_id)
        _owned(conn, user_id, session_id)
        _expire_stale(conn, user_id, session_id)
        row = _owned(conn, user_id, session_id)
        if row["stage"] not in ("recorded", "failed"):
            raise Conflict("This session is not ready to be transcribed.")
        provider = STT_FACTORY()
        now = clock.now()
        if repo.begin_processing(conn, user_id, session_id, now) != 1:      # atomic claim: a second caller gets nothing
            raise Conflict("This session is already being transcribed.")
        run_id = repo.insert_run(conn, session_id, user_id, provider.name if provider else "none", row["locale"], now)
        _sync(conn, user_id, session_id, "processing", now)
        early = None
        audio = None
        if provider is None:
            early = "provider_unavailable"
        elif not provider.capabilities.supports_language(row["locale"]):
            early = "unsupported_language"
        elif row["audio_mime"] not in provider.capabilities.mime_types or row["audio_bytes"] > provider.capabilities.max_bytes:
            early = "unsupported_format"
        else:
            try:
                audio = STORAGE_FACTORY().read(row["audio_ref"])
            except (OSError, ValueError):
                early = "recording_unavailable"
        if early is not None:
            _fail(conn, user_id, session_id, run_id, early, now, now)
            return _view(conn, ctx, user_id, repo.get_session(conn, user_id, session_id))
        started, mime, locale = now, row["audio_mime"], row["locale"]

    # --- step 2 (no transaction): the provider call, time-limited ---
    result, failure = None, None
    try:
        result = _call_provider(provider, audio, mime, locale)
    except stt.SttError as e:
        failure = e.code

    # --- step 3 (transaction): record the outcome ---
    purge = None
    with connect(db_path) as conn:
        ctx = learner_context(conn, user_id)
        now = clock.now()
        text = (result.text or "").strip() if result else ""
        if failure is None and not text:
            failure = "no_speech"
        if failure is not None:
            _fail(conn, user_id, session_id, run_id, failure, max(now, started), started)
        else:
            repo.insert_transcript(conn, run_id, session_id, user_id, 1, text[:2000], _valid_confidence(result.confidence), locale, now)
            for rank, alt in enumerate((a.strip() for a in result.alternatives if a and a.strip()), start=2):
                repo.insert_transcript(conn, run_id, session_id, user_id, rank, alt[:2000], None, locale, now)
            repo.finish_run(conn, run_id, "completed", None, max(now, started), int((_parse(max(now, started)) - _parse(started)).total_seconds() * 1000))
            repo.end_processing(conn, user_id, session_id, "completed", now)
            final = repo.get_session(conn, user_id, session_id)
            if not settings.keep_recordings() and final["audio_ref"] and not _pronunciation_needs_audio():
                purge = final["audio_ref"]
                repo.clear_recording(conn, user_id, session_id, now)
            _sync(conn, user_id, session_id, "completed", now)
        view = _view(conn, ctx, user_id, repo.get_session(conn, user_id, session_id))
    if purge:
        STORAGE_FACTORY().delete(purge)          # after commit: the transcript is safe before the voice data goes
    return view


def _pronunciation_needs_audio():
    """With a pronunciation provider that analyses the recording, the file is kept for the assessment step instead of being deleted
    at transcription. sweep_expired() bounds how long (a few minutes); the default configuration (no provider) deletes at once."""
    provider = pron_providers.configured()
    return provider is not None and provider.capabilities.requires_audio


def sweep_expired(db_path):
    """Delete recordings that have outlived their purpose: a transcribed session's file after PRON_AUDIO_GRACE_SECONDS (it was only
    kept for an assessment), and a failed session's file after FAILED_AUDIO_GRACE_SECONDS. Metadata stays. Returns how many files
    were removed. Safe to call at any time; does nothing when SPEAKING_KEEP_AUDIO is on."""
    if settings.keep_recordings():
        return 0
    now = clock.now()
    cut = lambda seconds: (_parse(now) - timedelta(seconds=seconds)).strftime(_TIME)
    refs = []
    with connect(db_path) as conn:
        for r in repo.expired_recordings(conn, cut(settings.PRON_AUDIO_GRACE_SECONDS), cut(settings.FAILED_AUDIO_GRACE_SECONDS)):
            repo.clear_recording(conn, r["user_id"], r["session_id"], now)
            refs.append(r["audio_ref"])
    for ref in refs:
        try:
            STORAGE_FACTORY().delete(ref)
        except ValueError:
            log.warning("ignored an invalid recording reference during the sweep")
    return len(refs)


def _valid_confidence(value):
    """Keep a provider's confidence only if it is a real 0..1 number (never invent or pass on nonsense)."""
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) and 0 <= value <= 1 else None


def cancel(db_path, user_id, session_id):
    ref = None
    with connect(db_path) as conn:
        ctx = learner_context(conn, user_id)
        row = _owned(conn, user_id, session_id)
        now = clock.now()
        if repo.cancel(conn, user_id, session_id, now) != 1:
            raise Conflict("This session can no longer be cancelled.")
        if row["audio_ref"]:
            ref = row["audio_ref"]
            repo.clear_recording(conn, user_id, session_id, now)
        _sync(conn, user_id, session_id, "cancelled", now)
        view = _view(conn, ctx, user_id, repo.get_session(conn, user_id, session_id))
    if ref:
        STORAGE_FACTORY().delete(ref)
    return view


def list_sessions(db_path, user_id, limit=20):
    with connect(db_path) as conn:
        ctx = learner_context(conn, user_id)
        rows = repo.list_sessions(conn, user_id, ctx["target_language_id"], limit)
        out = []
        for r in rows:
            item = _item_view(conn, ctx, r["item_id"])
            t = repo.transcript_for(conn, user_id, r["id"])
            out.append({"id": r["id"], "stage": r["stage"], "prompt": {"text": item["text"], "pronunciation": item["pronunciation"], "meaning": item["meaning"]},
                        "transcript": t["text"] if t else None, "created_at": r["created_at"]})
    return out


def progress(db_path, user_id):
    with connect(db_path) as conn:
        ctx = learner_context(conn, user_id)
        lang = ctx["target_language_id"]
        counts, last = repo.progress_counts(conn, user_id, lang)
        available = repo.available_prompts(conn, lang, ctx["max_rank"], ctx["age_group_id"])
        practised = repo.practised_items(conn, user_id, lang)
    return {"sessions_total": sum(counts.values()), "completed": counts.get("completed", 0), "failed": counts.get("failed", 0),
            "cancelled": counts.get("cancelled", 0),
            "in_progress": counts.get("created", 0) + counts.get("recorded", 0) + counts.get("processing", 0),
            "prompts_available": len(available), "prompts_practised": len(practised & set(available)), "last_session_at": last}
