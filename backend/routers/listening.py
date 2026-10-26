"""HTTP layer for listening activities. Always the session's own learner; no user id is ever read from a request."""
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, Field

from ..auth.deps import db_path, require_roles
from ..listening import service

router = APIRouter()


class AnswerIn(BaseModel):
    model_config = ConfigDict(extra="forbid")  # e.g. a client-sent user_id or is_correct is rejected, not ignored
    option_id: int = Field(ge=1)
    plays: int = Field(default=0, ge=0, le=service.MAX_PLAYS)
    response_ms: int | None = Field(default=None, ge=0, le=service.MAX_RESPONSE_MS)


def _guard(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except service.NeedsProfile:
        raise HTTPException(status_code=409, detail="Set up your learner profile first")
    except service.NotFound:
        raise HTTPException(status_code=404, detail="Not found")
    except service.InvalidInput as exc:
        raise HTTPException(status_code=422, detail=[{"loc": ["body", exc.field], "msg": exc.message, "type": "value_error"}])


# Fixed paths are declared before /{activity_id} so "attempts" and "progress" are never parsed as an id.
@router.get("/api/listening")
def list_activities(response: Response, user=Depends(require_roles("learner")), path=Depends(db_path)):
    response.headers["Cache-Control"] = "no-store"
    return {"activities": _guard(service.list_activities, path, user.id)}


@router.get("/api/listening/attempts")
def list_attempts(response: Response, limit: int = Query(default=50, ge=1, le=200), user=Depends(require_roles("learner")), path=Depends(db_path)):
    response.headers["Cache-Control"] = "no-store"
    return {"attempts": _guard(service.list_attempts, path, user.id, limit)}


@router.get("/api/listening/progress")
def get_progress(response: Response, user=Depends(require_roles("learner")), path=Depends(db_path)):
    response.headers["Cache-Control"] = "no-store"
    return {"progress": _guard(service.progress, path, user.id)}


@router.get("/api/listening/{activity_id}")
def get_activity(activity_id: int, response: Response, user=Depends(require_roles("learner")), path=Depends(db_path)):
    response.headers["Cache-Control"] = "no-store"
    return {"activity": _guard(service.get_activity, path, user.id, activity_id)}


@router.post("/api/listening/{activity_id}/attempts")
def submit_answer(activity_id: int, body: AnswerIn, user=Depends(require_roles("learner")), path=Depends(db_path)):
    return _guard(service.submit_answer, path, user.id, activity_id, option_id=body.option_id, plays=body.plays, response_ms=body.response_ms)
