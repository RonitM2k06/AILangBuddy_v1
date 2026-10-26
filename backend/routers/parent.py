"""HTTP layer for the parent portal. Identity comes only from the session. Parent endpoints need the parent role; the child is
always named by the parent's own link id, so an id that is not theirs is a 404 exactly like one that does not exist (nothing
here lets a parent discover learners). The learner endpoint that makes a link code needs the learner role."""
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field, StrictBool

from ..auth.deps import db_path, require_roles
from ..parent import service

router = APIRouter()


class LinkIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str = Field(min_length=4, max_length=40)


class ControlsIn(BaseModel):
    model_config = ConfigDict(extra="forbid")     # only known controls; a client cannot invent one
    voice_disabled: StrictBool                    # true/false only: "1", "yes", 1 are rejected


def _guard(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except service.NotFound:
        raise HTTPException(status_code=404, detail="Not found")
    except service.InvalidCode:
        raise HTTPException(status_code=404, detail="That code did not work. Ask your child to make a new one.")
    except service.Conflict as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except service.TooManyAttempts as exc:
        raise HTTPException(status_code=429, detail="Too many wrong codes. Try again later.", headers={"Retry-After": str(exc.retry_after)})
    except service.InvalidInput as exc:
        raise HTTPException(status_code=422, detail=[{"loc": ["body", exc.field], "msg": exc.message, "type": "value_error"}])


def _no_store(response):
    response.headers["Cache-Control"] = "no-store"


parent_only = require_roles("parent")


@router.post("/api/profile/parent-link-code", status_code=201)
def make_link_code(response: Response, user=Depends(require_roles("learner")), path=Depends(db_path)):
    """The learner shares this code with their parent. It works once, for a few minutes."""
    _no_store(response)
    return _guard(service.issue_code, path, user.id)


@router.post("/api/parent/children", status_code=201)
def link_child(body: LinkIn, response: Response, user=Depends(parent_only), path=Depends(db_path)):
    _no_store(response)
    return {"child": _guard(service.link_with_code, path, user.id, body.code)}


@router.get("/api/parent/children")
def list_children(response: Response, user=Depends(parent_only), path=Depends(db_path)):
    _no_store(response)
    return {"children": _guard(service.list_children, path, user.id)}


@router.delete("/api/parent/children/{link_id}")
def unlink_child(link_id: int, response: Response, user=Depends(parent_only), path=Depends(db_path)):
    _no_store(response)
    _guard(service.unlink, path, user.id, link_id)
    return {"ok": True}


@router.get("/api/parent/children/{link_id}/overview")
def overview(link_id: int, response: Response, user=Depends(parent_only), path=Depends(db_path)):
    _no_store(response)
    return _guard(service.overview, path, user.id, link_id)


@router.get("/api/parent/children/{link_id}/progress")
def progress(link_id: int, response: Response, user=Depends(parent_only), path=Depends(db_path)):
    _no_store(response)
    return _guard(service.progress, path, user.id, link_id)


@router.get("/api/parent/children/{link_id}/weaknesses")
def weaknesses(link_id: int, response: Response, user=Depends(parent_only), path=Depends(db_path)):
    _no_store(response)
    return _guard(service.weaknesses_view, path, user.id, link_id)


@router.get("/api/parent/children/{link_id}/confidence")
def confidence(link_id: int, response: Response, user=Depends(parent_only), path=Depends(db_path)):
    _no_store(response)
    return _guard(service.confidence_view, path, user.id, link_id)


@router.get("/api/parent/children/{link_id}/activity")
def activity(link_id: int, response: Response, user=Depends(parent_only), path=Depends(db_path)):
    _no_store(response)
    return _guard(service.activity_view, path, user.id, link_id)


@router.get("/api/parent/children/{link_id}/controls")
def get_controls(link_id: int, response: Response, user=Depends(parent_only), path=Depends(db_path)):
    _no_store(response)
    return {"controls": _guard(service.get_controls, path, user.id, link_id)}


@router.put("/api/parent/children/{link_id}/controls")
def put_controls(link_id: int, body: ControlsIn, response: Response, user=Depends(parent_only), path=Depends(db_path)):
    _no_store(response)
    return {"controls": _guard(service.set_controls, path, user.id, link_id, voice_disabled=body.voice_disabled)}
