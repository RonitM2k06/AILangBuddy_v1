# 🌍 LingoBuddy

> Traditional language apps teach you a language. LingoBuddy teaches you how to **live in a new place**.

## Run
```bash
./run.sh            # creates .venv, installs requirements.txt (fastapi, uvicorn, httpx, cryptography), serves on 127.0.0.1:8000
open http://localhost:8000
HOST=0.0.0.0 ./run.sh   # only if you deliberately want LAN access (API is unauthenticated)
```

**Installable app:** served over HTTPS (or on `localhost`), LingoBuddy can be installed (📲 Install app in Chromium browsers; Share → Add to Home Screen on iPhone). Its service worker caches only the app's static files, never your data, and shows an offline page with emergency phrases when the server can't be reached. Learning still needs a connection; see `docs/ARCHITECTURE.md` section 29. After changing an icon SVG run `.venv/bin/python tools/make_icons.py`.

Tests: `.venv/bin/pip install -r requirements-dev.txt && .venv/bin/pytest`. The mobile layout tests (`tests/test_mobile_layout.py`) drive a headless Google Chrome if one is installed (they are skipped otherwise); it can only reach 127.0.0.1. Database migrations run automatically on startup; see `docs/ARCHITECTURE.md`. Create an admin with `.venv/bin/python -m backend.manage create-admin --email you@example.com`.

## Optional AI (works fully offline without it)
| Variable | Effect |
|---|---|
| `GROQ_API_KEY` | Groq (`openai/gpt-oss-120b`) for tutor + roleplay (read from `.env`) |
| `ANTHROPIC_API_KEY` | Claude for tutor + roleplay |
| `OPENAI_API_KEY` (+ `OPENAI_BASE_URL`) | Any OpenAI-compatible API |
| `OLLAMA_URL` (e.g. `http://localhost:11434`) | Local Ollama |
| `LLM_MODEL` | Override model name |
| `DEMO_MODE` | Default `1`: the legacy `/api/ai` endpoint also answers callers who are not signed in (offline unless `DEMO_LIVE_AI`). `0` requires login for it. Either way the web app shows only its sign-in screen (and the 🆘 help) until you sign in |
| `DEMO_LIVE_AI` | Default `0`. `1` lets anonymous visitors' legacy `/api/ai` requests reach the configured LLM. Children never do |
| `COOKIE_SECURE` | Set `1` when served over HTTPS (also turns on HSTS and accepts `https://<Host>` as the site's own origin) |
| `SESSION_IDLE_MINUTES` | Default `30`: a session unused this long ends (sessions also end 7 days after sign-in, however active) |
| `REGISTER_IP_MAX`, `LOGIN_IP_MAX_FAILURES`, `LOGIN_ACCOUNT_MAX_FAILURES`, `PASSWORD_CHANGE_MAX_FAILURES` | Override the authentication throttles (defaults 30/h, 20/15 min, 5/15 min, 5/15 min), e.g. a higher `REGISTER_IP_MAX` for a classroom behind one address |
| `TOTP_ENC_KEY` | 32 random bytes, base64url (`python -c "import secrets,base64;print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())"`). Encrypts TOTP 2FA secrets; without it 2FA cannot be set up or checked (recovery codes still work). Admins must use 2FA, so set it before creating admins. Back it up: losing it disables every authenticator |
| `TRUSTED_ORIGINS` | Comma-separated origins writes may come from, e.g. `https://lingo.example`. Unset: the request's own scheme and Host. Set it behind a proxy that rewrites Host |
| `STT_PROVIDER` | Speech-to-text for Voice Practice: unset/`none` (record only), `mock` (development), or `groq` (Whisper via Groq; needs `GROQ_API_KEY`; sends recordings to Groq) |
| `PRONUNCIATION_PROVIDER` | Pronunciation assessment: unset/`none` (the word check works, pronunciation reports "not available") or `mock` (a deterministic test provider; its scores are labelled test scores, not measurements). No real provider is included |
| `RECORDINGS_DIR` | Where voice recordings are stored (default `~/.lingobuddy/recordings`, outside the repo). Deleted after transcription unless `SPEAKING_KEEP_AUDIO=1` |

With no key, a contextual scripted engine drives the tutor and roleplays, so there are no error states.

## Structure
- `backend/main.py`: FastAPI app. Serves the SPA, stores each signed-in user's own state in SQLite (`/api/state`), proxies the optional LLM (`/api/ai`; rules in `backend/legacy/`)
- `frontend/content.js`: languages, cities, Delhi 7-day pack, roleplay scenarios, tutor intents, readings, placement test
- `frontend/engine.js`: state/persistence, weighted confidence, TTS/speech recognition, pronunciation scoring, offline AI, SM-2-lite flashcards
- `frontend/app.js`: hash-routed views
- `frontend/bits.js`: vanilla ports of React Bits components (BlurText, GradientText, ShinyText, RotatingText, CountUp, DecryptedText, TextType, SpotlightCard, TiltedCard, Magnet, StarBorder, ClickSpark, AnimatedContent, Aurora, LogoLoop)

## 2-minute demo
Home → **I'm New Here** → Delhi → Hindi/Hinglish → **Build My Survival Pack** → Day 2 Transport → 🔊 Listen / 🎤 Practice → **Practice Conversation** → Confidence (78%) → **Practice Now** (Small Talk with Priya).
Use **Progress → Reset demo data** to reset between runs.
