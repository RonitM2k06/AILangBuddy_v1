"""HTTP layer for the AI tutor and roleplay. Learners only; identity always comes from the session, and a conversation or session that
belongs to someone else is a 404, exactly like one that does not exist. Nothing here accepts an answer key, a verdict, XP or a user id."""
import re

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ..auth.deps import db_path, require_roles
from ..roleplay import service as roleplay
from ..tutor import service as tutor

router = APIRouter()
_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


class ConversationIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    lesson_id: int | None = Field(default=None, ge=1)
    situation_id: int | None = Field(default=None, ge=1)
    topic: str | None = Field(default=None, min_length=1, max_length=40)

    @model_validator(mode="after")
    def one_context(self):
        if sum(v is not None for v in (self.lesson_id, self.situation_id, self.topic)) > 1:
            raise ValueError("choose at most one of lesson_id, situation_id, topic")
        return self


class _WithClientId(BaseModel):
    client_id: str | None = None

    @field_validator("client_id")
    @classmethod
    def valid_client_id(cls, v):
        if v is not None and not _ID.match(v):
            raise ValueError("client_id must be 1-64 letters, digits, - or _")
        return v


class MessageIn(_WithClientId):
    model_config = ConfigDict(extra="forbid")
    message: str | None = Field(default=None, max_length=2000)
    quick_prompt: str | None = Field(default=None, max_length=40)


class StartIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    situation_id: int = Field(ge=1)


class TurnIn(_WithClientId):
    model_config = ConfigDict(extra="forbid")
    text: str | None = Field(default=None, max_length=2000)
    speaking_session_id: int | None = Field(default=None, ge=1)


class _Empty(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _guard(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except tutor.NeedsProfile:
        raise HTTPException(status_code=409, detail="Set up your learner profile first")
    except tutor.Forbidden:
        raise HTTPException(status_code=403, detail="Voice practice is not available for this account")
    except tutor.NotFound:
        raise HTTPException(status_code=404, detail="Not found")
    except (tutor.Conflict, roleplay.Conflict) as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except tutor.AiUnavailable:
        raise HTTPException(status_code=502, detail="The tutor couldn't answer right now. Please try again.")
    except tutor.InvalidInput as exc:
        raise HTTPException(status_code=422, detail=[{"loc": ["body", exc.field], "msg": exc.message, "type": "value_error"}])


def _no_store(response):
    response.headers["Cache-Control"] = "no-store"


learner = require_roles("learner")


# ---------- tutor ----------
@router.get("/api/tutor/conversations")
def list_conversations(response: Response, user=Depends(learner), path=Depends(db_path)):
    _no_store(response)
    return {"conversations": _guard(tutor.list_conversations, path, user.id)}


@router.post("/api/tutor/conversations", status_code=201)
def create_conversation(body: ConversationIn, response: Response, user=Depends(learner), path=Depends(db_path)):
    _no_store(response)
    return _guard(tutor.create_conversation, path, user.id, lesson_id=body.lesson_id, situation_id=body.situation_id, topic=body.topic)


@router.get("/api/tutor/conversations/{conversation_id}")
def get_conversation(conversation_id: int, response: Response, user=Depends(learner), path=Depends(db_path)):
    _no_store(response)
    return _guard(tutor.get_conversation, path, user.id, conversation_id)


@router.get("/api/tutor/conversations/{conversation_id}/messages")
def get_messages(conversation_id: int, response: Response, after_seq: int = Query(default=0, ge=0), limit: int = Query(default=50, ge=1, le=100),
                 user=Depends(learner), path=Depends(db_path)):
    _no_store(response)
    return {"messages": _guard(tutor.get_messages, path, user.id, conversation_id, after_seq, limit)}


@router.post("/api/tutor/conversations/{conversation_id}/messages")
def send_message(conversation_id: int, body: MessageIn, response: Response, user=Depends(learner), path=Depends(db_path)):
    _no_store(response)
    return _guard(tutor.send_message, path, user.id, conversation_id, message=body.message, quick_prompt=body.quick_prompt, client_id=body.client_id)


# ---------- roleplay ----------
@router.get("/api/roleplay/sessions")
def list_sessions(response: Response, user=Depends(learner), path=Depends(db_path)):
    _no_store(response)
    return {"sessions": _guard(roleplay.list_sessions, path, user.id)}


@router.post("/api/roleplay/sessions", status_code=201)
def start_session(body: StartIn, response: Response, user=Depends(learner), path=Depends(db_path)):
    _no_store(response)
    result, resumed = _guard(roleplay.start, path, user.id, body.situation_id)
    if resumed:
        response.status_code = 200                      # starting the same situation again resumes the active session
    return {**result, "resumed": resumed}


@router.get("/api/roleplay/sessions/{session_id}")
def get_session(session_id: int, response: Response, user=Depends(learner), path=Depends(db_path)):
    _no_store(response)
    return _guard(roleplay.get, path, user.id, session_id)


@router.post("/api/roleplay/sessions/{session_id}/turns")
def post_turn(session_id: int, body: TurnIn, response: Response, user=Depends(learner), path=Depends(db_path)):
    _no_store(response)
    return _guard(roleplay.turn, path, user.id, session_id, text=body.text, speaking_session_id=body.speaking_session_id, client_id=body.client_id)


@router.post("/api/roleplay/sessions/{session_id}/complete")
def complete_session(session_id: int, response: Response, body: _Empty | None = None, user=Depends(learner), path=Depends(db_path)):
    _no_store(response)
    return _guard(roleplay.complete, path, user.id, session_id)


@router.get("/api/roleplay/sessions/{session_id}/feedback")
def get_feedback(session_id: int, response: Response, user=Depends(learner), path=Depends(db_path)):
    _no_store(response)
    return _guard(roleplay.get_feedback, path, user.id, session_id)
