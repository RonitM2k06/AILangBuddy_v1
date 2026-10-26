"""HTTP layer for the learner profile and the learning catalogue (CEFR levels, supported combinations)."""
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field

from ..auth.deps import db_path, require_roles
from ..learner import service
from ..repositories import catalog

router = APIRouter()


class ProfileIn(BaseModel):
    # Identity and age group are never accepted from the client: the user comes from the session,
    # the age group is derived from date_of_birth. Any extra field is rejected.
    model_config = ConfigDict(extra="forbid")
    native_language: str = Field(min_length=1, max_length=20)
    target_language: str = Field(min_length=1, max_length=20)
    cefr_level: str = Field(min_length=1, max_length=5)
    date_of_birth: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")


@router.get("/api/cefr-levels")
def cefr_levels(path=Depends(db_path)):
    return {"levels": catalog.list_cefr_levels(path)}


@router.get("/api/language-levels")
def language_levels(path=Depends(db_path)):
    return {"language_levels": catalog.list_language_levels(path)}


@router.get("/api/profile")
def get_profile(response: Response, user=Depends(require_roles("learner")), path=Depends(db_path)):
    response.headers["Cache-Control"] = "no-store"
    return {"profile": service.get_profile(path, user.id)}


@router.get("/api/content-review")
def content_review(response: Response, user=Depends(require_roles("learner")), path=Depends(db_path)):
    """How the content of the learner's own target language has been checked: an editorial pass, a native review, known limitations.
    {"language": null, "review": null} before a profile exists; "review" is null for a language without a recorded review."""
    response.headers["Cache-Control"] = "no-store"
    profile = service.get_profile(path, user.id)
    code = profile["target_language"] if profile else None
    return {"language": code, "review": catalog.content_review(path, code) if code else None}


@router.put("/api/profile")
def put_profile(body: ProfileIn, response: Response, user=Depends(require_roles("learner")), path=Depends(db_path)):
    try:
        profile = service.save_profile(path, user.id, **body.model_dump())
    except service.ProfileError as exc:
        raise HTTPException(status_code=422, detail=[{"loc": ["body", exc.field], "msg": exc.message, "type": "value_error"}])
    except service.AgeGroupLocked:
        raise HTTPException(status_code=409, detail="Your date of birth can't move you to a different age group while a parent is linked to your account.")
    response.headers["Cache-Control"] = "no-store"
    return {"profile": profile}
