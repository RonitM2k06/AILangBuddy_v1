"""HTTP layer for authentication: registration, sign-in, sessions, password change. (The admin account listing moved to routers/admin.py in Phase 14E.)"""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Request, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .. import settings
from ..auth import service
from ..auth.deps import db_path, require_user

router = APIRouter()

EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class LoginIn(BaseModel):
    model_config = ConfigDict(extra="forbid")  # e.g. a client-sent "roles" or "user_id" is rejected, not ignored
    email: str = Field(max_length=254, pattern=EMAIL_PATTERN)
    password: str = Field(min_length=1, max_length=128)  # the strength policy applies at registration only


def _not_blank_password(v):
    # The strength policy: 8 to 128 characters (any Unicode), not only whitespace. It is never trimmed or otherwise changed.
    if not v.strip():
        raise ValueError("must not be only whitespace")
    return v


class RegisterIn(LoginIn):
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=60)
    # Self-service registration can only ever create a learner or a parent. Admins are created out of band.
    role: Literal["learner", "parent"] = "learner"

    @field_validator("password")
    @classmethod
    def _password_policy(cls, v):
        return _not_blank_password(v)

    @field_validator("display_name")
    @classmethod
    def _strip(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("must not be blank")
        return v


class PasswordChangeIn(BaseModel):
    model_config = ConfigDict(extra="forbid")       # no user id or email: the account is the session's
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def _password_policy(cls, v):
        return _not_blank_password(v)


def _client(request):
    return request.client.host if request.client else "-"


def _too_many(exc):
    return HTTPException(status_code=429, detail="Too many attempts. Try again later.", headers={"Retry-After": str(exc.retry_after)})


def _user_json(user):
    return {"user": {"handle": user.handle, "display_name": user.display_name, "email": user.email, "roles": sorted(user.roles)}}


def _set_cookie(response, token):
    response.set_cookie(
        settings.COOKIE_NAME, token, max_age=settings.SESSION_TTL_DAYS * 86400, path="/",
        httponly=True, samesite="lax", secure=settings.cookie_secure(),
    )


CHALLENGE_PATH = "/api/auth/2fa"          # the login-challenge cookie is only ever sent to the two-factor endpoints


def set_challenge_cookie(response, token):
    """The step between a correct password and the second factor. Opaque random token (only its hash is stored); never a session."""
    response.set_cookie(settings.MFA_COOKIE_NAME, token, max_age=settings.MFA_CHALLENGE_SECONDS, path=CHALLENGE_PATH,
                        httponly=True, samesite="lax", secure=settings.cookie_secure())


def clear_challenge_cookie(response):
    response.delete_cookie(settings.MFA_COOKIE_NAME, path=CHALLENGE_PATH, httponly=True, samesite="lax", secure=settings.cookie_secure())


def _clear_cookie(response):
    response.delete_cookie(settings.COOKIE_NAME, path="/", httponly=True, samesite="lax", secure=settings.cookie_secure())


@router.post("/api/auth/register", status_code=201)
def register(body: RegisterIn, request: Request, response: Response, path=Depends(db_path)):
    try:
        user, token = service.create_user(path, email=body.email, password=body.password, display_name=body.display_name, roles=[body.role],
                                          client=_client(request), replaces=request.cookies.get(settings.COOKIE_NAME))
    except service.TooManyAttempts as exc:
        raise _too_many(exc)
    except service.EmailTaken:
        raise HTTPException(status_code=409, detail="That email is already registered")
    _set_cookie(response, token)
    response.headers["Cache-Control"] = "no-store"
    return _user_json(user)


@router.post("/api/auth/login")
def login(body: LoginIn, request: Request, response: Response, path=Depends(db_path)):
    try:
        user, token = service.login(path, email=body.email, password=body.password, client=_client(request),
                                    replaces=request.cookies.get(settings.COOKIE_NAME))
    except service.TooManyAttempts as exc:
        raise _too_many(exc)
    except service.InvalidCredentials:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    except service.MfaRequired as exc:                # no session yet: only the challenge cookie, and nothing about the account
        set_challenge_cookie(response, exc.challenge_token)
        return {"mfa_required": True}
    _set_cookie(response, token)
    response.headers["Cache-Control"] = "no-store"
    return _user_json(user)


@router.post("/api/auth/logout")
def logout(request: Request, response: Response, path=Depends(db_path)):
    service.logout(path, request.cookies.get(settings.COOKIE_NAME), client=_client(request))  # idempotent: fine with no/expired session
    _clear_cookie(response)
    return {"ok": True}


@router.post("/api/auth/logout-all")
def logout_all(request: Request, user=Depends(require_user), path=Depends(db_path)):
    """Signs out every OTHER session of this account; the one making the request stays signed in."""
    return {"ok": True, "revoked": service.logout_others(path, user, client=_client(request))}


@router.get("/api/auth/sessions")
def list_sessions(user=Depends(require_user), path=Depends(db_path)):
    return {"sessions": service.list_sessions(path, user)}


@router.delete("/api/auth/sessions/{public_id}")
def revoke_session(request: Request, response: Response, public_id: str = Path(max_length=64), user=Depends(require_user), path=Depends(db_path)):
    """Revoke one of your own sessions. Anything else, including another account's session, is a 404 exactly like an unknown id."""
    try:
        current = service.revoke_session(path, user, public_id, client=_client(request))
    except service.NotFound:
        raise HTTPException(status_code=404, detail="Not found")
    if current:
        _clear_cookie(response)
    return {"ok": True, "current": current}


@router.post("/api/auth/password")
def change_password(body: PasswordChangeIn, request: Request, response: Response, user=Depends(require_user), path=Depends(db_path)):
    """Every other session is signed out and this one gets a fresh token."""
    try:
        token = service.change_password(path, user, current_password=body.current_password, new_password=body.new_password, client=_client(request))
    except service.TooManyAttempts as exc:
        raise _too_many(exc)
    except service.WrongPassword:
        raise HTTPException(status_code=403, detail="The current password is not correct")
    _set_cookie(response, token)
    return {"ok": True}


@router.get("/api/auth/me")
def me(response: Response, user=Depends(require_user)):
    response.headers["Cache-Control"] = "no-store"
    return _user_json(user)
