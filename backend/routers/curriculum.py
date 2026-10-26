"""HTTP layer for lessons, exercise attempts and progress. Always the session's own learner."""
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field

from ..auth.deps import db_path, require_roles
from ..curriculum import service

router = APIRouter()


class AttemptIn(BaseModel):
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
    except service.AttemptError as exc:
        raise HTTPException(status_code=422, detail=[{"loc": ["body", exc.field], "msg": exc.message, "type": "value_error"}])


@router.get("/api/lessons")
def lessons(response: Response, user=Depends(require_roles("learner")), path=Depends(db_path)):
    response.headers["Cache-Control"] = "no-store"
    return {"lessons": _guard(service.list_lessons, path, user.id)}


@router.get("/api/lessons/{lesson_id}")
def lesson(lesson_id: int, response: Response, user=Depends(require_roles("learner")), path=Depends(db_path)):
    response.headers["Cache-Control"] = "no-store"
    return {"lesson": _guard(service.get_lesson, path, user.id, lesson_id)}


@router.post("/api/exercises/{exercise_id}/attempts")
def attempt(exercise_id: int, body: AttemptIn, user=Depends(require_roles("learner")), path=Depends(db_path)):
    return _guard(service.submit_attempt, path, user.id, exercise_id, answer_id=body.answer_id, text=body.text)


@router.get("/api/progress/lessons")
def progress(response: Response, user=Depends(require_roles("learner")), path=Depends(db_path)):
    response.headers["Cache-Control"] = "no-store"
    return {"progress": _guard(service.lesson_progress, path, user.id)}
