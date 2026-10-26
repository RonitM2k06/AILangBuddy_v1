"""HTTP layer for the adaptive AI features. Learners only; identity comes from the session and every row is the caller's own (another learner's id is a
404). Nothing here accepts a score, an XP amount, a recommendation's content, a level or an answer key: the server works all of that out from stored evidence."""
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field

from ..adaptive import service
from ..auth.deps import db_path, require_roles

router = APIRouter()


class _Empty(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AnswerIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    choice: int | None = Field(default=None, ge=1, le=6)
    text: str | None = Field(default=None, max_length=2000)


def _guard(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except service.NeedsProfile:
        raise HTTPException(status_code=409, detail="Set up your learner profile first")
    except service.NotFound:
        raise HTTPException(status_code=404, detail="Not found")
    except service.Conflict as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except service.InvalidInput as exc:
        raise HTTPException(status_code=422, detail=[{"loc": ["body", exc.field], "msg": exc.message, "type": "value_error"}])


def _no_store(response):
    response.headers["Cache-Control"] = "no-store"


learner = require_roles("learner")


@router.get("/api/ai/recommendations")
def get_recommendations(response: Response, user=Depends(learner), path=Depends(db_path)):
    _no_store(response)
    return _guard(service.recommendations, path, user.id)


@router.post("/api/ai/recommendations/{recommendation_id}/apply")
def apply_recommendation(recommendation_id: int, response: Response, body: _Empty | None = None, user=Depends(learner), path=Depends(db_path)):
    _no_store(response)
    return _guard(service.apply, path, user.id, recommendation_id)


@router.get("/api/ai/insights")
def get_insights(response: Response, user=Depends(learner), path=Depends(db_path)):
    _no_store(response)
    return _guard(service.insights, path, user.id)


@router.get("/api/ai/micro-lessons")
def get_micro_lessons(response: Response, user=Depends(learner), path=Depends(db_path)):
    _no_store(response)
    return _guard(service.micro_lessons, path, user.id)


@router.post("/api/ai/micro-lessons/{micro_lesson_id}/answer")
def answer_micro_lesson(micro_lesson_id: int, body: AnswerIn, response: Response, user=Depends(learner), path=Depends(db_path)):
    _no_store(response)
    return _guard(service.answer_micro_lesson, path, user.id, micro_lesson_id, choice=body.choice, text=body.text)


@router.get("/api/ai/adaptive-plan")
def get_adaptive_plan(response: Response, user=Depends(learner), path=Depends(db_path)):
    _no_store(response)
    return _guard(service.adaptive_plan, path, user.id)
