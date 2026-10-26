"""HTTP layer for TOTP two-factor authentication (Phase 14D). The rules live in backend/auth/mfa.py. Identity always comes from the session
(or, for /verify only, from the login-challenge cookie); no body names a user, and every write goes through the global CSRF guard."""
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, model_validator

from .. import settings
from ..auth import mfa
from ..auth.deps import db_path, require_user
from .auth import _client, _set_cookie, _too_many, _user_json, clear_challenge_cookie

router = APIRouter(prefix="/api/auth/2fa")


class PasswordIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    password: str = Field(min_length=1, max_length=128)


class CodeIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str = Field(min_length=1, max_length=16)                      # exactly six digits is checked by the TOTP module


class FactorIn(BaseModel):
    """A current TOTP code or a recovery code: exactly one."""
    model_config = ConfigDict(extra="forbid")
    code: str | None = Field(default=None, min_length=1, max_length=16)
    recovery_code: str | None = Field(default=None, min_length=1, max_length=32)

    @model_validator(mode="after")
    def exactly_one(self):
        if (self.code is None) == (self.recovery_code is None):
            raise ValueError("send either code or recovery_code")
        return self


class DisableIn(FactorIn):
    password: str = Field(min_length=1, max_length=128)


class RegenerateIn(CodeIn):
    password: str = Field(min_length=1, max_length=128)


def _guard(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except mfa.TooManyAttempts as exc:
        raise _too_many(exc)
    except mfa.NotConfigured:
        raise HTTPException(status_code=503, detail="Two-factor codes cannot be checked on this server right now")
    except mfa.AlreadyEnabled:
        raise HTTPException(status_code=409, detail="Two-factor authentication is already on")
    except mfa.NotEnabled:
        raise HTTPException(status_code=409, detail="Two-factor authentication is not on")
    except mfa.NoPendingSetup:
        raise HTTPException(status_code=409, detail="There is no setup waiting to be confirmed. Start the setup again.")
    except mfa.AdminCannotDisable:
        raise HTTPException(status_code=403, detail="Administrators cannot turn off two-factor authentication")
    except mfa.WrongCredentials:
        raise HTTPException(status_code=403, detail="That is not correct")


@router.get("")
def status(user=Depends(require_user), path=Depends(db_path)):
    return mfa.status(path, user)


@router.post("/setup")
def setup(body: PasswordIn, request: Request, user=Depends(require_user), path=Depends(db_path)):
    """Returns the setup material ONCE: the base32 key, the otpauth:// URI and its QR module matrix. Nothing is on until /confirm."""
    return _guard(mfa.begin_setup, path, user, body.password, client=_client(request))


@router.post("/confirm")
def confirm(body: CodeIn, request: Request, response: Response, user=Depends(require_user), path=Depends(db_path)):
    """Turns 2FA on and returns the recovery codes ONCE. This browser's session is replaced by one with the second factor."""
    codes, token = _guard(mfa.confirm_setup, path, user, body.code, request.cookies.get(settings.COOKIE_NAME), client=_client(request))
    _set_cookie(response, token)
    return {"ok": True, "recovery_codes": codes}


@router.post("/verify")
def verify(body: FactorIn, request: Request, path=Depends(db_path)):
    """The second step of signing in: the login-challenge cookie plus a code. Only this creates the session."""
    try:
        user, token = _guard(mfa.verify_challenge, path, request.cookies.get(settings.MFA_COOKIE_NAME), code=body.code,
                             recovery_code=body.recovery_code, presented_session=request.cookies.get(settings.COOKIE_NAME),
                             client=_client(request))
    except HTTPException as exc:
        if exc.status_code == 403:
            exc = HTTPException(status_code=401, detail="That code is not correct")
        if exc.status_code == 409:                       # 2FA was turned off meanwhile: start again
            exc = HTTPException(status_code=401, detail="Your sign-in has expired. Please sign in again.")
        raise exc
    except mfa.ChallengeInvalid:
        response = JSONResponse(status_code=401, content={"detail": "Your sign-in has expired. Please sign in again."})
        clear_challenge_cookie(response)
        return response
    response = JSONResponse(content=_user_json(user))
    _set_cookie(response, token)
    clear_challenge_cookie(response)
    return response


@router.post("/disable")
def disable(body: DisableIn, request: Request, response: Response, user=Depends(require_user), path=Depends(db_path)):
    """Password AND a current code or a recovery code. Every session ends; this browser gets a fresh one. Refused for administrators."""
    token = _guard(mfa.disable, path, user, password=body.password, code=body.code, recovery_code=body.recovery_code,
                   current_token=request.cookies.get(settings.COOKIE_NAME), client=_client(request))
    _set_cookie(response, token)
    return {"ok": True}


@router.post("/recovery-codes")
def regenerate(body: RegenerateIn, request: Request, user=Depends(require_user), path=Depends(db_path)):
    """Password AND a current code. The old recovery codes stop working; the new ones are returned ONCE."""
    return {"recovery_codes": _guard(mfa.regenerate_recovery_codes, path, user, password=body.password, code=body.code, client=_client(request))}
