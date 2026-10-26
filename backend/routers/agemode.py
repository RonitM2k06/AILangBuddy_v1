"""HTTP layer for the age-aware experience: the mode, the child adventure and the teen home. Always the session's own learner:
no user id is read from a request, lives cannot be set by a client, and levels, questions and choices are positions, not ids."""
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field

from ..auth.deps import db_path, require_roles
from ..experience import service as experience
from ..kids import service as kids

router = APIRouter()


class KidsAnswerIn(BaseModel):
    model_config = ConfigDict(extra="forbid")     # a client-sent lives, correct or user_id is rejected, not ignored
    question: int = Field(ge=1, le=100)
    choice: int = Field(ge=1, le=10)


def _guard(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except kids.NeedsProfile:
        raise HTTPException(status_code=409, detail="Set up your learner profile first")
    except kids.Forbidden:
        raise HTTPException(status_code=403, detail="This is not available for your age group")
    except kids.NotFound:
        raise HTTPException(status_code=404, detail="Not found")
    except kids.Locked:
        raise HTTPException(status_code=409, detail="Finish the level before this one first")
    except kids.NoLives as exc:
        headers = {"Retry-After": str(exc.next_life_in)} if exc.next_life_in else None
        raise HTTPException(status_code=409, detail={"message": "No lives left. Come back soon!", "next_life_in_seconds": exc.next_life_in}, headers=headers)
    except kids.InvalidInput as exc:
        raise HTTPException(status_code=422, detail=[{"loc": ["body", exc.field], "msg": exc.message, "type": "value_error"}])


@router.get("/api/experience")
def get_experience(response: Response, user=Depends(require_roles("learner")), path=Depends(db_path)):
    response.headers["Cache-Control"] = "no-store"
    return _guard(experience.experience, path, user.id)


@router.get("/api/kids/adventure")
def get_adventure(response: Response, user=Depends(require_roles("learner")), path=Depends(db_path)):
    response.headers["Cache-Control"] = "no-store"
    return _guard(kids.adventure, path, user.id)


@router.get("/api/kids/levels/{number}")
def get_level(number: int, response: Response, user=Depends(require_roles("learner")), path=Depends(db_path)):
    response.headers["Cache-Control"] = "no-store"
    return _guard(kids.level, path, user.id, number)


@router.post("/api/kids/levels/{number}/answers")
def post_answer(number: int, body: KidsAnswerIn, response: Response, user=Depends(require_roles("learner")), path=Depends(db_path)):
    response.headers["Cache-Control"] = "no-store"
    return _guard(kids.answer, path, user.id, number, body.question, body.choice)


@router.get("/api/teen/home")
def get_teen_home(response: Response, user=Depends(require_roles("learner")), path=Depends(db_path)):
    response.headers["Cache-Control"] = "no-store"
    return _guard(experience.teen_home, path, user.id)
