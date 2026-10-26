"""HTTP layer for gamification and friends. Learners only; identity comes from the session. Nothing here accepts an XP amount, a
level, a date, an achievement or a score: the server works all of those out from what the learner has done."""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, Field

from ..auth.deps import db_path, require_roles
from ..gamification import service as gamification
from ..social import service as social

router = APIRouter()


class TimezoneIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    timezone: str = Field(min_length=1, max_length=64)


class FriendCodeIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str = Field(min_length=4, max_length=40)


class _Empty(BaseModel):
    model_config = ConfigDict(extra="forbid")      # these actions take no input at all: a body with xp, user_id... is rejected


def _guard(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except social.NeedsProfile:
        raise HTTPException(status_code=409, detail="Set up your learner profile first")
    except social.Forbidden:
        raise HTTPException(status_code=403, detail="This is not available for your age group")
    except (social.NotFound, gamification.NotFound):
        raise HTTPException(status_code=404, detail="Not found")
    except social.InvalidCode:
        raise HTTPException(status_code=404, detail="That code did not work. Ask your friend for their current code.")
    except (social.Conflict, gamification.Conflict) as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except social.TooManyAttempts as exc:
        raise HTTPException(status_code=429, detail="Too many wrong codes. Try again later.", headers={"Retry-After": str(exc.retry_after)})
    except (social.InvalidInput, gamification.InvalidInput) as exc:
        raise HTTPException(status_code=422, detail=[{"loc": ["body", exc.field], "msg": exc.message, "type": "value_error"}])


def _no_store(response):
    response.headers["Cache-Control"] = "no-store"


learner = require_roles("learner")


# ---------- gamification ----------
@router.get("/api/gamification")
def get_summary(response: Response, user=Depends(learner), path=Depends(db_path)):
    _no_store(response)
    return _guard(gamification.summary, path, user.id)


@router.put("/api/gamification/settings")
def put_settings(body: TimezoneIn, response: Response, user=Depends(learner), path=Depends(db_path)):
    _no_store(response)
    return _guard(gamification.set_timezone, path, user.id, body.timezone)


@router.get("/api/gamification/achievements")
def get_achievements(response: Response, user=Depends(learner), path=Depends(db_path)):
    _no_store(response)
    return {"achievements": _guard(gamification.achievements, path, user.id)}


@router.get("/api/gamification/challenges")
def get_challenges(response: Response, user=Depends(learner), path=Depends(db_path)):
    _no_store(response)
    return {"challenges": _guard(gamification.challenges, path, user.id)}


@router.post("/api/gamification/challenges/{challenge_id}/claim")
def claim_challenge(challenge_id: int, response: Response, body: _Empty | None = None, user=Depends(learner), path=Depends(db_path)):
    _no_store(response)
    return _guard(gamification.claim, path, user.id, challenge_id)


# ---------- social ----------
@router.get("/api/social/friends")
def get_friends(response: Response, user=Depends(learner), path=Depends(db_path)):
    _no_store(response)
    return _guard(social.friends, path, user.id)


@router.post("/api/social/friend-code")
def new_friend_code(response: Response, body: _Empty | None = None, user=Depends(learner), path=Depends(db_path)):
    _no_store(response)
    return _guard(social.rotate_code, path, user.id)


@router.post("/api/social/friends/requests", status_code=201)
def send_request(body: FriendCodeIn, response: Response, user=Depends(learner), path=Depends(db_path)):
    _no_store(response)
    return {"request": _guard(social.send_request, path, user.id, body.code)}


@router.post("/api/social/friends/requests/{request_id}/accept")
def accept_request(request_id: int, response: Response, body: _Empty | None = None, user=Depends(learner), path=Depends(db_path)):
    _no_store(response)
    return _guard(social.accept, path, user.id, request_id)


@router.post("/api/social/friends/requests/{request_id}/reject")
def reject_request(request_id: int, response: Response, body: _Empty | None = None, user=Depends(learner), path=Depends(db_path)):
    _no_store(response)
    return _guard(social.reject, path, user.id, request_id)


@router.delete("/api/social/friends/{friendship_id}")
def remove_friend(friendship_id: int, response: Response, user=Depends(learner), path=Depends(db_path)):
    _no_store(response)
    _guard(social.remove_friend, path, user.id, friendship_id)
    return {"ok": True}


@router.get("/api/social/leaderboard")
def get_leaderboard(response: Response, period: Literal["week", "all"] = Query(default="week"), user=Depends(learner), path=Depends(db_path)):
    _no_store(response)
    return _guard(social.leaderboard, path, user.id, period)
