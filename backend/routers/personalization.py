"""HTTP layer for confidence, weaknesses, difficulty, recommendations and the daily plan. Always the session's own learner."""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, Field

from ..auth.deps import db_path, require_roles
from ..personalization import confidence, context, difficulty, plan, recommendations, weaknesses

router = APIRouter()


class ConfidenceIn(BaseModel):
    model_config = ConfigDict(extra="forbid")  # the user comes from the session, never the body
    topic: str | None = Field(default=None, max_length=40)
    skill: str | None = Field(default=None, max_length=40)
    score: int = Field(ge=0, le=100)
    source: Literal["self_report", "lesson", "situation"] = "self_report"
    lesson_id: int | None = Field(default=None, ge=1)
    situation_id: int | None = Field(default=None, ge=1)


class TaskStatusIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["pending", "done", "skipped"]


def _guard(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except context.NeedsProfile:
        raise HTTPException(status_code=409, detail="Set up your learner profile first")
    except context.NotFound:
        raise HTTPException(status_code=404, detail="Not found")
    except context.InvalidInput as exc:
        raise HTTPException(status_code=422, detail=[{"loc": ["body", exc.field], "msg": exc.message, "type": "value_error"}])


def _no_store(response):
    response.headers["Cache-Control"] = "no-store"


@router.post("/api/confidence", status_code=201)
def record_confidence(body: ConfidenceIn, user=Depends(require_roles("learner")), path=Depends(db_path)):
    return {"confidence": _guard(confidence.record, path, user.id, **body.model_dump())}


@router.get("/api/confidence")
def get_confidence(response: Response, user=Depends(require_roles("learner")), path=Depends(db_path)):
    _no_store(response)
    return _guard(confidence.overview, path, user.id)


@router.get("/api/confidence/history")
def confidence_history(response: Response, topic: str | None = Query(default=None, max_length=40), skill: str | None = Query(default=None, max_length=40),
                       limit: int = Query(default=50, ge=1, le=200), user=Depends(require_roles("learner")), path=Depends(db_path)):
    _no_store(response)
    return {"history": _guard(confidence.history, path, user.id, topic=topic, skill=skill, limit=limit)}


@router.get("/api/weaknesses")
def get_weaknesses(response: Response, user=Depends(require_roles("learner")), path=Depends(db_path)):
    _no_store(response)
    return {"weaknesses": _guard(weaknesses.list_weaknesses, path, user.id)}


@router.get("/api/difficulty")
def get_difficulty(response: Response, user=Depends(require_roles("learner")), path=Depends(db_path)):
    _no_store(response)
    return {"difficulty": _guard(difficulty.get_recommendation, path, user.id)}


@router.get("/api/recommendations")
def get_recommendations(response: Response, user=Depends(require_roles("learner")), path=Depends(db_path)):
    _no_store(response)
    return _guard(recommendations.get_recommendations, path, user.id)


@router.get("/api/daily-plan")
def get_daily_plan(response: Response, user=Depends(require_roles("learner")), path=Depends(db_path)):
    _no_store(response)
    return {"plan": _guard(plan.get_plan, path, user.id)}


@router.post("/api/daily-plan/generate")
def generate_daily_plan(response: Response, user=Depends(require_roles("learner")), path=Depends(db_path)):
    _no_store(response)
    return {"plan": _guard(plan.generate_plan, path, user.id)}


@router.post("/api/daily-plan/tasks/{task_id}/status")
def set_task_status(task_id: int, body: TaskStatusIn, user=Depends(require_roles("learner")), path=Depends(db_path)):
    return {"task": _guard(plan.set_task_status, path, user.id, task_id, body.status)}
