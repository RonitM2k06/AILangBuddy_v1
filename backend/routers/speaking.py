"""HTTP layer for speaking practice. Always the session's own learner: no user id is ever read from a request, and a session that
belongs to someone else is indistinguishable from one that does not exist."""
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from .. import settings
from ..auth.deps import db_path, require_roles
from ..speaking import service
from ..speaking.storage import UploadError

router = APIRouter()


class SessionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")      # a client-sent user_id, stage, transcript... is rejected, not ignored
    item_id: int | None = Field(default=None, ge=1)


def _guard(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except service.NeedsProfile:
        raise HTTPException(status_code=409, detail="Set up your learner profile first")
    except service.Forbidden:
        raise HTTPException(status_code=403, detail="Voice practice is not available for this account")
    except service.NotFound:
        raise HTTPException(status_code=404, detail="Not found")
    except service.Conflict as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except UploadError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.message)
    except service.InvalidInput as exc:
        raise HTTPException(status_code=422, detail=[{"loc": ["body", exc.field], "msg": exc.message, "type": "value_error"}])


async def _read_limited(request: Request, limit: int) -> bytes:
    """Read the raw request body but stop as soon as it exceeds the limit (never buffer an oversized upload)."""
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > limit:
        raise HTTPException(status_code=413, detail="The recording is too large.")
    chunks, total = [], 0
    async for chunk in request.stream():
        total += len(chunk)
        if total > limit:
            raise HTTPException(status_code=413, detail="The recording is too large.")
        chunks.append(chunk)
    return b"".join(chunks)


def _no_store(response):
    response.headers["Cache-Control"] = "no-store"


@router.get("/api/speaking/prompts")
def prompts(response: Response, user=Depends(require_roles("learner")), path=Depends(db_path)):
    _no_store(response)
    return _guard(service.list_prompts, path, user.id)


@router.get("/api/speaking/progress")
def progress(response: Response, user=Depends(require_roles("learner")), path=Depends(db_path)):
    _no_store(response)
    return {"progress": _guard(service.progress, path, user.id)}


@router.post("/api/speaking/sessions", status_code=201)
def create_session(response: Response, body: SessionIn | None = None, user=Depends(require_roles("learner")), path=Depends(db_path)):
    _no_store(response)
    return {"session": _guard(service.create_session, path, user.id, body.item_id if body else None)}


@router.get("/api/speaking/sessions")
def list_sessions(response: Response, limit: int = Query(default=20, ge=1, le=100), user=Depends(require_roles("learner")), path=Depends(db_path)):
    _no_store(response)
    return {"sessions": _guard(service.list_sessions, path, user.id, limit)}


@router.get("/api/speaking/sessions/{session_id}")
def get_session(session_id: int, response: Response, user=Depends(require_roles("learner")), path=Depends(db_path)):
    _no_store(response)
    return {"session": _guard(service.get_session, path, user.id, session_id)}


@router.post("/api/speaking/sessions/{session_id}/recording")
async def upload_recording(session_id: int, request: Request, response: Response, duration_ms: int | None = Query(default=None),
                           user=Depends(require_roles("learner")), path=Depends(db_path)):
    """The recording is the raw request body (Content-Type: the audio type), so no multipart library is needed."""
    _no_store(response)
    data = await _read_limited(request, settings.MAX_RECORDING_BYTES)
    return {"session": _guard(service.store_recording, path, user.id, session_id, data, request.headers.get("content-type"), duration_ms)}


@router.post("/api/speaking/sessions/{session_id}/transcribe")
def transcribe(session_id: int, response: Response, user=Depends(require_roles("learner")), path=Depends(db_path)):
    """A provider failure is a normal outcome: 200 with stage 'failed' and an error code, never a 500."""
    _no_store(response)
    return {"session": _guard(service.transcribe, path, user.id, session_id)}


@router.post("/api/speaking/sessions/{session_id}/cancel")
def cancel(session_id: int, response: Response, user=Depends(require_roles("learner")), path=Depends(db_path)):
    _no_store(response)
    return {"session": _guard(service.cancel, path, user.id, session_id)}
