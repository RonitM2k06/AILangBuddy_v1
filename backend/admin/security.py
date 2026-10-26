"""Who may call /api/admin/*, and how a state-changing call must look. The server is the only authority: the frontend guard is a convenience.

  * admin_only: the one authorization dependency for every admin route (401 without a session, 403 for any role but admin, including the
    demo learner and parents). Admins get no access to learner or parent data through it: those routes keep their own learner/parent guards.
  * csrf_guard: every state-changing request must carry Content-Type: application/json and X-Requested-With: XMLHttpRequest. A browser
    cannot send either cross-site without a CORS preflight (this app grants none), so a forged form post or <img> request is refused
    even if the SameSite=Lax session cookie came along. Since Phase 14B the global guard (backend/security/csrf.py) applies the same rule,
    plus Origin checks, to every route before routing; this dependency stays on the admin router as a second layer.
  * request_id: a server-made id stored with each audit event; never taken from the client."""
import uuid

from fastapi import Depends, HTTPException, Request

from ..auth import events
from ..auth.deps import require_roles

SAFE_METHODS = ("GET", "HEAD", "OPTIONS")
CSRF_HEADER, CSRF_VALUE = "x-requested-with", "XMLHttpRequest"

_admin_role = require_roles("admin")


def admin_only(request: Request, user=Depends(_admin_role)):
    """The admin role AND a session created after a verified second factor (mfa_level >= 1, Phase 14D). The level is the session row's,
    read by authenticate(); nothing in the request can raise it. An admin signed in with a password only gets 403 mfa_required until
    they turn on 2FA (which replaces this session with an MFA one) or sign in again with their code."""
    if user.mfa_level < 1:
        events.record_admin_denial(request.app.state.db_path, user.id, request.client.host if request.client else None)
        raise HTTPException(status_code=403, detail={"code": "mfa_required",
                                                      "message": "Two-factor authentication is required for the admin console. Turn it on, or sign in again with your code."})
    return user


def csrf_guard(request: Request):
    if request.method in SAFE_METHODS:
        return
    content_type = request.headers.get("content-type", "").split(";")[0].strip().lower()
    if content_type != "application/json" or request.headers.get(CSRF_HEADER) != CSRF_VALUE:
        raise HTTPException(status_code=403, detail="CSRF check failed: send Content-Type: application/json and X-Requested-With: XMLHttpRequest")


def request_id(request: Request):
    rid = uuid.uuid4().hex
    request.state.request_id = rid
    return rid
