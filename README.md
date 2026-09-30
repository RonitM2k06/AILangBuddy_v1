# 🌍 LingoBuddy

> Traditional language apps teach you a language. LingoBuddy teaches you how to **live in a new place**.

## Run
```bash
./run.sh            # creates .venv, installs fastapi/uvicorn/httpx, serves on :8000
open http://localhost:8000
```

## Optional AI (works fully offline without it)
| Variable | Effect |
|---|---|
| `GROQ_API_KEY` | Groq (`openai/gpt-oss-120b`) for tutor + roleplay (read from `.env`) |
| `ANTHROPIC_API_KEY` | Claude for tutor + roleplay |
| `OPENAI_API_KEY` (+ `OPENAI_BASE_URL`) | Any OpenAI-compatible API |
| `OLLAMA_URL` (e.g. `http://localhost:11434`) | Local Ollama |
| `LLM_MODEL` | Override model name |

With no key, a contextual scripted engine drives the tutor and roleplays, so there are no error states.

## Structure
- `backend/main.py`: FastAPI app. Serves the SPA, stores state in SQLite (`/api/state`), proxies the optional LLM (`/api/ai`)
- `frontend/content.js`: languages, cities, Delhi 7-day pack, roleplay scenarios, tutor intents, readings, placement test
- `frontend/engine.js`: state/persistence, weighted confidence, TTS/speech recognition, pronunciation scoring, offline AI, SM-2-lite flashcards
- `frontend/app.js`: hash-routed views
- `frontend/bits.js`: vanilla ports of React Bits components (BlurText, GradientText, ShinyText, RotatingText, CountUp, DecryptedText, TextType, SpotlightCard, TiltedCard, Magnet, StarBorder, ClickSpark, AnimatedContent, Aurora, LogoLoop)

## 2-minute demo
Home → **I'm New Here** → Delhi → Hindi/Hinglish → **Build My Survival Pack** → Day 2 Transport → 🔊 Listen / 🎤 Practice → **Practice Conversation** → Confidence (78%) → **Practice Now** (Small Talk with Priya).
Use **Progress → Reset demo data** to reset between runs.
