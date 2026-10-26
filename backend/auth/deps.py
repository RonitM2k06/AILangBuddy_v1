"""FastAPI dependencies: who is calling, and are they allowed. Identity comes only from the
server-side session behind the cookie; nothing about the caller is taken from request bodies."""
from fastapi import Depends, HTTPException, Request

from .. import settings
from . import service


def db_path(request: Request):
    return request.app.state.db_path


def optional_user(request: Request, path=Depends(db_path)):
    return service.authenticate(path, request.cookies.get(settings.COOKIE_NAME))


def require_user(user=Depends(optional_user)):
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


def require_roles(*roles):
    def dependency(user=Depends(require_user)):
        if not user.has_any_role(*roles):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user

    return dependency


def authorize_state_access(user, handle):
    """Legacy state is keyed by user handle. A signed-in user may touch only their own; there is no shared state (the demo learner's included,
    in any mode), and anonymous visitors keep theirs in the browser. Admins get no special access."""
    if user is not None and user.handle == handle:
        return
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    raise HTTPException(status_code=403, detail="Forbidden")


def require_user_or_demo(user=Depends(optional_user)):
    """For endpoints the prototype used anonymously (the AI proxy): open in demo mode, otherwise login."""
    if user is None and not settings.demo_mode():
        raise HTTPException(status_code=401, detail="Authentication required")
    return user
