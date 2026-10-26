"""HTTP layer for pronunciation assessment. Always the session's own learner: no user id is ever read from a request, and another
learner's session or assessment is indistinguishable from one that does not exist."""
from fastapi import APIRouter, Depends, HTTPException, Query, Response

from ..auth.deps import db_path, require_roles
from ..speaking import assessment, service

router = APIRouter()


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


def _no_store(response):
    response.headers["Cache-Control"] = "no-store"


# Fixed paths first (they never collide with /sessions/{id}/..., but keep the habit).
@router.get("/api/speaking/pronunciation/history")
def history(response: Response, limit: int = Query(default=20, ge=1, le=100), user=Depends(require_roles("learner")), path=Depends(db_path)):
    _no_store(response)
    return {"history": _guard(assessment.history, path, user.id, limit)}


@router.get("/api/speaking/pronunciation/progress")
def progress(response: Response, user=Depends(require_roles("learner")), path=Depends(db_path)):
    _no_store(response)
    return {"progress": _guard(assessment.progress, path, user.id)}


@router.post("/api/speaking/sessions/{session_id}/assess-pronunciation")
def assess(session_id: int, response: Response, user=Depends(require_roles("learner")), path=Depends(db_path)):
    """Idempotent. A provider failure is a normal outcome: 200 with status 'failed' and an error code, never a 500."""
    _no_store(response)
    return {"assessment": _guard(assessment.assess, path, user.id, session_id)}


@router.get("/api/speaking/sessions/{session_id}/pronunciation")
def get_pronunciation(session_id: int, response: Response, user=Depends(require_roles("learner")), path=Depends(db_path)):
    """The session's assessment, or {"assessment": null} when it has not been assessed (an unknown or foreign session is a 404)."""
    _no_store(response)
    return {"assessment": _guard(assessment.get_assessment, path, user.id, session_id)}
