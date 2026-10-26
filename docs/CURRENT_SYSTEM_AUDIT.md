# LingoBuddy — Current System Audit

Audit of commit `cec0252` ("Initial commit: LingoBuddy v1"), the TCS hackathon prototype. Nothing in the application was modified during this audit.

## 1. Tech stack

| Layer | Actual |
|---|---|
| Frontend | Vanilla JS single-page app, **no framework, no bundler, no npm**. Hash router. Plain `<script>` tags. Google Fonts CDN. |
| Backend | Python 3.13, FastAPI 0.141 + Uvicorn 0.54, httpx 0.28 (`requirements.txt` is unpinned) |
| Database | SQLite file `buddy.db` (gitignored), accessed with raw `sqlite3` |
| ORM / migrations | **None.** Table is created inline by `CREATE TABLE IF NOT EXISTS` on every connection |
| Auth | **None** |
| AI | Optional LLM proxy: Groq (default here, `openai/gpt-oss-120b`), Anthropic, OpenAI-compatible, Ollama. Offline scripted fallback in the browser |
| Speech | Browser Web Speech API (TTS `speechSynthesis`, STT `SpeechRecognition`) |
| Tests / CI | **None** |
| Docs | `README.md` only (accurate and short) |

## 2. Repository structure

```
backend/main.py      159 lines. FastAPI: static hosting, /api/health, /api/state/{id}, /api/ai
frontend/index.html   shell: sidebar, #app, bottom nav, toast
frontend/app.js       730 lines. All views + router + widgets (price check, SOS panel)
frontend/engine.js    241 lines. State/persistence, TTS/STT, pronunciation scoring, offline AI, SM-2 flashcards
frontend/content.js   324 lines. ALL content: languages, cities, Delhi pack, scenarios, tutor intents, readings, placement test
frontend/bits.js      150 lines. Vanilla ports of React Bits animation effects
frontend/styles.css   416 lines
deck/                 pitch deck (pptx, build script, screenshots). Not part of the app
run.sh                creates .venv, pip installs, starts uvicorn on :8000 (binds 0.0.0.0)
.env                  (untracked) contains GROQ_API_KEY
```

## 3. Application flow

1. `GET /` serves `index.html`, which loads `content.js`, `engine.js`, `bits.js`, `app.js` from `/static/` (cache-buster `?v=` is a hardcoded number).
2. `engine.js` loads state from `localStorage["llb-state-v1"]` (falling back to the hardcoded `DEMO()` learner "Alex"). Every `save()` also debounces a `PUT /api/state/demo-alex` (400 ms).
3. `hydrate()`: if localStorage exists it wins and overwrites the server copy. The server copy is only read when localStorage is empty.
4. Views render via template-string `innerHTML` and inline `onclick="A.xxx()"` handlers.
5. AI calls go browser → `POST /api/ai` → provider. Any failure returns `{ok:false}` and the client uses the scripted engine.

## 4. Routes (frontend, hash-based)

`#/` landing · `#/new` onboarding (city → language) · `#/pack` First Week · `#/lesson/:day` · `#/roleplay/:scenario` · `#/confidence` · `#/tutor` · `#/speaking` · `#/learn` (flashcards / reading / listening / level test tabs) · `#/progress`.
Unknown routes fall back to the landing page. Global widgets: 🆘 Help-me-now panel, 📱 "show to a local" overlay, 💰 fair-price check.

## 5. Backend APIs

| Endpoint | Behaviour | Issues |
|---|---|---|
| `GET /api/health` | `{ok, ai: provider}` | fine |
| `GET /api/state/{user_id}` | returns the JSON blob | unauthenticated; any id readable |
| `PUT /api/state/{user_id}` | upserts the JSON blob | unauthenticated; no size limit or schema validation; any id writable |
| `POST /api/ai` | builds prompt from `mode` (tutor/roleplay), calls LLM, parses JSON | unauthenticated and unrate-limited, so anyone reaching the server can spend the API key; prompt `.format()` on client-supplied values (prompt injection surface) |
| `GET /`, `/static/*` | SPA + assets | fine |

## 6. Database / persistence

Single table, created inline:

```sql
state(user_id TEXT PRIMARY KEY, data TEXT NOT NULL, updated TEXT DEFAULT CURRENT_TIMESTAMP)
```

- Holds 1 row for `demo-alex`, containing the entire learner state as one JSON blob: `{name, city, language, level, confidence{7 cats}, completedDays[], practiced, xp, streak, lastActive, skills{4}, srs{cardId:{ease,interval,reps,due}}, placement, tutor[] (chat history), roleplays, achievements[]}`.
- No FKs, indexes, constraints, or migrations. Not 1NF (the blob is a nested, repeating-group document), so it is not queryable or analysable in SQL.
- The `user_id` is a hardcoded constant (`"demo-alex"`). There is no concept of a user.
- Connections are opened per request and **never closed** (`with sqlite3.connect` commits but does not close).

## 7. AI integrations

- `call_llm` supports Groq / Anthropic / OpenAI-compatible / Ollama, selected by which env var is set (precedence: Groq > Anthropic > OpenAI > Ollama).
- Two prompt modes: *roleplay* (persona from the scenario) and *tutor* (phrase cards). Both are **hardcoded to Delhi + Hinglish** in the prompt text.
- Anthropic default model string `claude-sonnet-5` is not a valid model ID (the current ID is `claude-sonnet-5-5`). Only reachable if `ANTHROPIC_API_KEY` is set and Groq is not.
- `max_tokens` is 400 (Groq path overrides to 1200). Timeout 15 s.
- Client-side: `Engine.tutorReply` (intent matching over `TUTOR_INTENTS`) and `Engine.roleplayReply` (keyword rules per scenario) are the offline engines. The LLM is only consulted in the tutor when the local engine returns `generic`.

## 8. Environment variables

`GROQ_API_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OLLAMA_URL`, `LLM_MODEL`, `DB_PATH` (undocumented in README), `PORT` (run.sh). Loaded by a hand-rolled `.env` parser; `.env` is gitignored (verified not in `git ls-files`).

## 9. Implemented features

Working (verified by running the server and exercising the API; see section 13):
- Onboarding: city → language (Delhi ready; Mumbai/Bengaluru/Hyderabad/Chennai shown as "not ready")
- 7-day Delhi survival pack, each day with situation, cultural tip and 5 phrases (Devanagari + romanised + English + natural)
- Day completion → confidence bump, XP, confetti
- AI roleplay with 7 scenarios (live LLM or offline rules), per-message coaching tip, suggested replies, end-of-chat summary
- AI tutor with offline intent engine, glossary lookups and optional LLM
- Local Confidence score: 7 weighted categories, overall %, readiness label, weakest-area insight, "Practice now" link
- Speaking practice: TTS playback (normal/slow), STT capture, Levenshtein-based per-word pronunciation score (with a deterministic *estimated* score if STT is unavailable)
- Learn: SM-2-lite flashcards, reading comprehension, listening quiz, 6-question placement test (sets A1/A2 only)
- Progress: XP, streak, level, achievements
- Fair-price check, Help-me-now SOS panel with 112 link, "show to a local" overlay, responsive layout with mobile bottom nav
- Offline-first: full demo works with no API key

Partial / stubbed:
- Language list holds 11 languages but only Hindi/Hinglish/English content exists. `LANGUAGES` has no effect beyond the onboarding picker and TTS locale.
- Cities: only Delhi has content.
- Levels: only A1/A2 are ever produced. The CEFR chips A1–C2 are cosmetic.
- Streak and `lastActive` are stored but **never updated** by any logic (streak stays at the demo value 4). Achievements other than `first-chat` and `local` are pre-seeded demo values.
- Skills (speaking/listening/pronunciation) are seeded constants; only `vocabulary` changes.

## 10. Mock / hardcoded data (to be DB-backed later)

| Where | What |
|---|---|
| `engine.js` `DEMO()` | The fake learner (Alex, XP 340, streak 4, confidences, completed days 1–3, achievements) |
| `engine.js` `USER = "demo-alex"` | The only user id |
| `content.js` | `LANGUAGES`, `CITIES`, `CATEGORIES` (+weights), `PACKS`, `SCENARIOS`, `TUTOR_INTENTS`, `GLOSSARY`, `READINGS`, `PLACEMENT`, `PLACE_HI` |
| `app.js` | `PRICES` (fair-price data), `SOS` phrases, `ACH` achievement definitions, `NAV`, tutor starter prompts, time-of-day "Right now" slots |
| `engine.js` | `PLACES`, `PRAISE`, regex word lists for English/Hindi detection |
| `backend/main.py` | Persona/city/language prompt templates |

## 11. Authentication

None. No login, sessions, roles or password handling. The state endpoints trust a client-supplied id. Consequence: there is no per-user data isolation and the LLM endpoint is open.

## 12. Reusable components and logic

Reusable as is or with light extraction:
- **`Engine.score` + `lev`** pronunciation scoring: language-agnostic except the Devanagari regex.
- **SM-2-lite `review`/`dueCards`**: swap storage for a table later.
- **`speak`/`listen`** wrappers: parameterise locale (already mostly a `lang` arg).
- **Weighted confidence `overall()`**: sound idea; the maths can move to SQL/service.
- **LLM proxy `call_llm`** provider abstraction and JSON-extraction/fallback contract (`ok:false` → client falls back).
- **Scenario schema** (`partner, role, place, goal, start, rules, fallback`): a good shape for a `situations`/`situation_steps` table.
- **UI helpers** (`bar`, `ring`, `esc`, toast, confetti, `bits.js` effects) and `styles.css` design system.

## 13. Build / run status (verified)

- Start: `./run.sh` (or `.venv/bin/uvicorn backend.main:app --port 8000`). Dependencies were already installed in `.venv`.
- Server started cleanly on a spare port with `DB_PATH` pointed to a scratch file. `/api/health` → `{"ok":true,"ai":"groq"}`; `/`, `app.js`, `engine.js`, `content.js`, `bits.js`, `styles.css` all 200; `/api/state/demo-alex` → `{"state":null}` on a fresh DB; `POST /api/ai` returned a valid live Groq tutor response.
- **Not verified:** browser rendering and Web Speech features (no browser driven; `node` is not installed so JS syntax checks were not run). Treat the UI as "last known working from the hackathon".
- There is no build step and no test suite.

## 14. Technical debt

1. **No users, no auth, no authorization** on any API (see section 5).
2. **State is one JSON blob**, so no relational model, no analytics, and read-modify-write races from two tabs or devices (last write wins).
3. **localStorage is authoritative over the server** (`hydrate`), so the DB is effectively a write-only backup.
4. **`content.js` is the source of truth for all content.** Adding a language or lesson requires a code change, which contradicts the goal of adding languages through the database.
5. **Language coupling:** Hindi/Devanagari checks in `engine.js` (`/[ऀ-ॿ]/`, `hi-IN`, `phrase.hi` field naming) and in the LLM prompts (`"Delhi Hinglish"`, JSON keys `hi`/`roman`).
6. **Category coupling:** confidence categories are the Delhi-survival topics, not skills (speaking/listening/…). The two concepts (`confidence` vs `skills`) are separate seeded objects.
7. **`app.js` is a 730-line monolith** mixing view rendering, business logic and state mutation; inline `onclick` handlers on a global `A`; `innerHTML` templates (escaped via `esc`, but easy to regress).
8. No input validation on `PUT /api/state` or `/api/ai` (history is capped to 12 messages only).
9. `sqlite3` connections never closed; schema creation on every request.
10. No tests, no CI, unpinned dependencies, no lockfile.
11. `run.sh` binds `0.0.0.0` (LAN-exposed, unauthenticated API and key-backed LLM endpoint).
12. Cache-buster is a hardcoded epoch in `index.html`.
13. Stale/invalid Anthropic default model ID.
14. Streak and XP logic is incomplete (streak never increments).
15. `deck/` (binary assets) lives in the app repo.

## 15. Problems to fix (priority order)

1. Real user identity and authorization (Phase 2). Until then, do **not** deploy this publicly.
2. Protect `/api/ai` (auth + rate limit) before any public exposure; it spends a paid key.
3. Fix `claude-sonnet-5` default model ID.
4. Close DB connections / move to a migration-managed schema.
5. Streak/achievement logic that actually computes.
6. `run.sh` host binding default → `127.0.0.1`.

## 16. Recommended refactoring (later, not now)

- Introduce a backend `db/` layer + numbered SQL migrations (keep raw SQL via `sqlite3`/SQLAlchemy Core; no heavy ORM needed). SQLite is fine through the academic phases; keep SQL portable (Postgres-compatible).
- Move content (`PACKS`, `SCENARIOS`, `READINGS`, `PLACEMENT`, `CATEGORIES`, `LANGUAGES`, `CITIES`) into tables and serve through read-only API endpoints; keep `content.js` as the seed source and as the offline fallback.
- Split `app.js` into per-view modules; keep the no-build approach (native ES modules) unless a framework is explicitly chosen.
- Move confidence/XP/streak/SRS calculations server-side (transactional) and have the frontend call APIs rather than mutate `state` locally.
- Generalise the prompt templates by language/city/scenario data.

## 17. Features that can be directly extended

| Existing | Extends naturally into |
|---|---|
| `SCENARIOS` roleplays | Situational learning (Phase 5), AI roleplay (Phase 11) |
| `PACKS` (7 days × phrases) | Lessons/phrases tables, emergency/travel packs |
| Confidence score + categories | Confidence & personalisation (Phase 6), weakness detection |
| Pronunciation scoring + TTS/STT | Speaking/listening (Phase 7) |
| SM-2 flashcards | Spaced repetition + mistake notebook |
| Placement test | CEFR placement/diagnostic (Phase 3) |
| SOS panel + 🆘 phrases | Emergency language pack |
| `/api/ai` proxy | AI tutor with learner context (Phase 11) |
| Offline engine | Keeps offline/no-key mode for demos and mobile/offline (Phase 15) |

## 18. Database audit and proposed normalized architecture (for discussion, nothing created)

**Current:** 1 table, 1 row, JSON blob. It cannot support multiple users, parents/children, multi-language, age groups, assessments or analytics without redesign. The blob's contents do, however, map cleanly onto relational entities:

| Blob field | Becomes |
|---|---|
| `name/city/language/level` | `users`, `user_languages` (learner + language + CEFR level + target city) |
| `confidence{}` | `confidence_scores(user, language, category/skill, score, updated_at)` (+ history table for trends) |
| `completedDays[]` | `user_lesson_progress` |
| `srs{}` | `flashcard_reviews` / `user_cards` |
| `placement` | `assessments`, `assessment_attempts` |
| `tutor[]` | `conversations`, `conversation_messages` |
| `achievements[]`, `xp`, `streak` | `user_achievements`, `xp_events`, `streaks` |

**Proposed domains (introduce table-by-table, phase-by-phase):**

1. **Identity & access:** `users`, `roles`, `user_roles`, `sessions`, `login_history` (later `two_factor_auth`, `parent_child`).
2. **Language catalogue:** `languages` (code, name, native name, tts_locale, script, is_active), `cefr_levels`, `cities`/`regions`, `age_groups` (data-driven bands, not hardcoded in UI).
3. **Content:** `topics`, `lessons`, `lesson_sections`, `phrases` + `phrase_translations` (one row per language, which replaces the `hi`/`roman`/`en` columns-as-fields), `vocabulary`, `grammar_topics`, `situations`, `situation_steps`, `questions`, `answers`, `hints`.
4. **Learner state:** `learner_profiles` (DOB/age band, goals), `user_languages`, `user_lesson_progress`, `flashcards/flashcard_reviews`, `mistakes`, `xp_events`.
5. **Assessment & personalisation:** `skills`, `confidence_scores`, `weaknesses`, `recommendations`, `assessments`, `assessment_questions`, `assessment_attempts`, `user_answers`.
6. **Speaking/AI:** `conversations`, `conversation_messages`, `speaking_sessions`, `pronunciation_scores`.
7. **Engagement:** `achievements`, `user_achievements`, `challenges`, `user_challenges`, `streaks`, `friends`, `notifications`.
8. **Parental:** `parent_child`, `parental_controls`.

**Design principles to keep:** 3NF/BCNF by default; many-to-many via junction tables (`lesson_phrases`, `user_roles`, `user_achievements`); language-specific text lives in rows (translation tables), not columns; FKs with explicit ON DELETE; CHECK constraints for score ranges (0–100) and CEFR values; indexes chosen from real queries (e.g. `(user_id, due_at)` for SRS); transactions around XP + confidence + progress writes; any denormalised aggregate (e.g. cached overall confidence) documented with its reason.

## 19. Proposed application architecture (evolutionary)

- Keep FastAPI + SQLite + vanilla SPA. No rewrite.
- Backend layering: `routers/` (HTTP + validation via Pydantic) → `services/` (business rules) → `repositories/` (SQL). `main.py` stays as the app factory and static server.
- Migrations: numbered `.sql` files + a tiny runner recording applied versions in `schema_migrations`.
- Frontend: progressively replace local `state` mutation with API calls, while retaining the offline fallback.
- AI: one `ai/` service taking a learner-context object (language, CEFR level, age band, current lesson, weaknesses) and building prompts from DB data rather than Delhi constants.

## 20. Recommended Phase 1 (for your approval, not started)

**Goal: introduce a real, migrated relational foundation without changing user-visible behaviour.**

1. Add a migration runner and `schema_migrations`; keep the legacy `state` table untouched.
2. Migration 001: `users` (with a seeded `demo-alex` learner), `languages`, `cefr_levels`, `cities`, `city_languages`. Seed from `content.js` values.
3. Add a small repository layer and close connections properly (context manager, `PRAGMA foreign_keys=ON`, WAL).
4. Add read-only `/api/languages`, `/api/cities` (frontend unchanged until used).
5. Introduce `pytest` with tests for migrations, constraints, and the existing endpoints.
6. Fix the Anthropic model ID and default `run.sh` host to `127.0.0.1`.
7. Write the normalisation/ER notes into `docs/ARCHITECTURE.md` as the first DBMS-report artefact.

Explicitly **not** in Phase 1: auth, content migration, frontend refactor, parent/admin.
