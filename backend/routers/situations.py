"""HTTP layer for situational learning. Always the session's own learner."""
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field

from ..auth.deps import db_path, require_roles
from ..situations import service

router = APIRouter()


class ResponseIn(BaseModel):
    model_config = ConfigDict(extra="forbid")  # the user comes from the session, never the body
    answer_id: int | None = Field(default=None, ge=1)
    text: str | None = Field(default=None, max_length=service.MAX_TEXT_ANSWER * 2)


def _guard(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except service.NeedsProfile:
        raise HTTPException(status_code=409, detail="Set up your learner profile first")
    except service.NotFound:
        raise HTTPException(status_code=404, detail="Not found")
    except service.OutOfOrder:
        raise HTTPException(status_code=409, detail="Finish the current step first")
    except service.AttemptError as exc:
        raise HTTPException(status_code=422, detail=[{"loc": ["body", exc.field], "msg": exc.message, "type": "value_error"}])


@router.get("/api/situations")
def list_situations(response: Response, user=Depends(require_roles("learner")), path=Depends(db_path)):
    response.headers["Cache-Control"] = "no-store"
    return {"situations": _guard(service.list_situations, path, user.id)}


@router.get("/api/situations/{situation_id}")
def get_situation(situation_id: int, response: Response, user=Depends(require_roles("learner")), path=Depends(db_path)):
    response.headers["Cache-Control"] = "no-store"
    return {"situation": _guard(service.get_situation, path, user.id, situation_id)}


@router.post("/api/situations/{situation_id}/steps/{step_id}/responses")
def submit_response(situation_id: int, step_id: int, body: ResponseIn, user=Depends(require_roles("learner")), path=Depends(db_path)):
    return _guard(service.submit_response, path, user.id, situation_id, step_id, answer_id=body.answer_id, text=body.text)


@router.get("/api/progress/situations")
def progress(response: Response, user=Depends(require_roles("learner")), path=Depends(db_path)):
    response.headers["Cache-Control"] = "no-store"
    return {"progress": _guard(service.situation_progress, path, user.id)}
