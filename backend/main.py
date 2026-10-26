"""LingoBuddy — FastAPI backend.

Serves the SPA, persists learner state in SQLite and proxies an optional LLM.
With no LLM configured, /api/ai returns ok=false and the frontend uses its
built-in contextual engine, so the demo always works offline.
"""
import asyncio
import json
import logging
import os
import re
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import settings
from .auth.deps import authorize_state_access, db_path, optional_user, require_user_or_demo
from .db.migrate import migrate
from .legacy import ai as legacy_ai, state as legacy_rules
from .repositories import catalog, legacy_state
from .security import csrf
from .security import headers as security_headers
from .routers import auth as auth_router
from .speaking import service as speaking_service
from .routers import learner as learner_router
from .routers import curriculum as curriculum_router
from .routers import situations as situations_router
from .routers import personalization as personalization_router
from .routers import listening as listening_router
from .routers import speaking as speaking_router
from .routers import pronunciation as pronunciation_router
from .routers import agemode as agemode_router
from .routers import parent as parent_router
from .routers import gamification as gamification_router
from .routers import ai as ai_router
from .routers import adaptive as adaptive_router
from .routers import admin as admin_router
from .routers import two_factor as two_factor_router

log = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "buddy.db"))

# Minimal .env loader (keeps keys out of code, no extra dependency).
if (ROOT / ".env").exists():
    for line in (ROOT / ".env").read_text().splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"'))

GROQ_KEY = os.getenv("GROQ_API_KEY")
ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OLLAMA_URL = os.getenv("OLLAMA_URL")  # e.g. http://localhost:11434
LLM_MODEL = os.getenv("LLM_MODEL")


@asynccontextmanager
async def lifespan(_app):
    migrate(DB_PATH)  # ordered, idempotent; existing data is never dropped
    try:
        speaking_service.sweep_expired(DB_PATH)  # delete voice recordings that have outlived their purpose
    except Exception:  # housekeeping must never stop the app from starting
        pass
    _app.state.db_path = DB_PATH  # read by the db_path dependency
    yield


app = FastAPI(title="LingoBuddy", lifespan=lifespan)
app.include_router(auth_router.router)
app.include_router(two_factor_router.router)
app.include_router(learner_router.router)
app.include_router(curriculum_router.router)
app.include_router(situations_router.router)
app.include_router(personalization_router.router)
app.include_router(listening_router.router)
app.include_router(speaking_router.router)
app.include_router(pronunciation_router.router)
app.include_router(agemode_router.router)
app.include_router(parent_router.router)
app.include_router(gamification_router.router)
app.include_router(ai_router.router)
app.include_router(adaptive_router.router)
app.include_router(admin_router.router)


@app.middleware("http")
async def browser_security(request, call_next):
    """Runs on every request before any route: the global CSRF guard (backend/security/csrf.py), then the security headers on whatever
    response comes back, the guard's own refusals and every 4xx included (backend/security/headers.py)."""
    scheme, path = request.url.scheme, request.url.path
    refused = csrf.rejection(request.method, path, request.headers, scheme)
    response = JSONResponse(status_code=403, content={"detail": refused}) if refused else await call_next(request)
    security_headers.apply(response.headers, path, scheme)
    return response


@app.exception_handler(RequestValidationError)
async def validation_error(_request, exc):
    # FastAPI's default 422 echoes the rejected input, which would send a submitted password back in the response.
    return JSONResponse(status_code=422, content={"detail": [{"loc": e["loc"], "msg": e["msg"], "type": e["type"]} for e in exc.errors()]})


@app.exception_handler(OverflowError)
async def number_out_of_range(_request, exc):
    """A whole number beyond SQLite's 64-bit range (a path id, query parameter or body field) can name nothing: 422, not a 500 (Phase 14F).
    Any other OverflowError is a server bug and stays a 500."""
    if "SQLite INTEGER" not in str(exc):
        raise exc
    return JSONResponse(status_code=422, content={"detail": [{"loc": ["request"], "msg": "A number is out of range", "type": "value_error"}]})


def provider():
    if GROQ_KEY:
        return "groq"
    if ANTHROPIC_KEY:
        return "anthropic"
    if OPENAI_KEY:
        return "openai"
    if OLLAMA_URL:
        return "ollama"
    return None


@app.get("/api/health")
def health():
    """Public: coarse statuses only (Phase 14E). `ai` says whether a language model is configured, not which one."""
    return {"ok": True, "ai": provider() is not None}


@app.get("/api/state/{user_id}")
def get_state(user_id: str, user=Depends(optional_user), path=Depends(db_path)):
    authorize_state_access(user, user_id)
    return {"state": legacy_state.get_state(path, user_id)}


async def _read_limited(request: Request, limit: int) -> bytes:
    """The raw body, refused with 413 as soon as it is larger than `limit` (declared or actual); never buffered past the limit."""
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > limit:
        raise HTTPException(status_code=413, detail="The state is too large.")
    chunks, total = [], 0
    async for chunk in request.stream():
        total += len(chunk)
        if total > limit:
            raise HTTPException(status_code=413, detail="The state is too large.")
        chunks.append(chunk)
    return b"".join(chunks)


@app.put("/api/state/{user_id}")
async def put_state(user_id: str, request: Request, user=Depends(optional_user), path=Depends(db_path)):
    authorize_state_access(user, user_id)  # before reading the body
    raw = await _read_limited(request, settings.LEGACY_STATE_MAX_BYTES)
    try:
        data = legacy_rules.parse(raw, {lvl["code"] for lvl in catalog.list_cefr_levels(path)},
                                  {c["slug"]: c["languages"] for c in catalog.list_cities(path)})
    except legacy_rules.InvalidState as exc:
        raise HTTPException(status_code=422, detail=[{"loc": ["body", exc.field], "msg": exc.message, "type": "value_error"}])
    legacy_state.put_state(path, user_id, data)
    return {"ok": True}


@app.get("/api/languages")
def languages(path=Depends(db_path)):
    return {"languages": catalog.list_languages(path)}


@app.get("/api/cities")
def cities(path=Depends(db_path)):
    return {"cities": catalog.list_cities(path)}


SYSTEM = """You are a friendly local-language buddy helping a newcomer in {city} learn {language} for real-life situations.
Learner level: {level} (beginner). Keep language simple, culturally natural and never stereotyped.
{mode_text}
Respond ONLY with a single JSON object, no markdown."""

ROLEPLAY = """ROLEPLAY: You ARE {partner}, a {role} at {place}. Learner's goal: {goal}.
Speak exactly like a real {city} {role}: 1-2 short sentences of natural romanised {style}. React to what the learner just said
and keep the scene moving toward their goal. Never break character, never lecture, never suggest a different activity.
JSON schema: {{"reply": str, "translation": str (English meaning of reply), "tip": str (one short friendly coaching note on the
learner's last message, e.g. a more natural {style} way to say it; "" if it was already good), "suggestions": [3 short {style} replies the learner could say next]}}"""
ROLEPLAY_STYLE = {"Hindi": "Hinglish", "Hindi (Hinglish)": "Hinglish", "Marathi": "Marathi", "Kannada": "Kannada", "Tamil": "Tamil", "French": "French", "Bengali": "Bengali", "Telugu": "Telugu", "Urdu": "Urdu", "Kashmiri": "Kashmiri", "Dogri": "Dogri"}   # the language the character speaks
SCRIPT_NAME = {"Kannada": "Kannada script", "Tamil": "Tamil script", "Bengali": "Bengali script", "Telugu": "Telugu script", "Urdu": "Urdu script (right to left)", "Kashmiri": "Kashmiri Perso-Arabic script (right to left)", "French": "the same French text, with its accents"}                     # the script of the tutor's "hi" field; Devanagari for Hindi and Marathi

TUTOR = """TUTOR: Answer the learner's question with the exact phrases a local would use.
JSON schema: {{"intro": str (one short sentence, e.g. "Try:"), "phrases": [1-3 items of {{"roman": str (romanised Hinglish),
"hi": str (Devanagari), "en": str (English meaning), "label": str ("" or e.g. "More polite")}}], "note": str (one short cultural tip or ""),
"suggestions": [2 short follow-up questions the learner might ask next, in English]}}
If the learner asks about something unrelated to language or life in the city, gently steer back."""


async def call_llm(system: str, messages: list[dict]) -> str:
    async with httpx.AsyncClient(timeout=15) as client:
        p = provider()
        if p == "anthropic":
            r = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": ANTHROPIC_KEY, "anthropic-version": "2023-06-01"},
                json={"model": LLM_MODEL or "claude-sonnet-5-5", "max_tokens": 400, "system": system, "messages": messages},
            )
            r.raise_for_status()
            return "".join(b.get("text", "") for b in r.json()["content"])
        payload = {"messages": [{"role": "system", "content": system}, *messages], "max_tokens": 400}
        if p == "groq":
            base, key = "https://api.groq.com/openai/v1", GROQ_KEY
            payload |= {"model": LLM_MODEL or "openai/gpt-oss-120b", "reasoning_effort": "low",
                        "response_format": {"type": "json_object"}, "max_tokens": 1200}
        elif p == "ollama":
            base, key = f"{OLLAMA_URL.rstrip('/')}/v1", None
            payload["model"] = LLM_MODEL or "llama3.1"
        else:
            base, key = OPENAI_BASE, OPENAI_KEY
            payload["model"] = LLM_MODEL or "gpt-4o-mini"
        r = await client.post(f"{base}/chat/completions", headers={"Authorization": f"Bearer {key}"} if key else {}, json=payload)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]


def _field_error(field, message):
    return HTTPException(status_code=422, detail=[{"loc": ["body", field], "msg": message, "type": "value_error"}])


@app.post("/api/ai")
async def ai(body: legacy_ai.LegacyAiIn, request: Request, user=Depends(require_user_or_demo), path=Depends(db_path)):
    """The legacy prototype's AI. Returns {ok: true, reply, translation, tip, suggestions} or {ok: false, reason} → the client falls back to
    its built-in engine. Who may reach the real model, and with what, is decided in backend/legacy/ai.py."""
    retry = legacy_ai.hit(legacy_ai.caller_key(user, request.client.host if request.client else None))
    if retry is not None:
        raise HTTPException(status_code=429, detail="Too many requests. Try again later.", headers={"Retry-After": str(retry)})
    cities = {c["name"]: c for c in catalog.list_cities(path)}
    if body.city not in cities:
        raise _field_error("city", "Unknown city")
    code = legacy_ai.CITY_LANGUAGE_CODES.get(body.language)       # Marathi only in Mumbai, Kannada in Bengaluru, Tamil in Chennai and Puducherry, French in Puducherry, Bengali in Kolkata, Telugu and Urdu in Hyderabad, Kashmiri, Dogri and Urdu in Jammu & Kashmir
    if code and code not in cities[body.city]["languages"]:
        raise _field_error("language", f"This city is not offered in {body.language}")
    if body.level not in {lvl["code"] for lvl in catalog.list_cefr_levels(path)}:
        raise _field_error("level", "Unknown CEFR level")
    if not provider() or not legacy_ai.live_allowed(path, user):
        return {"ok": False, "reason": "offline"}
    style = ROLEPLAY_STYLE[body.language]                       # the language the character or tutor answers in (Hinglish unless Marathi or Kannada)
    mode_text = (ROLEPLAY.format(city=body.city, style=style, **legacy_ai.SCENARIOS[body.scenario]) if body.mode == "roleplay"   # city: checked above
                 else TUTOR.replace("romanised Hinglish", f"romanised {style}").replace("(Devanagari)", f"({SCRIPT_NAME.get(body.language, 'Devanagari')})"))
    mode_text = mode_text.replace("romanised French", "French")              # French is written in Roman letters already
    system = SYSTEM.format(city=body.city, language=body.language, level=body.level, mode_text=mode_text)
    msgs = [{"role": "assistant" if m.role == "ai" else "user", "content": m.text} for m in body.history]
    while msgs and msgs[0]["role"] == "assistant":
        msgs.pop(0)
    if not msgs:
        return {"ok": False}
    try:
        text = await asyncio.wait_for(call_llm(system, msgs), timeout=settings.ai_timeout_seconds())
        match = re.search(r"\{.*\}", text, re.S)
        data = json.loads(match.group(0)) if match else {"reply": text.strip()}
        phrases = [p for p in data.get("phrases", []) if isinstance(p, dict) and p.get("roman")][:3]
        reply = data.get("reply") or data.get("intro") or ""
        if not reply and not phrases:
            return {"ok": False}
        return {"ok": True, "reply": reply, "translation": data.get("translation", ""), "tip": data.get("tip", ""),
                "phrases": phrases, "note": data.get("note", ""), "suggestions": data.get("suggestions", [])[:3]}
    except Exception as exc:  # never surface AI errors to the learner: no exception name, message or provider detail leaves the server
        log.warning("legacy /api/ai provider call failed (%s)", type(exc).__name__)
        return {"ok": False, "reason": "unavailable"}


@app.get("/sw.js", include_in_schema=False)
def service_worker():
    """A clean-up worker: the app no longer installs, so this only removes the worker (and its cache) that browsers registered before.
    no-cache: browsers that still have the old worker pick this one up on their next visit."""
    return FileResponse(FRONTEND / "sw.js", media_type="text/javascript", headers={"Cache-Control": "no-cache"})


app.mount("/static", StaticFiles(directory=FRONTEND), name="static")


@app.get("/")
def index():
    # no-cache: the browser always checks with the server before using its copy of the page, so a new release is picked up.
    return FileResponse(FRONTEND / "index.html", headers={"Cache-Control": "no-cache"})
