"""LingoBuddy — FastAPI backend.

Serves the SPA, persists learner state in SQLite and proxies an optional LLM.
With no LLM configured, /api/ai returns ok=false and the frontend uses its
built-in contextual engine, so the demo always works offline.
"""
import json
import os
import re
import sqlite3
from pathlib import Path

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

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

app = FastAPI(title="LingoBuddy")


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("CREATE TABLE IF NOT EXISTS state (user_id TEXT PRIMARY KEY, data TEXT NOT NULL, updated TEXT DEFAULT CURRENT_TIMESTAMP)")
    return conn


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
    return {"ok": True, "ai": provider()}


@app.get("/api/state/{user_id}")
def get_state(user_id: str):
    with db() as conn:
        row = conn.execute("SELECT data FROM state WHERE user_id=?", (user_id,)).fetchone()
    return {"state": json.loads(row[0]) if row else None}


@app.put("/api/state/{user_id}")
async def put_state(user_id: str, request: Request):
    data = await request.json()
    with db() as conn:
        conn.execute(
            "INSERT INTO state(user_id, data) VALUES(?, ?) ON CONFLICT(user_id) DO UPDATE SET data=excluded.data, updated=CURRENT_TIMESTAMP",
            (user_id, json.dumps(data)),
        )
    return {"ok": True}


SYSTEM = """You are a friendly local-language buddy helping a newcomer in {city} learn {language} for real-life situations.
Learner level: {level} (beginner). Keep language simple, culturally natural and never stereotyped.
{mode_text}
Respond ONLY with a single JSON object, no markdown."""

ROLEPLAY = """ROLEPLAY: You ARE {partner}, a {role} at {place}. Learner's goal: {goal}.
Speak exactly like a real Delhi {role}: 1-2 short sentences of natural romanised Hinglish. React to what the learner just said
and keep the scene moving toward their goal. Never break character, never lecture, never suggest a different activity.
JSON schema: {{"reply": str, "translation": str (English meaning of reply), "tip": str (one short friendly coaching note on the
learner's last message, e.g. a more natural Hinglish way to say it; "" if it was already good), "suggestions": [3 short Hinglish replies the learner could say next]}}"""

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
                json={"model": LLM_MODEL or "claude-sonnet-5", "max_tokens": 400, "system": system, "messages": messages},
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


@app.post("/api/ai")
async def ai(request: Request):
    """Returns {ok: true, reply, translation, tip, suggestions} or {ok: false} → client falls back."""
    if not provider():
        return {"ok": False, "reason": "offline"}
    body = await request.json()
    sc = body.get("scenario") or {}
    mode_text = ROLEPLAY.format(**{k: sc.get(k, "") for k in ("partner", "role", "place", "goal")}) if body.get("mode") == "roleplay" else TUTOR
    system = SYSTEM.format(city=body.get("city", "Delhi"), language=body.get("language", "Hindi"),
                           level=body.get("level", "A1"), mode_text=mode_text)
    msgs = [{"role": "assistant" if m["role"] == "ai" else "user", "content": m["text"]} for m in body.get("history", [])][-12:]
    while msgs and msgs[0]["role"] == "assistant":
        msgs.pop(0)
    if not msgs:
        return {"ok": False}
    try:
        text = await call_llm(system, msgs)
        match = re.search(r"\{.*\}", text, re.S)
        data = json.loads(match.group(0)) if match else {"reply": text.strip()}
        phrases = [p for p in data.get("phrases", []) if isinstance(p, dict) and p.get("roman")][:3]
        reply = data.get("reply") or data.get("intro") or ""
        if not reply and not phrases:
            return {"ok": False}
        return {"ok": True, "reply": reply, "translation": data.get("translation", ""), "tip": data.get("tip", ""),
                "phrases": phrases, "note": data.get("note", ""), "suggestions": data.get("suggestions", [])[:3]}
    except Exception as exc:  # never surface AI errors to the learner
        return JSONResponse({"ok": False, "reason": type(exc).__name__})


app.mount("/static", StaticFiles(directory=FRONTEND), name="static")


@app.get("/")
def index():
    return FileResponse(FRONTEND / "index.html")
