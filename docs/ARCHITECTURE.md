# LingoBuddy — Architecture (as of Phase 7C)

This document describes what is implemented now. Planned work is in `FEATURE_ROADMAP.md`; the pre-Phase-1 baseline is in `CURRENT_SYSTEM_AUDIT.md`.

## 1. Current architecture

```
Browser (vanilla JS SPA, unchanged)             FastAPI (backend/main.py)              SQLite (buddy.db)
 content.js  (content + config)  ──static──▶    GET  /  /static/*
 engine.js   (state, speech, scoring)  ───────▶ GET/PUT /api/state/{id}  ──▶ repositories/legacy_state ──▶ state (JSON blob)
 app.js      (views, router)           ───────▶ POST /api/ai  ──▶ LLM provider (optional) / client-side fallback
                                                GET  /api/health
                                                GET  /api/languages ┐
                                                GET  /api/cities    ┴▶ repositories/catalog ──▶ relational tables
```

- Since Phase 3 the frontend loads the language and CEFR catalogue from the API (`profile.js`), with `content.js` kept as the offline fallback. Cities (`/api/cities`) are still read from `content.js`.
- Learner progress still lives in the legacy `state` JSON blob.
- Phase 2 added server-side authentication and role-based access control (section 8). The frontend has no login UI yet; it keeps using the public demo learner (`DEMO_MODE`, on by default).

## 2. Phase 1 architecture

### Layers (`backend/`)

| Module | Responsibility |
|---|---|
| `main.py` | HTTP only: routing, the LLM proxy, static files. Runs migrations at startup via the FastAPI lifespan hook and publishes the DB path on `app.state`. Holds no SQL. |
| `repositories/catalog.py` | Read queries for languages, CEFR levels and cities (with their languages). |
| `repositories/legacy_state.py` | The original get/put of the JSON state blob, behaviour unchanged. |
| `db/__init__.py` | `connect(db_path)` context manager: opens a connection, sets `PRAGMA foreign_keys = ON`, uses `sqlite3.Row`, commits on success, rolls back on error, and **always closes**. |
| `db/migrate.py` | The migration runner. |
| `db/migrations/*.sql` | Ordered migrations. |

There is no ORM. Repositories take a `db_path` and use plain parameterised SQL, which keeps the dependency list unchanged (`fastapi`, `uvicorn`, `httpx`; `pytest` is dev-only in `requirements-dev.txt`).

`DB_PATH` (env, default `<repo>/buddy.db`) is read once in `main.py`; tests override `backend.main.DB_PATH` with a temp file.

### Migration strategy

- Files `backend/db/migrations/NNNN_name.sql`, applied in version order on every startup.
- `schema_migrations(version PK, name, checksum, applied_at)` records applied migrations. The runner creates it itself (`CREATE TABLE IF NOT EXISTS`).
- **Idempotent:** applied versions are skipped; a second run applies nothing.
- **Atomic:** each migration and its `schema_migrations` row run in one explicit transaction (SQLite DDL is transactional). A failing migration is rolled back completely, and earlier ones stay applied.
- **Tamper check:** the SHA-256 of each applied file is stored. If an applied file is later edited, startup fails with `MigrationError`. Schema changes must be new migration files.
- **Existing data is preserved:** `0001` creates `state` with `IF NOT EXISTS` and the exact legacy DDL, so on an existing `buddy.db` it is a no-op for that table. Nothing is dropped or rewritten.

Migrations shipped:

| Version | Purpose |
|---|---|
| `0001_foundation_schema` | `state` (legacy, no-op if present), `users`, `languages`, `cefr_levels`, `cities`, `city_languages`, one index |
| `0002_seed_foundation` | Seed rows transcribed from the prototype (see section 4) |
| `0003_auth_schema` | Phase 2: rebuilds `users` with credentials; adds `roles`, `user_roles`, `sessions` (section 8) |
| `0004_seed_roles` | Phase 2: the three roles; the demo learner gets `learner` |
| `0005_learner_profile_schema` | Phase 3: `language_levels`, `age_groups`, `learner_profiles` (section 9) |
| `0006_seed_learning_config` | Phase 3: supported combinations and age bands |
| `0007_curriculum_schema` | Phase 4: topics, lessons, vocabulary, grammar, exercises (section 10) |
| `0008_progress_schema` | Phase 4: `lesson_progress`, `exercise_attempts` |
| `0009_seed_curriculum` | Phase 4: the prototype's Delhi pack, glossary and placement questions as relational content |
| `0010_situations_schema` | Phase 5: `situations`, `situation_steps`, `situation_step_answers` (section 11) |
| `0011_situation_progress_schema` | Phase 5: `situation_progress`, `situation_step_attempts` |
| `0012_seed_situations` | Phase 5: the prototype's roleplay scenarios, pack days and SOS phrases as situations |
| `0013_personalization_schema` | Phase 6: `skills`, `exercises.difficulty`, `confidence_scores`, `weaknesses`, `daily_tasks`, two read-only attempt views (section 12) |
| `0014_seed_personalization` | Phase 6: the three skills; difficulty metadata by exercise kind |
| `0015_listening_schema` | Phase 7A: `audio_assets`, `listening_activities`, `listening_options`, `audio_sessions`, `listening_attempts` (section 13) |
| `0016_attempt_views_listening` | Phase 7A: the two personalization views gain a listening branch |
| `0017_seed_listening` | Phase 7A: 15 listening activities built from the existing Delhi pack and SOS phrases |
| `0018_speaking_schema` | Phase 7B: `speaking_sessions`, `stt_runs`, `speaking_transcripts` (section 14) |
| `0019_pronunciation_schema` | Phase 7C: `pronunciation_assessments`, `pronunciation_components`, `pronunciation_word_scores`, evidence view (section 15) |

### API added

- `GET /api/languages` → `{"languages": [{code, name, native_name, tts_locale}, …]}` in prototype order.
- `GET /api/cities` → `{"cities": [{slug, name, flag, emoji, tagline, blurb, ready, languages: [code, …]}, …]}`, languages in display order.

Existing endpoints keep their request/response contracts. Phase 2 adds access rules to `/api/state/{id}` and `/api/ai` (section 8).

## 3. Database schema

```
┌────────────┐
│ users      │  (no relationships yet)
└────────────┘

┌──────────────┐ 1        N ┌─────────────────┐ N        1 ┌──────────────┐
│ cities       │────────────│ city_languages  │────────────│ languages    │
└──────────────┘            └─────────────────┘            └──────────────┘
 PK id                       PK (city_id, language_id)      PK id
 UQ slug                     FK city_id → cities.id         UQ code
                                (ON DELETE CASCADE)         UQ name
                             FK language_id → languages.id
                                (ON DELETE RESTRICT)
                             UQ (city_id, sort_order)
                             IX language_id

┌──────────────┐   (standalone reference table)      ┌───────────────────────────┐
│ cefr_levels  │                                     │ state  (LEGACY, unrelated)│
└──────────────┘                                     └───────────────────────────┘
 PK code, UQ rank                                     PK user_id (TEXT)
```

| Table | Columns | Keys and constraints |
|---|---|---|
| `users` | `id`, `handle`, `display_name`, `created_at` | PK `id`; `handle` UNIQUE NOT NULL |
| `languages` | `id`, `code`, `name`, `native_name`, `tts_locale` | PK `id`; `code` UNIQUE; `name` UNIQUE; all NOT NULL |
| `cefr_levels` | `code`, `rank`, `label` | PK `code`; `rank` UNIQUE, CHECK ≥ 1 |
| `cities` | `id`, `slug`, `name`, `flag`, `emoji`, `tagline`, `blurb`, `is_ready` | PK `id`; `slug` UNIQUE; `is_ready` CHECK IN (0,1); all NOT NULL |
| `city_languages` | `city_id`, `language_id`, `sort_order` | composite PK; two FKs as above; UNIQUE `(city_id, sort_order)`; CHECK `sort_order ≥ 1` |
| `schema_migrations` | `version`, `name`, `checksum`, `applied_at` | PK `version` |
| `state` (legacy) | `user_id`, `data`, `updated` | PK `user_id` |

Only one explicit index exists: `idx_city_languages_language(language_id)`, for "which cities offer language X" and for efficient `ON DELETE RESTRICT` checks on `languages`. The other indexes are the ones SQLite creates for PK/UNIQUE constraints.

### Why each table exists

- **`languages`**: the prototype's 11 languages. It makes "add a language" a data change, not a code change. `tts_locale` is what the prototype already stores (`tts`).
- **`cefr_levels`**: the A1–C2 scale the UI shows. Ranking is stored explicitly so levels can be compared and ordered without string tricks. Only A1 and A2 are currently *assigned* to learners by the prototype's placement test. The labels "Beginner"/"Elementary" come from the app; B1–C2 labels are the standard CEFR names.
- **`cities`**: the prototype's five cities; only Delhi has content (`is_ready`).
- **`city_languages`**: the many-to-many between cities and languages (Delhi offers hi/hinglish/en; a language can belong to many cities). `sort_order` preserves the prototype's display order, which is meaningful.
- **`users`**: the minimum anchor for future per-user tables. It has no credentials, roles or email on purpose (authentication is a later phase). `handle` equals the legacy `state.user_id`.
- **`schema_migrations`**: migration bookkeeping.

### Functional dependencies and normalisation

- `languages`: `id → code, name, native_name, tts_locale`; also `code → all`, `name → all`. Candidate keys: `id`, `code`, `name`. Every determinant is a candidate key → **BCNF**.
- `cefr_levels`: `code → rank, label`; `rank → code, label`. Candidate keys: `code`, `rank` → **BCNF**.
- `cities`: `id → all`; `slug → all`. Candidate keys: `id`, `slug` → **BCNF**. The `flag` column holds a country emoji per city; if a `countries` entity is introduced later, `city → country → flag` would be a transitive dependency and should be split out. With one country in the data and no country attributes, a separate table is not justified yet.
- `city_languages`: `(city_id, language_id) → sort_order` and `(city_id, sort_order) → language_id`. Both determinants are candidate keys → **BCNF**. The composite key is what makes the city↔language relation many-to-many without repeating-group columns (1NF).
- `users`: `id → handle, display_name, created_at`; `handle → id, …`. **BCNF**.
- 1NF: all columns are atomic (the prototype's `langs: ["hi","hinglish","en"]` array became `city_languages` rows). 2NF/3NF follow from the above, since there are no partial or transitive dependencies in any table apart from the noted `flag` case.
- `state` is **not normalised**: the `data` column is a nested JSON document (repeating groups, non-atomic). It is kept only as the prototype's storage until later phases replace it with proper tables.

## 4. Seed data

Migration `0002` inserts values transcribed from the prototype:

- 11 languages from `LANGUAGES` in `frontend/content.js`;
- 5 cities and their language lists from `CITIES` in `content.js`;
- 6 CEFR levels from the level chips in `app.js`;
- 1 user, `demo-alex` / "Alex", matching the demo learner in `engine.js` and the existing `state` row key.

`tests/test_schema.py` checks the seeded languages and cities against `content.js` so the two sources do not silently drift. Business logic contains no copies of these values; they are only in `content.js` (still used by the frontend) and the seed migration.

## 5. How the legacy `state` table is handled

- Left intact, same name, columns and behaviour. The `/api/state/{id}` endpoints behave exactly as before, now through `repositories/legacy_state.py` with properly closed connections.
- Not migrated, not linked. There is no foreign key between `state.user_id` and `users.handle`, because existing rows may use any client-supplied id.
- Its eventual replacement (per-user relational progress tables) is scheduled for later phases. Nothing reads the new tables for progress yet.

## 6. Known limitations at this stage

- `/api/cities` is not yet consumed by the frontend, so city data is duplicated in `content.js` and the DB. Languages and CEFR levels are consumed since Phase 3.
- With `DEMO_MODE` on (default, to keep the prototype working) `/api/ai` and the `demo-alex` state are anonymous. See section 8 for the remaining Phase 2 limitations.
- `is_ready` and SQLite booleans are stored as 0/1 integers.
- SQLite only, with portable SQL. No connection pooling (one connection per operation).

## 7. Testing

`pytest` suite in `tests/` using temporary databases only (fixtures in `tests/conftest.py`): migration order, idempotency, atomic rollback, tamper detection, preservation of a pre-existing legacy DB and upgrade from a Phase 1 DB, schema, foreign-key enforcement and constraints, seed parity, the API endpoints including the legacy endpoints and AI fallback, and (`test_auth.py`, `test_authorization.py`) password hashing, registration, login, sessions, expiry, throttling, per-user state isolation and RBAC.

## 8. Phase 2: authentication and RBAC

### Schema (migration `0003`)

```
users ──< user_roles >── roles          users ──< sessions
 PK id     PK (user_id, role_id)         PK id     FK user_id → users.id (CASCADE)
 UQ handle FK user_id → users.id (CASCADE)         UQ token_hash, CHECK expires_at > created_at
 UQ email (NOCASE, nullable)  FK role_id → roles.id (RESTRICT)   IX user_id
 password_hash (nullable)     roles: PK id, UQ name
 CHECK (email IS NULL) = (password_hash IS NULL)
```

- `users` was rebuilt (rows copied) because SQLite cannot add a cross-column CHECK with `ALTER TABLE`. Users with no credentials (the demo learner, legacy rows) are valid but cannot log in.
- `roles` is data, not a CHECK constraint: `learner`, `parent`, `admin`. `user_roles` is the many-to-many junction (a user may hold several roles).
- `sessions` stores only the SHA-256 of the session token, so a leaked database cannot be replayed as cookies.
- Functional dependencies: `users`: `id → all`, `handle → all`, `email → all` (all candidate keys; BCNF). `roles`: `id ↔ name` (BCNF). `user_roles`: all-key (BCNF). `sessions`: `id → all`, `token_hash → all` (BCNF).
- Transactions: registration (user + roles + first session) and login (expired-session cleanup + new session) each run in one transaction through a single `connect()` block.

### Flow

1. `POST /api/auth/register` `{email, password, display_name, role?}`: `role` may only be `learner` (default) or `parent`; unknown or extra fields (`roles`, `user_id`, `handle`) are rejected with 422. The server generates the user's `handle`. The response sets the session cookie.
2. `POST /api/auth/login` `{email, password}`: a fresh session per login. Wrong password and unknown email return the same 401 and do the same amount of hashing work. After 5 failures per (email, client address) in 15 minutes it returns 429 with `Retry-After` (in-memory, per process).
3. `GET /api/auth/me`: the current user and roles, or 401.
4. `POST /api/auth/logout`: deletes the server-side session (so a copied cookie stops working) and clears the cookie. Idempotent.
5. Every request resolves identity only from the `llb_session` cookie → `sessions` row; bodies, headers and other cookies are never trusted for identity or role.

Passwords: scrypt (stdlib, N=2^15, r=8, p=1, random 16-byte salt, parameters stored in the hash string), constant-time comparison, 8–128 characters. Session tokens: `secrets.token_urlsafe(32)`, 7-day absolute expiry, cookie `HttpOnly; SameSite=Lax; Path=/`, plus `Secure` when `COOKIE_SECURE=1`. Expired sessions are rejected and deleted on use, and a user's expired sessions are purged at login. Validation errors never echo the submitted password.

### Authorization

| Endpoint | Rule |
|---|---|
| `/api/health`, `/api/languages`, `/api/cities`, `/`, `/static/*` | public |
| `/api/auth/register`, `/api/auth/login`, `/api/auth/logout` | public (logout is a no-op without a session) |
| `/api/auth/me` | any authenticated user |
| `/api/admin/users` | role `admin` (401 anonymous, 403 otherwise); never returns password hashes |
| `GET/PUT /api/state/{user_id}` | the path id must equal the caller's own `handle` (403 otherwise, 401 anonymous). **Admins have no special access.** Since Phase 14A there is no exception: the demo learner's state is closed in every mode (section 22) |
| `POST /api/ai` | open while `DEMO_MODE` is on (keeps the prototype and offline fallback working); any logged-in user otherwise. Who actually reaches the model is narrower (section 22) |

Role guards are FastAPI dependencies in `backend/auth/deps.py` (`require_user`, `require_roles(...)`, `authorize_state_access`). Business logic is in `backend/auth/service.py`, SQL in `backend/repositories/users.py` and `sessions.py`, and HTTP in `backend/routers/auth.py`.

### Demo mode (transition)

`DEMO_MODE` (default `1`) keeps the prototype usable without an account: `/api/ai` stays reachable anonymously (and answers offline unless `DEMO_LIVE_AI=1`). With `DEMO_MODE=0`, `/api/ai` requires login. Until Phase 14A it also opened a shared `demo-alex` state to anonymous visitors; that was removed (section 22), and anonymous visitors now keep their state in the browser only.

### Creating an admin

Self-registration can never produce an admin. Use `.venv/bin/python -m backend.manage create-admin --email you@example.com --name "Name"` (prompts for the password).

### Configuration

`DEMO_MODE` (default `1`), `COOKIE_SECURE` (default `0`; set `1` behind HTTPS). Both are read at request time.

### Limitations

- No login/registration UI in the frontend yet; Phase 2 is API-only.
- The login throttle is in-memory and per process; there is no global rate limit or CAPTCHA, and registration is not rate limited.
- Registration reveals whether an email is taken (409).
- No password reset, email verification, login history, or "log out all devices" (later phases). No CSRF token: state-changing calls rely on `SameSite=Lax` and JSON bodies (cross-site JSON requests are blocked by CORS preflight because no CORS is enabled).
- Parent and learner roles have identical permissions today; parent-specific rules arrive with the parent portal.
- `/api/state` bodies are not size-limited.

## 9. Phase 3: languages, CEFR and the age system

### Schema (migrations `0005`, `0006`; additive, nothing existing was altered)

```
languages ──< language_levels >── cefr_levels          users ──1:1── learner_profiles
 PK id        PK (language_id, cefr_code)               PK+FK user_id → users.id (CASCADE)
              FK language_id → languages.id (CASCADE)   FK native_language_id → languages.id (RESTRICT)
              FK cefr_code → cefr_levels.code (RESTRICT) FK (target_language_id, cefr_level)
                                                             → language_levels(language_id, cefr_code) (RESTRICT)
age_groups (standalone)                                  CHECK native <> target; CHECK date_of_birth is a real YYYY-MM-DD date
 PK id, UQ code, UQ min_age, CHECK max_age >= min_age
```

| Table | Why it exists |
|---|---|
| `language_levels` | The supported (language, CEFR level) combinations. A catalogued language with no rows (Spanish, French, …) exists but cannot be a target language yet. Adding support is an `INSERT`. Seeded: A1 and A2 for `hi`, `hinglish`, `en`, matching the prototype (all shipped content is A1; the placement test only assigns A1/A2). |
| `age_groups` | Age bands as data: `child` (0–9, "Under 10"), `teen` (10–17), `adult` (18+, `max_age` NULL). 18 starts adulthood, so the teen band ends at 17. Experiences for each band are not built yet. |
| `learner_profiles` | One row per learner: native language, target language, CEFR level, date of birth. |

- **Composite foreign key:** `(target_language_id, cefr_level)` references `language_levels`, so the *database* rejects an unsupported pair, even if application validation were bypassed. The service also checks first, to return a field-level message.
- **Age group is derived, not stored.** `age_group = f(date_of_birth, today)` is a transitive dependency; storing it would be a 3NF violation and would go stale on a birthday. The service computes the age and looks the band up in `age_groups`. Non-overlap and full coverage of ages 0–120 can't be declared in SQLite; `tests/test_learning_config.py` verifies contiguity and exactly-one-band for every age.
- **Functional dependencies:** `language_levels`: all-key. `age_groups`: `id → all`, `code → all`, `min_age → all` (BCNF). `learner_profiles`: `user_id → all` (BCNF).
- No new index: the composite PK on `language_levels` serves the FK and lookups; `learner_profiles` is accessed only by its PK. Add an index on `(target_language_id, cefr_level)` when analytics needs "learners per language".
- Users keep their existing shape. Profile data lives in its own table so non-learners (parents, admins) carry no learner columns.

### API

| Endpoint | Access |
|---|---|
| `GET /api/languages` (unchanged) | public |
| `GET /api/cefr-levels` → `{levels: [{code, rank, label}]}` | public |
| `GET /api/language-levels` → `{language_levels: [{language, levels: [...]}]}` | public |
| `GET /api/profile` → `{profile: {...} \| null}` | role `learner`, always own profile (no id in the URL) |
| `PUT /api/profile` `{native_language, target_language, cefr_level, date_of_birth}` (full replace) | role `learner` |

The profile response adds the derived `age` and `age_group {code, label}`. The request rejects unknown fields, so a client cannot submit `age_group`, `user_id` or `handle`. Rules: languages must exist, native ≠ target, the level must be supported for the target, DOB must be a real past date and not over 120 years ago. Parents and admins get 403 and anonymous callers get 401, including in demo mode (demo mode only covers the prototype's own endpoints).

### Frontend

`frontend/profile.js` (new) plus three one-line touches in `app.js` (route, nav entry, CEFR chip list) and one script tag:
- Loads `/api/languages` and `/api/cefr-levels` into the existing `LANGUAGES` array and a `CEFR_LEVELS` list, falling back to the `content.js` values offline.
- `#/profile` page: a minimal sign-in / create-learner-account card for signed-out visitors (the prototype has no other login UI), then a form for native language, target language, level (only supported combinations are offered) and date of birth, showing the derived age group.
- The profile does **not** yet drive the prototype's lessons, placement or state. The "I'm New Here" flow and the demo learner are unchanged.

### Privacy note

Date of birth is personal data, and under-10 accounts are possible. Parental consent and the parent–child link arrive with the parent portal; until then a child can self-register.

## 10. Phase 4: lessons, vocabulary, grammar, exercises and progress

### Content migrated from the prototype (`0009`, generated from `content.js`)

| Prototype source | Became |
|---|---|
| `PACKS.delhi` (7 days) | 7 published lessons (`hi`, A1): title, description, situation, tip, order = day number |
| `CATEGORIES` | 7 `topics`; each lesson is linked to the topic of its day |
| the 30 pack phrases (`hi`, `roman`, `en`, `natural`) | 30 `phrase` vocabulary items: `text` = Devanagari, `pronunciation` = roman, English `meaning` (literal) and `natural` |
| `GLOSSARY` (18 words; `achha` is a duplicate spelling of `accha`) | 18 `word` items, each with an example phrase from the pack where one exists |
| tutor notes (`-iye` politeness, "na?" tag) | 2 grammar topics with examples taken from pack phrases |
| `PLACEMENT` (5 questions) | 5 multiple-choice exercises, placed in the lesson they belong to (the prototype's own level test is unchanged) |

**Not from `content.js` (please review):** the Devanagari spellings of the 18 glossary words (the glossary was romanised only), and 14 derived exercises: per lesson one *translation* (phrase 1, English to Hindi) and one *fill-in-the-blank* (a hand-picked word masked in a real pack phrase). `READINGS`, `SCENARIOS` (roleplays) and `TUTOR_INTENTS` were **not** migrated (reading passages and situations are later-phase content). All seeded content is Hindi; Hinglish and English targets have no lessons yet.

### Schema

```
topics ──< lesson_topics >── lessons >──< lesson_vocabulary >── vocabulary_items ──< vocabulary_translations >── languages
                               │  │                              │      ▲
                               │  └─< lesson_grammar >── grammar_topics ──< grammar_topic_texts >── languages
                               │                              └─< grammar_examples >─┘ (examples are vocabulary items)
                               └─< exercises ──< exercise_answers          vocabulary_items ──< vocabulary_examples >── vocabulary_items
users ──< lesson_progress >── lessons        users ──< exercise_attempts >── exercises (+ chosen exercise_answers)
lessons / vocabulary_items / grammar_topics  →  (language_id, cefr_code) FK → language_levels
```

| Table | Purpose and keys |
|---|---|
| `topics` | Categories (`slug` UNIQUE). Many-to-many with lessons via `lesson_topics` (index on `topic_id` for "lessons of a topic"). |
| `lessons` | `language_id` + `cefr_code` with a **composite FK to `language_levels`** (a lesson can only exist for a supported combination). `status` ∈ draft/published/archived (default draft). `UNIQUE (language_id, slug)`, `UNIQUE (language_id, cefr_code, sort_order)` (ordering, and the index behind "lessons of a language/level in order"). |
| `vocabulary_items` | Target-language words/phrases: `kind`, `text`, `pronunciation`; same composite FK; `UNIQUE (language_id, text)`. |
| `vocabulary_translations` | The item's meaning per **native** language (`PK (item_id, language_id)`): `meaning`, `natural`. Supports learners with any native language without duplicating target-language rows. |
| `vocabulary_examples` | An example of an item is another vocabulary item, so nothing is duplicated; `CHECK item_id <> example_item_id`. |
| `lesson_vocabulary` | Which items a lesson teaches and in what order (`UNIQUE (lesson_id, sort_order)`); an item can be in many lessons. Index on `item_id`. |
| `grammar_topics`, `grammar_topic_texts`, `grammar_examples`, `lesson_grammar` | A grammar concept per language/level; its title and explanation per reading language (multi-language ready); examples are vocabulary items; concepts attach to lessons. |
| `exercises` | `kind` ∈ multiple_choice/translation/fill_blank is the **answer format**. The subject is given by the optional links `item_id` (vocabulary question) and `grammar_topic_id` (grammar question). A new subject or format is data, not a new table. |
| `exercise_answers` | Options (multiple choice, exactly one `is_correct`) or accepted answers (typed kinds). `UNIQUE (exercise_id, answer_text)`. |
| `lesson_progress` | `PK (user_id, lesson_id)`: row created on the first attempt; `completed_at` set when every exercise in the lesson has a correct attempt; `CHECK completed_at >= started_at`. Status (not started / in progress / completed) is derived. |
| `exercise_attempts` | One row per submission (history kept): `answer_id` (multiple choice) or `submitted_text`, `is_correct`, `attempted_at`. Composite FK `(answer_id, exercise_id)` forces the chosen option to belong to the exercise. Index `(user_id, exercise_id, is_correct)` for "has this learner answered this correctly" and progress roll-ups. |

### Normalisation notes

- All tables are BCNF with respect to their declared keys (every determinant is a key). Translation and text tables (`PK (item_id, language_id)`) hold exactly the facts that depend on both parts of the key, which is what keeps native-language text out of the item rows (2NF).
- **Deliberate redundancy:** junction tables linking two language-bound rows (`lesson_vocabulary`, `lesson_grammar`, `grammar_examples`, `vocabulary_examples`) and `exercises` also store `language_id`, which is functionally determined by the parent rows. Composite foreign keys `(parent_id, language_id)` into parents that expose `UNIQUE (id, language_id)` make the database reject cross-language links (for example a Spanish word in a Hindi lesson); tests exercise this. This is a documented 3NF trade-off for integrity, not an accident.
- The derived `status` of progress and the learner's age group are not stored.
- CHECK constraints cover enumerations (kinds, status), ordering >= 1, non-blank text, and 0/1 flags. "Exactly one correct option per multiple-choice exercise" cannot be declared per kind in SQLite and is verified by `tests/test_curriculum_seed.py`.

### API (all require a signed-in **learner**; the user always comes from the session)

| Endpoint | Behaviour |
|---|---|
| `GET /api/lessons` | Published lessons in the learner's **target language at or below their selected level** (by CEFR rank), ordered by level then lesson order, each with topics and progress. 409 without a profile. |
| `GET /api/lessons/{id}` | Lesson content: situation, tip, topics, vocabulary (meanings in the learner's native language, falling back to `FALLBACK_CONTENT_LANGUAGE` = `en`), examples, grammar, exercises and progress. Exercise objects carry **no answer key and no explanation**. 404 for unknown, unpublished or out-of-scope lessons (indistinguishable). |
| `POST /api/exercises/{id}/attempts` `{answer_id}` or `{text}` | Grades server-side, stores the attempt, starts/completes progress in **one transaction**, and returns `{correct, correct_answers, explanation, lesson_progress}`. Multiple choice needs `answer_id` (must belong to the exercise); typed kinds need `text`. Typed answers are compared after Unicode normalisation that ignores case and punctuation but keeps Devanagari vowel signs. Unknown fields (e.g. `user_id`) are rejected. |
| `GET /api/progress/lessons` | The learner's started lessons (most recent first) with status and counts. |

Code layout: SQL in `repositories/curriculum.py` and `repositories/progress.py`; rules in `curriculum/service.py`; HTTP in `routers/curriculum.py`.

### Frontend

New `frontend/lessons.js` (+ a nav item "My Lessons", one route entry in `app.js`, one script tag; `profile.js` now shares its small API helpers): a lesson list (`#/lessons`) and lesson page (`#/lessons/:id`) with vocabulary, grammar and interactive exercises with immediate feedback. Signed-out, profile-less and no-content states link to the profile page or to the prototype's First Week. The existing "I'm New Here" flow, First Week pack, roleplays, tutor and learn tools are unchanged and still read `content.js`; nothing was removed.

### Limitations

- The profile's language and level do not drive the prototype's own screens; the prototype's local progress (`state`) and the database progress are separate until a later migration of the state blob.
- Lesson/exercise prompts and titles are single-language (English); only vocabulary meanings and grammar texts are translated per language so far. Topic names are English only.
- Lessons exist only for Hindi at A1. Lesson access for a level includes easier levels; there is no unlocking or adaptive difficulty.
- Translation answers are string comparisons (no spelling-variant tolerance beyond case and punctuation), e.g. "accha" vs "achha".
- Completion requires a correct answer to every exercise in the lesson; there is no attempt limit or rate limit.
- Placement stays a prototype feature; its questions also exist as lesson exercises. A proper assessment model is a later phase.

## 11. Phase 5: situational learning

### Content migrated (`0012`, generated from `content.js` and `app.js`)

| Prototype source | Became |
|---|---|
| `SCENARIOS` (7 roleplays) + the `PACKS.delhi` day of the same category | 7 situations (Hindi, A1): title, goal, setting and partner name/role from the scenario; description = the pack day's situation text; topic = the category topic |
| the day's pack phrases | `learn_phrase` steps that **reference** the Phase 4 vocabulary items (no copies) |
| scenario `opening` line + first suggested reply (`start[0]`) | one `choose_response` step; the suggested reply is the correct option |
| the scripted rule that answers that reply (its `text`/`en`) and its suggested replies `s` | one `conversation` step: the partner's real reply, with the prototype's own suggestions as the accepted answers |
| `SOS_LIST` (Help me now panel, 5 phrases) | 5 new phrase items, an **Emergency** situation (new topic) with `learn_phrase` steps, a `choose_response` and a `translate` step |

**Editorial, not from the prototype (please review):** the `difficulty` values (1–3; the prototype only implies a day-by-day ramp), the two wrong options in each `choose_response` (first replies borrowed from other scenarios), and the Emergency situation's title, description and two step prompts. `READINGS`, the roleplay keyword rules beyond the one reply used per situation, and `TUTOR_INTENTS` were not migrated. No "Workplace" situation exists because the prototype has none ("College / Work" is one category). The schema supports `fill_blank` steps, but no seeded step uses one (the tests do).

### Schema

```
topics ──< situations >── language_levels (language_id, cefr_code)
              │ 1
              └──< situation_steps >── vocabulary_items (learn_phrase steps; same-language composite FK)
                        │ 1
                        └──< situation_step_answers
users ──< situation_progress >── situations         users ──< situation_step_attempts >── situation_steps (+ chosen answer)
```

| Table | Purpose and keys |
|---|---|
| `situations` | `language_id` + `cefr_code` (composite FK to `language_levels`), `topic_id` (FK to `topics`), `slug`, `title`, `description`, `difficulty` (CHECK 1–5), `sort_order`, `status` (draft/published/archived, default draft). Persona columns `goal`, `setting`, `partner_name`, `partner_role` (name and role both set or both NULL) describe who the learner is talking to, so a later AI roleplay can be driven from the same row. `UNIQUE (language_id, slug)`, `UNIQUE (language_id, cefr_code, sort_order)`, `UNIQUE (id, language_id)`; index on `topic_id`. |
| `situation_steps` | Ordered (`UNIQUE (situation_id, sort_order)`). `kind` ∈ learn_phrase / choose_response / translate / fill_blank / conversation. CHECKs: `learn_phrase` needs `item_id`; every other kind needs a non-blank `prompt`. `prompt_meaning` is the English gloss of a target-language prompt. Composite FKs keep the step's language equal to its situation's and its vocabulary item's; index on `item_id`. |
| `situation_step_answers` | Options (`choose_response`, exactly one correct) or accepted answers (typed kinds, all correct). `UNIQUE (step_id, answer_text)`, `UNIQUE (step_id, sort_order)`. |
| `situation_progress` | `PK (user_id, situation_id)`; created on the first response; `completed_at` set when every step has a correct attempt; `CHECK completed_at >= started_at`. |
| `situation_step_attempts` | One row per submission (history kept). `answer_id` or `submitted_text` (never both; neither for an acknowledged `learn_phrase`). Composite FK `(answer_id, step_id)` forces the option to belong to the step. Index `(user_id, step_id, is_correct)`. |

**Normalisation and derived data.** All tables are BCNF. The current step, the steps-completed count, the attempt count and the status are **derived** from the attempt history, not stored, so they cannot disagree with it (a stored "current step" pointer would be a redundant, updatable copy). The same-language composite FKs are the deliberate redundancy described in section 10.

### Step behaviour

- Steps are taken **in order**. The server rejects a step beyond the current one with 409; already-passed steps (and every step of a completed situation) can be redone.
- `learn_phrase`: acknowledged with an empty body, always passes. `choose_response`: `answer_id` of one of the step's options. `translate`, `fill_blank`, `conversation`: `text`, compared after the shared normalisation (`backend/textnorm.py`: Unicode NFKC, case-folded, punctuation ignored, Devanagari vowel signs kept) against the accepted answers. A wrong answer records an attempt, does not advance, and returns the correct answers and the step's explanation.
- A response, its attempt row, the started-row and (when it completes the situation) `completed_at` are written in **one transaction**.
- Answer secrecy: `GET` never includes `is_correct`, explanations or typed answers. A step's vocabulary item is only returned on `learn_phrase` steps (on a `translate` step it would be the answer). `conversation` steps return their accepted replies as `suggestions` by design, as the prototype's roleplay offers them.

### API (learner role; the user always comes from the session)

| Endpoint | Behaviour |
|---|---|
| `GET /api/situations` | Published situations in the target language at or below the learner's level, each with topic, persona, difficulty and progress. 409 without a profile. |
| `GET /api/situations/{id}` | The situation with its ordered steps (vocabulary meanings in the learner's native language with the same fallback as lessons) and progress incl. `current_step_id`. 404 if unknown, unpublished or out of scope. |
| `POST /api/situations/{id}/steps/{step_id}/responses` `{}` / `{answer_id}` / `{text}` | Grades and records. 404 for a step of another situation, 409 out of order, 422 for a malformed answer. Unknown fields such as `user_id` are rejected. |
| `GET /api/progress/situations` | The learner's started situations, most recent first. |

Code layout: SQL in `repositories/situations.py`; rules in `situations/service.py`; HTTP in `routers/situations.py`.

### Frontend

New `frontend/situations.js` (+ a "Situations" nav item, one route entry in `app.js`, one script tag): a situation list with difficulty and progress (`#/situations`) and a step-by-step view (`#/situations/:id`) with the goal and partner, a progress bar, the current step, immediate feedback, suggestions for conversation steps, and a completion screen. The existing "I'm New Here" flow, First Week pack, roleplays, tutor and learn tools are unchanged; the prototype's roleplays still run from `content.js`.

### Limitations

- Situations exist only for Hindi at A1; other targets see an empty list and a link back to First Week.
- Prompts and explanations are English; only vocabulary meanings are per native language.
- Conversation steps are one scripted turn graded by exact (normalised) match against the suggestions, not free conversation. The persona columns are the hook for the later AI roleplay.
- Learning-progress state is separate from the prototype's local `state`.
- Nothing limits or rate-limits attempts.

## 12. Phase 6: confidence, weaknesses, adaptive difficulty, recommendations, daily plan

### What is stored and what is derived

| Concept | How it exists |
|---|---|
| Confidence | **Stored**: what the learner *says* (`confidence_scores`, self-reported, history kept). Never computed from answers. |
| Performance | **Derived** from `exercise_attempts` / `situation_step_attempts` through two views. Shown next to confidence, never merged into it. |
| Weaknesses | **Stored** with their evidence (`weaknesses`) so they have a lifecycle (active → resolved → reactivated); refreshed from attempts on read. |
| Adaptive difficulty | **Derived** on demand (a pure function of recent attempts); only a recommendation, never a change to content. |
| Recommendations | **Derived** on demand from weaknesses, confidence, progress and curriculum order. Not stored: storing them would duplicate data that is already stored and go stale. |
| Daily plan | **Stored** (`daily_tasks`), generated once per learner, language and day from the top recommendations. |

### Schema (migration `0013`; seed `0014`)

```
users ──< confidence_scores >── topics | skills   (exactly one of the two)   [+ optional lesson or situation context]
users ──< weaknesses >── topics (rule low_topic_accuracy) | vocabulary_items (rule repeated_item_errors)
users ──< daily_tasks >── lessons | situations | topics   (exactly one target)
exercises + difficulty (1 easy .. 3 hard)       skills (vocabulary, grammar, conversation)
VIEW learner_attempts        one row per graded attempt (lesson exercises + situation steps; learn_phrase acknowledgements excluded)
VIEW learner_attempt_topics  the same attempts attributed to topics (a lesson counts for each of its topics)
```

| Table | Key points |
|---|---|
| `skills` | Seeded only with skills the platform can serve today; speaking/listening/pronunciation are added as data in later phases. |
| `exercises.difficulty` | `NOT NULL DEFAULT 1 CHECK (1..3)`. Seeded by answer format (recognise < complete < produce: multiple choice 1, fill-in-the-blank 2, translation 3). This is editorial metadata; no exercise text, option or answer was changed (tested). |
| `confidence_scores` | `score` 0–100; `source` ∈ self_report/lesson/situation; `CHECK (topic_id IS NULL) <> (skill_id IS NULL)`; at most one of `lesson_id`/`situation_id` (`ON DELETE SET NULL`, so a rating outlives the content it followed); `language_id` is the learner's target language when recorded. Indexes on `(user, language, topic|skill, recorded_at)` serve "latest per dimension" and history. |
| `weaknesses` | The rule decides the subject (`CHECK`): topic for `low_topic_accuracy`, vocabulary item for `repeated_item_errors`. `attempts` and `incorrect` are the evidence (accuracy is derived, not stored); `CHECK 1 <= incorrect <= attempts`; `status` active/resolved with `resolved_at` (`CHECK`). One row per subject through two partial unique indexes (NULLs are distinct in `UNIQUE`). |
| `daily_tasks` | Exactly one target (`CHECK`), which must match `task_type`; `source` names the recommendation rule; `UNIQUE (user, language, date, priority)` and a unique expression index on `(user, language, date, task_type, COALESCE(target ids))` so the same task cannot appear twice in a day. `plan_date` is checked to be a real date; `done` requires `completed_at`. |

All tables are BCNF. The views are read-only conveniences so every rule reads one place; they add no stored data. Every row is owned by a user and cascades with it.

### Transparent rules (all thresholds live in `backend/personalization/rules.py`; no LLM, no learned parameters)

- **Low topic accuracy.** Over the learner's most recent 10 graded answers in a topic (lessons and situations combined): at least 6 answers **and** at least 3 wrong **and** accuracy below 60% ⇒ weakness. Severity: high below 40%, medium below 50%, otherwise low.
- **Repeated item errors.** A vocabulary item answered wrongly at least 3 times in total **and** the latest answer on it still wrong. Severity: 3 low, 4 medium, 5+ high.
- **No verdict from a few mistakes**: fewer than 6 answers, or fewer than 3 wrong, or one slip among many never flags anything. `learn_phrase` acknowledgements are not evidence. A weakness that stops holding becomes `resolved` (not deleted) and is reactivated if the pattern returns.
- **Adaptive difficulty.** From the last 8 graded lesson exercises: fewer than 5 answers ⇒ start at easy; accuracy ≥ 80% ⇒ one level above the level they have been working at (the rounded mean difficulty of those answers); accuracy < 50% ⇒ one level below; otherwise stay. The result carries its evidence and a plain-language reason.
- **Recommendations** (first 6 distinct targets, in this order, each only when its data exists): review a weak topic (most severe first) → review a problem item → continue an unfinished lesson → continue an unfinished situation → low self-reported confidence (≤ 50%) → confidence check-in for a topic practised ≥ 3 times but never rated → next unstarted lesson → next unstarted situation. A learner with no data therefore gets only the two starting points, and a learner with no content for their language gets none.
- **Daily plan.** The top 3 recommendations become tasks. Generation is deterministic and idempotent: a day that already has a plan is returned unchanged (without recomputing), so the plan does not reshuffle during the day. Unique indexes and `INSERT OR IGNORE` back this up against concurrent calls. Tasks the learner already completed on or after the plan date (lesson or situation finished, topic rated) are marked done when the plan is read; a task the learner skipped stays skipped.

### API (learner role; the user and target language always come from the session/profile)

| Endpoint | Behaviour |
|---|---|
| `POST /api/confidence` `{topic|skill, score, source?, lesson_id?, situation_id?}` | Records a self-report (201). Exactly one of topic/skill; the topic must have content for the learner's language/level; context ids must be visible to the learner. Unknown fields (e.g. `user_id`) are rejected. |
| `GET /api/confidence` | Per topic: latest confidence and recent performance (separately), per skill: latest confidence, and an unweighted overall mean of the latest topic ratings. |
| `GET /api/confidence/history?topic=&skill=&limit=` | Newest first. |
| `GET /api/weaknesses` | Refreshes the stored weaknesses from the attempts (idempotent) and returns the active ones with evidence and an explanation. |
| `GET /api/difficulty` | The adaptive difficulty recommendation with its reason and evidence. |
| `GET /api/recommendations` | Ordered recommendations, `next_activity`, and the difficulty recommendation; lesson targets carry `suggested_difficulty`. |
| `GET /api/daily-plan`, `POST /api/daily-plan/generate` | Today's plan (UTC date) for the target language; generate is idempotent. |
| `POST /api/daily-plan/tasks/{id}/status` `{status}` | pending / done / skipped. Someone else's task is a 404. |

Note: `GET /api/weaknesses` and `GET /api/recommendations` write derived rows (they refresh weaknesses), idempotently, in one transaction. Code layout: SQL in `repositories/personalization.py`; rules in `personalization/{weaknesses,difficulty,recommendations,plan,confidence}.py`; HTTP in `routers/personalization.py`.

### Frontend

New `frontend/plan.js` (+ a "My Plan" nav item, one route entry in `app.js`, one script tag): today's tasks (start, mark done, skip/undo, inline confidence rating for check-in tasks), the recommended next activity with the suggested exercise level, areas to improve, and per-topic confidence sliders shown next to recent accuracy. The prototype's own Confidence page (`#/confidence`, local weighted score) is unchanged.

### Limitations

- Confidence is self-reported only. There is no speaking/listening signal yet (those skills do not exist), and no weighting of topics in the overall value (the prototype's local score weights categories; this one does not).
- Weakness and difficulty rules are simple and global: no per-skill difficulty, no decay of old evidence beyond the recent-window rules, and exercise difficulty is set by answer format rather than measured. Situation steps have no 1–3 difficulty.
- The daily plan is frozen for the day by design: a weakness that appears later shows under "Recommended next" and "Areas to improve" but only enters the plan the next day. The date is the server's UTC date, not the learner's local date.
- A check-in task only completes when that topic is rated; a rating made earlier the same day counts.
- Recommendations name content only; they do not change which exercises the lesson page shows.
- Stored weaknesses are refreshed lazily (when read), not on every answer.
- Everything is per target language; switching language shows that language's own weaknesses, ratings and plan.

## 13. Phase 7A: listening and the audio-session foundation

Scope: listening activities, audio metadata and sessions, plus a usable Listening page. **Not** in this phase: microphone recording, speech recognition (STT) and pronunciation scoring (Phase 7B).

### Schema (migrations `0015`, `0016`; seed `0017`)

```
audio_assets ──(item_id, language_id)──> vocabulary_items          (playable sources of an item: metadata only)
listening_activities ──(item_id, language_id)──> vocabulary_items   (the phrase that is played)
        │ 1                      └── (language_id, cefr_code) ──> language_levels      topic_id ──> topics
        └──< listening_options ──(item_id, language_id)──> vocabulary_items            (the choices)
users ──< audio_sessions >──< listening_attempts >── listening_options / listening_activities
```

| Table | Key points |
|---|---|
| `audio_assets` | `provider` ∈ static / generated / external_tts (browser TTS is a runtime fallback, never a stored row). `source_url` is a site-relative path or an `https` URL (CHECK: no other scheme, no `//`, no `..`, no spaces); `mime_type` from a fixed audio list; `duration_ms > 0`; `is_active` switch; `UNIQUE (item_id, source_url)`. Same-language composite FK to the item. **No BLOB column anywhere**: only where a sound can be fetched from (a test asserts it). |
| `listening_activities` | Bound to a supported `(language, CEFR)` through the composite FK; `topic_id`; the played `item_id` (same-language composite FK); `mode` ∈ choose_meaning / choose_phrase; `difficulty` 1–3; ordering and publishing `status` as for lessons and situations. |
| `listening_options` | The choices: other vocabulary items (same-language composite FKs), `UNIQUE (activity_id, item_id)` and `(activity_id, sort_order)`. **There is no `is_correct` column**: the correct option is the one whose item is the activity's item, so the key cannot disagree with the activity. (Exactly one per activity, and 3 options each, is verified on the seed.) |
| `audio_sessions` | The generic container for one audio interaction: `kind` ∈ listening / speaking, `status` ∈ started / completed / abandoned / failed, `started_at`, `ended_at`, `duration_ms`. `CHECK (status = 'started') = (ended_at IS NULL)`, `ended_at >= started_at`, `UNIQUE (id, user_id)`. Speaking sessions (Phase 7B) reuse it with their own detail table. |
| `listening_attempts` | One answer: learner, session, activity, chosen option, `is_correct`, `plays` (0–99). Composite FKs force the **session to belong to the same learner** and the **option to belong to the same activity**; `UNIQUE (session_id)`. Every row is owned by a user and cascades with it. |

Indexes: per-activity, per-option and per-item lookups for the FK deletes and "activities of a topic/item"; `(user_id, kind, started_at)` on sessions; `(user_id, activity_id, is_correct)` and `(user_id, attempted_at)` on attempts for progress and newest-first listing. All tables are BCNF; same-language composite FKs are the deliberate redundancy described in section 10.

**Personalization integration (migration `0016`).** The two read-only views from Phase 6 (`learner_attempts`, `learner_attempt_topics`) each gained one `UNION ALL` branch for listening attempts. Nothing else changed: the existing weakness rules (topic accuracy, repeated item errors) and topic performance now count listening attempts automatically, and adaptive difficulty still reads only `source = 'lesson'`, so it is unaffected. Tests pin both directions.

### Seeded content (from existing material only)

15 published Hindi A1 activities, no new vocabulary (53 items before and after):
- for each of the 7 pack days: one **choose_meaning** (plays the day's 2nd phrase, difficulty 1) and one **choose_phrase** (plays its 3rd phrase, difficulty 2); the two wrong options are the next two phrases of the same day;
- one **Emergency** choose_meaning on the SOS phrase "Where's the nearest hospital?".

Editorial, not from `content.js`: the titles and prompts, the 1/2 difficulty by mode, and the rotation of the correct option's position (it appears in every slot). No audio file is shipped, so all playback uses the browser-TTS fallback until `audio_assets` rows exist.

### Audio abstraction (`backend/audio/service.py`)

`AudioService.resolve(conn, item_id)` returns an `AudioSource`:
- `kind: "url"` with provider (`static` / `generated` / `external_tts`), URL, MIME type, duration, voice, from the best **active** stored asset (static, then generated, then external TTS);
- otherwise `kind: "browser_tts"` with the language's TTS locale and `speak_text` (+ a romanised `speak_fallback_text`), needing no key and no row.

Providers implement `resolve(conn, item)` and are tried in order, so a new provider is added to the list, not wired into listening. `metadata()` lists an item's assets and what it currently resolves to. Generation is optional: a `TtsGenerator` (`provider`, `synthesize(text, locale) -> GeneratedAudio`) can produce a file and `ensure_asset()` records only its metadata; the default `NullTtsGenerator` does nothing, so no API key or paid dependency is needed. The listening service uses `listening.service.AUDIO`, which can be replaced (tests do) without touching the listening code.

### API (learner role; the user always comes from the session)

| Endpoint | Behaviour |
|---|---|
| `GET /api/listening` | Published activities in the target language at or below the learner's level, with topic, difficulty and the learner's progress (not_started / attempted / completed). 409 without a profile. |
| `GET /api/listening/{id}` | The activity: prompt, `audio` source, and options `{id, text[, pronunciation]}`. **No answer key**: no `is_correct`, no correct option id, no item id. 404 if unknown, unpublished or out of scope. |
| `POST /api/listening/{id}/attempts` `{option_id, plays?, response_ms?}` | Grades on the server, writes the session and the attempt in **one transaction**, and returns `correct`, `correct_option_id`, the heard phrase with its meaning, the attempt and progress. The option must belong to the activity (422 otherwise); `plays` 0–99 and `response_ms` 0–3,600,000 are bounded; unknown fields (`user_id`, `is_correct`, …) are rejected. |
| `GET /api/listening/attempts?limit=` | The learner's attempts, newest first. |
| `GET /api/listening/progress` | Activities total / attempted / completed, attempts, correct, accuracy (None until there is an attempt), last attempt time. |

Fixed paths are declared before `/{id}`, so `attempts` and `progress` are never parsed as ids. Code layout: SQL in `repositories/listening.py` and `repositories/audio.py`; rules in `listening/service.py` and `audio/service.py`; HTTP in `routers/listening.py`.

### Frontend

New `frontend/listening.js` (+ a "Listening" nav item, one route entry in `app.js`, one script tag): a list with overall progress, and an activity page with **Play / Replay / Slow**, the options, immediate feedback (the correct option marked, plus the phrase that was heard with its pronunciation and meaning), a play counter and "Try again / Next". Playback uses a stored file when the server returns one, otherwise the prototype's own `Engine.speak` (browser speech synthesis, with the romanised fallback for devices without a Hindi voice). The spoken text is never rendered. The prototype's own Learn > Listening quiz is untouched.

### Limitations

- **Browser TTS needs the text on the client.** With the fallback the response necessarily carries `speak_text` (the phrase being played), so a determined client could read it; the UI never displays it. A stored audio file carries only its URL, which is how this closes once real audio exists. The server-side key (which option is correct) is never sent before answering.
- No audio files are shipped, and there is no TTS generator (only the interface); quality depends on the learner's browser and installed voices. Devices without a Hindi voice fall back to the romanised text.
- `plays` and `response_ms` are client-reported and only bounded, never used for grading.
- Hindi A1 only; other target languages see an empty list. Activity titles and prompts are English.
- Listening is objective (choose an option); there is no recording, recognition or pronunciation scoring yet (Phase 7B). `audio_sessions.kind = 'speaking'` exists in the schema but no code creates it.
- A phrase with several listening activities is one item for the item-error rule, so repeated listening mistakes on it can flag the phrase; this is the intended reuse of the Phase 6 rules, not a new engine.

## 14. Phase 7B: speaking input and speech-to-text

Pipeline: **microphone (browser) → recording → speaking session → STT provider → transcript**. Not in this phase: pronunciation scoring, phoneme analysis, emotion detection, AI conversation. The transcript is only what the recogniser heard; nothing in the API or UI calls it correct, scores it, or compares it with the prompt.

### Schema (migration `0018`; no seed)

```
users ──< audio_sessions (kind 'speaking')  ──1:1──  speaking_sessions ──(item_id, language_id)──> vocabulary_items (the phrase to say)
                                                          │ 1
                                                          └──< stt_runs (one per transcription attempt) ──< speaking_transcripts (ranked hypotheses)
```

| Table | Key points |
|---|---|
| `audio_sessions` (reused) | **No second session system.** A speaking session *is* an `audio_sessions` row with `kind = 'speaking'` (the Phase 7A design). Its coarse status (started / completed / abandoned / failed) stays in step with the finer stage below. The one change: a unique index `(id, user_id, kind)` so the detail table can reference all three. |
| `speaking_sessions` | 1:1 detail (`session_id` PK). The composite FK `(session_id, user_id, kind) → audio_sessions` makes the **database** enforce that a speaking detail hangs off a *speaking* session of the *same learner*. Holds the prompt (`item_id` + same-language composite FK), `locale`, the pipeline `stage` and the recording **metadata**: generated `audio_ref` (a file name, never a path; CHECK forbids `/`, `\`, `..`, spaces), `audio_mime` (allow-list), `audio_bytes > 0`, `audio_sha256` (64 hex), `recording_ms > 0`, `recorded_at`, `audio_deleted_at`. CHECKs: a recording is described completely or not at all; `created` ⇔ nothing recorded; `recorded`/`processing` need the file reference; a deleted recording has no reference. **No BLOB/audio column exists** (a test asserts it). |
| `stt_runs` | One row per transcription attempt: `provider`, `locale`, `status` (processing / completed / failed), `error_code` (fixed list), timings. `CHECK (status = 'processing') = (finished_at IS NULL)`, `CHECK (status = 'failed') = (error_code IS NOT NULL)`. **Partial unique indexes**: at most one run in flight per session and at most one completed run per session, so concurrent transcription is refused by the database itself. Failed runs are kept as history; a retry is a new run. |
| `speaking_transcripts` | What a completed run heard: `text` (non-blank, ≤ 2000), optional `confidence` (0–1, only if the provider supplies one), `rank` (1 = best; providers that return alternatives add ranks 2, 3, …), `UNIQUE (run_id, rank)`. Composite FKs tie it to its run **and** to the session's owner. |

Indexes: `(user_id, item_id, stage)` for "prompts this learner practised", `item_id` for the FK, run history `(session_id, started_at)`, transcripts by session. All rows belong to a user and cascade with it. All tables are BCNF; same-language and ownership composite FKs are the deliberate redundancy described in section 10.

### Pipeline states (`speaking_sessions.stage`)

```
created --(recording stored)--> recorded --(transcribe)--> processing --> completed   (final)
    |                              |   ^                        |
    |                              |   '--- retry transcribe ---+--> failed
    '--------- cancel -------------'----------- cancel ---------'       cancelled    (final)
```
`recording` is deliberately **not** a server state: the recording happens in the learner's browser, and the server learns about it when the audio arrives, so its first state after that is `recorded`. Every transition is a guarded `UPDATE … WHERE stage IN (…)` (rowcount 0 means refused), so invalid or racing requests change nothing and return 409. The mapping to `audio_sessions.status` (created/recorded/processing → started, completed, failed, cancelled → abandoned) is applied by the service and verified after every transition in the tests.

### STT abstraction (`backend/speaking/stt.py`)

`STTProvider`: `name`, `capabilities` (supported MIME types, languages, max size) and `transcribe(audio, mime_type, locale) -> Transcription(text, confidence?, alternatives)`. Failures are `SttError(code, message)` with a fixed code set (`provider_unavailable`, `provider_timeout`, `provider_error`, `no_speech`, `unsupported_language`, `unsupported_format`, `recording_unavailable`); messages never contain a provider response body or a key. Providers:
- **`mock`** (deterministic, no network): the audio bytes carry the answer (`MOCKSTT:<text>`, `MOCKCONF:`, `MOCKALT:`, `MOCKFAIL`, `MOCKSILENCE`); audio without a marker returns a clearly labelled `[mock transcript]`.
- **`groq`** (Whisper through Groq's OpenAI-compatible endpoint): built on the `httpx` and `GROQ_API_KEY` the project already has, tested against a fake transport (no network, no key). It sends the recording to a third party, so it is used **only** when `STT_PROVIDER=groq` is set explicitly; a key alone does nothing.
- **Default: none.** With `STT_PROVIDER` unset a session can be recorded but transcription ends as a controlled `provider_unavailable` failure, and no audio leaves the machine. The Voice page tells the learner this up front.

Adding an engine means one class plus one line in `get_provider`; the speaking system never knows which engine ran.

### Processing model

`transcribe` runs in three steps: (1) a short transaction claims the session (`recorded|failed → processing`) and opens a run; (2) the provider is called **outside any transaction** with a hard timeout (`STT_TIMEOUT_SECONDS`, default 15, in a worker thread), so a slow provider never holds the database write lock or blocks other requests (tested); (3) a transaction stores the transcript (or the failure) and moves the session to `completed` or `failed`. A provider failure is a normal stored outcome (HTTP 200, stage `failed`, `error.code`/`error.message`), never a 500. Empty recognition results become `no_speech`. A run still `processing` after 120 s (for example a crash mid-call) is closed as `provider_timeout` the next time the session is read or transcribed, so a session can never stay stuck.

### Recording upload and storage (`backend/speaking/storage.py`)

- **Raw-body upload** (`Content-Type: audio/…`, optional `?duration_ms=`), so no multipart library (`python-multipart` is not installed) and no new dependency. The body is read in chunks and refused (413) as soon as it exceeds 5 MB, before it is buffered.
- **Validation does not trust the client:** the declared type must be on the allow-list (webm, ogg, mp4, mpeg, wav; parameters such as `;codecs=opus` are stripped) **and** the file's own leading bytes must match it (415 otherwise, so a script or executable cannot pass as audio); size is measured on the server (422 below 16 bytes, i.e. empty); the client-reported duration must be 1 ms – 30 s. (The server does not decode audio, so duration is bounded, not measured.)
- **Storage outside SQLite and, by default, outside the repository:** `RECORDINGS_DIR` (default `~/.lingobuddy/recordings`), directory mode 0700, files 0600, created exclusively. File names are generated (`rec_<32 hex>.<ext>`); a reference is re-validated on every use against a strict pattern and must resolve inside the directory (traversal, absolute paths, symlinks out of the directory and unknown extensions are refused). Uploaded bytes are only written and read back, never executed or served. `.gitignore` also excludes `recordings/` and `*.webm`.
- **Data minimisation:** the recording file is deleted after its transcript is saved (`SPEAKING_KEEP_AUDIO=1` keeps it) and when a session is cancelled; the metadata (type, size, hash) stays. A failed session keeps its file so the transcription can be retried.
- Filesystem paths and hashes are never returned by the API.

### API (learner role; the user always comes from the session)

| Endpoint | Behaviour |
|---|---|
| `GET /api/speaking/prompts` | Phrases the learner can practise (phrases of their published lessons and situations at or below their level; single words excluded), with a `practised` flag, and `stt` availability/limits. |
| `POST /api/speaking/sessions` `{item_id?}` | Creates a session (201) in stage `created`; without `item_id` the next phrase not yet practised is chosen. The phrase must be an available prompt (422). Unknown fields (`user_id`, `stage`, …) are rejected. |
| `GET /api/speaking/sessions`, `GET /api/speaking/sessions/{id}` | List (newest first) / one session: prompt (with a model pronunciation source), recording summary (type, size, duration), transcript, error, attempts. |
| `POST /api/speaking/sessions/{id}/recording` | Stores the recording (only from `created`). 413 / 415 / 422 for oversize / unsafe / empty, 409 if the session has one already or is finished. |
| `POST /api/speaking/sessions/{id}/transcribe` | Runs the pipeline step (from `recorded` or `failed`). |
| `POST /api/speaking/sessions/{id}/cancel` | Cancels (from `created`, `recorded`, `failed`) and deletes the file. |
| `GET /api/speaking/progress` | Sessions by outcome, prompts available and practised. Counts practice; it grades nothing. |

Someone else's session is indistinguishable from a missing one (404) on every operation. Code layout: SQL in `repositories/speaking.py` (every learner-data query and every stage change is scoped by user), rules in `speaking/service.py`, `speaking/stt.py`, `speaking/storage.py`, HTTP in `routers/speaking.py`.

### Frontend (`frontend/voice.js`, route `#/voice`, nav "Voice Practice")

The prototype already owns `#/speaking` (its local scoring page), which is untouched. Flow: prompt → **Record** → red indicator + timer → **Stop** → review (use / record again / cancel) → "turning your speech into text…" → result showing **"You were asked to say"** and **"Speech recognition heard"** as separate blocks with a note that it is not a pronunciation score. The microphone is requested only when Record is pressed (no session is created if permission is refused), is released on stop, cancel, error and page exit, and recording ends by itself at the maximum length. Handled with clear messages: unsupported browser, permission denied, no microphone, microphone busy, recorder failure, empty or too-short recording (never uploaded), server rejection, STT failure, and "speech recognition isn't set up". Prompts can be chosen from a list; "Hear it" reuses the prototype's browser speech synthesis.

### Personalization: deliberately unchanged

Speaking sessions are **not** performance evidence. A transcript that differs from the prompt is not a learner error (recognisers mis-hear; Hindi may come back in Devanagari or Roman letters), so feeding it to the weakness rules would invent weaknesses, and there is no deterministic content rule that supports the comparison. The two attempt views do not read the speaking tables, and tests pin that (many mismatching or failed sessions create no weakness, difficulty or recommendation changes). A later phase can add evidence on purpose once there is a defensible measure.

### Configuration

`STT_PROVIDER` (`none` default / `mock` / `groq`), `STT_MODEL` (default `whisper-large-v3-turbo`), `STT_TIMEOUT_SECONDS` (15), `RECORDINGS_DIR`, `SPEAKING_KEEP_AUDIO` (0). Nothing needs a paid key to run the test suite.

### Limitations

- `mock` is not speech recognition. Real transcripts need `STT_PROVIDER=groq` (a third party receives the audio) or another provider added behind the interface; quality, especially for Hindi and for Hinglish in Roman letters, is the provider's.
- Recording length is client-reported and only bounded; the server checks size and content type, not the decoded duration.
- Browser support follows `MediaRecorder` (webm/opus in Chrome and Firefox's ogg/opus, mp4 on Safari). The automated frontend tests run the real page code in JavaScriptCore with a stubbed microphone, recorder, clock and Blob (macOS only; skipped elsewhere), so the real permission prompt and real audio capture are not exercised.
- Transcription is synchronous within the request (bounded by the timeout), not a background queue; a provider-call thread cannot be force-killed after a timeout. Stale-run recovery happens when a session is read, so `GET /api/speaking/sessions/{id}` can write (idempotently).
- Voice recordings are sensitive, particularly for children. The default deletes them after transcription and stores them outside the repository, but retention policy, parental consent and the parent–child link belong to the parent-portal phase.
- Only Hindi A1 prompts exist (the existing phrases); no speaking curriculum was added.

## 15. Phase 7C: pronunciation assessment

Flow: recording → STT transcript (Phase 7B, unchanged) → **assessment** → two separate results. Not in this phase: parent controls, gamification, AI roleplay, emotion detection, a redesign of the STT pipeline.

### What this phase can and cannot honestly do

The project has **no acoustic pronunciation model**, and its speech provider (Groq Whisper) returns text, not a pronunciation analysis. So:
- **Content match** is computed by us, deterministically, from the transcript. It is always available.
- **Pronunciation** comes only from a pronunciation *provider*. The default is **none**, and the result is then reported as "not available", never estimated. The only provider shipped is a deterministic **mock** for development and tests, labelled as such everywhere.
- **No real provider adapter was written.** None can be built from the dependencies and configuration the project already has; adding one means implementing one interface (below).
- Nothing in the code or API can state a phoneme-level finding, because nothing produces one.

### Two measurements, never merged

| | Content match | Pronunciation |
|---|---|---|
| Question | Did speech recognition hear the words of the phrase? | How was it pronounced, according to a provider? |
| Source | This code (word alignment of transcript vs phrase) | A `PronunciationProvider` only |
| Available | Always, once a transcript exists | Only with a configured provider |
| Stored as | `words_expected`, `words_matched` (percentages are derived) | `overall_score`, optional components, optional word scores |
| Says | "3 of 4 words recognised" | "NN / 100" with its `method` |

They do not influence each other (tests prove both directions): a perfect transcript with a low provider score stays low; an unrelated transcript with a high provider score stays high. There is no combined score, and the API/UI never offer one.

### Schema (migration `0019`; no seed)

```
speaking_sessions ──< pronunciation_assessments >── speaking_transcripts   (the exact transcript assessed)
                              │ 1                     (composite FKs: owner = the session's learner; transcript belongs to the same session)
                              ├──< pronunciation_components   (only components the provider reported)
                              └──< pronunciation_word_scores  (only if the provider reported word scores)
VIEW learner_pronunciation_evidence  (completed assessments whose method is 'model' only)
```

| Table | Key points |
|---|---|
| `pronunciation_assessments` | `FK (session_id, user_id) → speaking_sessions` (ownership) and `FK (transcript_id, session_id) → speaking_transcripts` (a unique index `(id, session_id)` makes an assessment unable to cite another session's transcript). `status` completed/failed; `overall_score` 0–100; `CHECK (status='completed') = (overall_score IS NOT NULL)`, `CHECK (status='failed') = (error_code IS NOT NULL)`; `method` ∈ mock / proxy / model (required whenever there is a score); `words_expected >= 1`, `0 <= words_matched <= words_expected`; error codes from a fixed list. **Partial unique index: one completed assessment per session**; failed attempts are kept as history. Indexes on `(session_id, id)` and `(user_id, created_at)`. |
| `pronunciation_components` | `PK (assessment_id, component)`, component ∈ phoneme_accuracy / word_accuracy / fluency / prosody / confidence, score 0–100. A row exists only if the provider reported that component. |
| `pronunciation_word_scores` | `PK (assessment_id, position)`, word, score 0–100, only if reported. |
| *(none for phonemes)* | There is deliberately **no phoneme table**: there is nothing to store until a provider really reports phoneme data (a `phoneme_accuracy` *component* is accepted only if a provider declares and supplies it). |

`method` states what kind of numbers they are: **mock** (a controlled test signal, not a measurement), **proxy** (an indirect measure such as recogniser confidence), **model** (a real acoustic model). No audio, path or wording is stored; feedback is derived at read time. This extends the Phase 7B speaking model: there is no second session system. All rows belong to a user and cascade with the session or user.

### Provider architecture (`backend/speaking/pron_providers.py`)

`PronunciationProvider`: `name`, `method`, `capabilities` (components it can report, whether it reports word scores, languages, `requires_audio`) and `assess(PronunciationInput) -> PronunciationResult(overall?, components, word_scores)`. The input carries the target phrase (script and romanised), the locale, the transcript (text, confidence) and, only if the provider needs it, the recording. A provider returns only what it measured and leaves the rest out. Failures are `PronError(code)` and never leak provider detail. The mock reads its answer from controlled markers in the synthetic test audio (`MOCKPRON:`, `MOCKPRONC:component=n`, `MOCKPRONW:word=n`, `MOCKPRONFAIL`), so a test decides exactly what the "provider" reports; **it never looks at the speech or the transcript**, and audio with no marker yields `no_signal`, not an invented score. Selection is explicit: `PRONUNCIATION_PROVIDER=mock`; unset/`none` means unavailable; an STT provider or `GROQ_API_KEY` alone never enables pronunciation.

### Scoring methodology

1. **Provider output is validated strictly.** Every number must be a finite number from 0 to 100 and not a boolean; components must be known **and declared by the provider**; word scores only from a provider that declares them (≤ 50 entries, words ≤ 60 characters). Any violation rejects the **whole** result as `malformed_output`. Nothing is clamped, because a value outside the scale cannot be trusted, and no partial result is stored.
2. **Rounding:** stored scores are whole numbers, rounded half up.
3. **Aggregation:** overall = the provider's own overall score if it gave one; otherwise the plain, equal-weight mean of the component scores it gave; with neither, the assessment fails as `no_signal`. No component is ever created on the provider's behalf.
4. **Content match:** both texts are normalised (case, punctuation and the danda ignored; Devanagari vowel signs kept) and split into words; the target is taken in the script the transcript came back in (decided by Devanagari *letters*, so a "।" does not count); the word lists are aligned in order (`difflib`). Equal runs are matched; the rest are *missing*, *changed* or *extra*. Spelling variants of romanised Hindi (accha / achha) are different words.
5. **Thresholds:** one display convention only: a word the provider scored **below 60** is listed under "words to practise". It is not a pass mark. There are no bands, grades or overall verdicts.
6. **Limitations:** the mock's numbers are controlled test values; automated scores (when a real model exists) are an estimate and not a teacher's judgement; the content match depends on the recogniser's spelling of Hindi.

### Feedback methodology (`build_feedback`)

Built only from stored facts, as typed items (`content`, `pronunciation`, `notice`):
- *content:* "Speech recognition picked up N of M words"; "It did not pick up: …"; "It heard “x” where the phrase has “y”"; "It also heard: …" (always described as what the **recogniser** heard, with a note that a difference "does not by itself show a pronunciation problem");
- *pronunciation:* "Words to practise (word scores from the provider): …" only from provider word scores; "Reported by the provider: Fluency 70, …" only for components that exist; if the provider reports only an overall score the learner is told there are no word or sound details;
- *notice:* the method's limitation, or why pronunciation is unavailable.
It never says "your pronunciation of X is wrong", never mentions sounds, phonemes or vowels, never turns a missed word into a pronunciation finding, and never invents detail (each of these is a tested rule).

### Assessment flow (`backend/speaking/assessment.py`)

`assess` has three steps like the STT pipeline: (1) a short transaction validates ownership and state, computes the content match and prepares the provider input; (2) the provider is called **outside any transaction**, time-limited (`PRONUNCIATION_TIMEOUT_SECONDS`, default 15) in a worker thread, and its output validated; (3) one transaction stores the assessment, components and word scores together. Rules:
- the session must belong to the caller (else 404) and be `completed` with a transcript (else 409);
- **idempotent:** a session with a completed assessment returns it unchanged and the provider is not asked again; a concurrent request that completes first is returned instead of an error (the partial unique index decides);
- a failure is a stored outcome (HTTP 200, `status: failed`, an error code), never a 500; a failed attempt can be retried, up to 5 attempts per session;
- a provider that analyses audio needs the recording: if it has already been deleted the result is `recording_unavailable`.

### Retention (privacy)

Phase 7B deleted the recording as soon as it was transcribed. A provider that analyses audio needs it for one more step, so **only when a pronunciation provider that requires audio is configured** the deletion moves to the end of the assessment. It is bounded: a transcribed recording that is never assessed is removed after 10 minutes, a failed session's recording after 24 hours (a sweep runs at startup and whenever a session is created; `SPEAKING_KEEP_AUDIO=1` still keeps everything on purpose). With no provider configured (the default) nothing changes: the recording is deleted at transcription.

### API (learner role; the user always comes from the session)

| Endpoint | Behaviour |
|---|---|
| `POST /api/speaking/sessions/{id}/assess-pronunciation` | Runs (or returns) the assessment: `content_match`, `pronunciation`, `feedback`. Idempotent. |
| `GET /api/speaking/sessions/{id}/pronunciation` | The session's assessment, or `{"assessment": null}` if not assessed (404 for an unknown or foreign session). |
| `GET /api/speaking/pronunciation/history?limit=` | The learner's attempts, newest first. |
| `GET /api/speaking/pronunciation/progress` | Counts, summed word-match totals, and pronunciation averages **per method** (test or proxy scores are never blended with real measurements; there is no single average). |

The `pronunciation` object: `available`, `score` (0–100), `method`, `method_label`, `is_measurement` (true only for `model`), `components`, `word_scores`, `error`. Provider names, file paths, hashes and user ids are never returned. `GET /api/speaking/prompts` also reports whether pronunciation analysis exists.

### Frontend (`#/voice`)

After the transcript the page assesses automatically and shows three separate blocks: **Speech recognition heard** (the transcript, with "not a pronunciation score"), **Word check: what was recognised** ("N of M words recognised"), and a separately bordered **Pronunciation** card with the score as "NN / 100", a visible **test-score label** when the method is not a real measurement, components and word scores only if present, then the feedback and a note that the two are different measurements. With no provider, or on failure, the card says "Not available" with the reason (and offers a retry only where retrying can help); the transcript and word check are still shown.

### Personalization

The Phase 6 rules and views are **unchanged** and do not read pronunciation data, so one poor attempt, any number of poor mock scores, or a transcript mismatch cannot create a weakness or change a recommendation (tested). The only new evidence channel is the view `learner_pronunciation_evidence`, which admits **completed assessments by a real `model` method only**: mock and proxy scores are excluded by construction, and nothing consumes it yet, so a later phase must opt in on purpose.

### Configuration

`PRONUNCIATION_PROVIDER` (`none` default / `mock`), `PRONUNCIATION_TIMEOUT_SECONDS` (15); constants in `backend/settings.py` (`PRON_MAX_ATTEMPTS`, `PRON_AUDIO_GRACE_SECONDS`, `FAILED_AUDIO_GRACE_SECONDS`). No paid service is needed for the test suite.

### Limitations

- **There is no real pronunciation measurement yet.** The shipped provider is a mock; with none configured the learner gets the word check only. Every mock score is labelled a test score.
- The word check is only as good as the recogniser, especially for Hindi and for romanised Hinglish spelling; a difference is not evidence of a pronunciation problem and the feedback says so.
- A model provider would need to be added behind the interface, and its output validated by the same strict rules; per-phoneme data would also need a table.
- Recording retention with an audio-analysing provider now lasts up to 10 minutes after transcription (failed sessions: 24 hours) unless assessed or kept on purpose; voice data of children still needs the parental-consent work of a later phase.
- Frontend tests run the real page code in JavaScriptCore with a stubbed microphone and recorder (macOS only); real microphone capture and the real browser permission prompt were not exercised.

## 16. Phase 8: kids and teen learning

Migration `0020_age_targeting_and_child_game.sql`. Age groups are the Phase 3 ones (child under 10, teen 10-17, adult 18+); nothing new is invented, and the group is **derived** from the date of birth on every request (`learner.service.with_age_group`), never stored.

### Age targeting

`lesson_age_groups`, `situation_age_groups` and `listening_activity_age_groups`: `PRIMARY KEY (content_id, age_group_id)`, real foreign keys (content `CASCADE`, age group `RESTRICT`), one table per content type (no polymorphic ids). **A content row with no target rows is open to every age group**, so existing and future content is universal unless someone restricts it. A row with targets is shown only to those groups (a union).

The SQL is one shared fragment (`backend/repositories/age.py`). Every learner-facing selection takes a **required** `age_group_id` (lessons, situations, listening activities, the topics and lessons the recommendation rules draw on, and speaking prompts), so a call site that forgot it fails loudly instead of leaking content. A restricted item is a 404 by id, exactly like a nonexistent one. Adults keep everything: the only seed is editorial, restricting the existing College lesson, situation and two listening activities to **teen and adult** (a campus scenario); this is the one decision a content owner may want to change, and it is plain data in the migration.

### Child adventure

Levels are **derived**, not stored: the child's age-filtered listening activities grouped by topic in their usual order. A level is completed when every activity has a correct attempt; it is unlocked when the previous level is completed. Answers use the Listening feature's own grading and attempt recording (`listening.service.submit_in`), so they feed the existing weakness and confidence systems unchanged.

Stored state is only the lives:

| Table | Purpose |
|---|---|
| `child_game_state(user_id PK, lives CHECK 0..5, lives_updated_at, created_at)` | Created lazily with 5 lives. |
| `child_life_losses(attempt_id UNIQUE, attempt_correct CHECK = 0, lives_after CHECK 0..4, ...)` | Composite FK `(attempt_id, user_id, attempt_correct)` into `listening_attempts(id, user_id, is_correct)`: a life can only be lost for a **wrong attempt of the same learner, once**. |

Rules (`backend/kids/lives.py`, pure functions of stored lives, anchor and `now`): 5 lives maximum, one regenerates every 10 minutes (`LIFE_REGEN_SECONDS`), computed server-side, remainder preserved, time going backwards counts as no time. A wrong answer is a guarded `UPDATE ... WHERE lives > 0`; at 0 lives answers are refused (409 with `next_life_in_seconds` and `Retry-After`) and leave no attempt. A loss never delays a life that is already on its way. **No endpoint sets lives**, and the client stores nothing authoritative. The grade, the attempt, the life and the regeneration are one transaction.

### API (learner role; the user always comes from the session)

| Endpoint | Behaviour |
|---|---|
| `GET /api/experience` | `{mode, age_group, features}`; never the date of birth. 409 without a profile. |
| `GET /api/kids/adventure` | Lives and the levels (number, title, icon, status, progress). Child only, others 403. |
| `GET /api/kids/levels/{n}` | The level's questions by position, with audio and choices by position. No ids, no answer key. 409 if locked, 404 if unknown. |
| `POST /api/kids/levels/{n}/answers` | `{question, choice}` (1-based, extra fields rejected). Returns correct, `correct_choice`, lives, level progress, `game_over`. |
| `GET /api/teen/home` | Teen only. Composes the existing lessons (filtered), `next_activity`, `difficulty`, top 3 weaknesses and the daily plan; nothing is recomputed. |

Voice safety: `POST /api/speaking/sessions` returns 403 for the child group (no voice capture of children in this phase).

### Frontend

`agemode.js` reads `/api/experience` and sets `body.mode-child` / `mode-teen`; children get a three-item navigation (Adventure, Listen, Me) and any other route opens the adventure; teens get a "My Path" item added to the unchanged navigation; adults and anonymous visitors see exactly what they saw before. `kids.js` is the level map and question screen (big buttons, hearts, game over with a countdown that is only a display; the server decides). `teen.js` renders `/api/teen/home`.

### Limitations

- Child levels reuse the listening content (about seven short levels); there is no separate child curriculum, and no rewards, social features, leaderboards or parent controls (later phases).
- The College restriction is an editorial choice. Real age suitability review of the content is still a human job.
- Child voice: speaking is simply blocked; consent and child-voice handling still belong to a later phase.
- Frontend tests run the real page code in JavaScriptCore (macOS only); visual layout was not checked in a real browser.

## 17. Phase 9: the parent portal

Migration `0021_parent_portal.sql`. Parents are ordinary users with the existing `parent` role; children are ordinary `learner` users. Nothing is copied: three small tables relate them.

| Table | Purpose |
|---|---|
| `parent_links(id, parent_id, learner_id, ...)` | `UNIQUE (parent_id, learner_id)`, `CHECK (parent_id <> learner_id)`, composite FKs into `user_roles` so the **database** refuses a link whose parent lacks the `parent` role or whose child lacks `learner` (role ids 2 and 1 are those seeded by 0004; a test ties them to the names). Removing a role or a user removes the link. |
| `parent_link_codes(learner_id, code_hash UNIQUE, expires_at, used_at/used_by, ...)` | One-time codes. Only a SHA-256 is stored. |
| `parent_controls(link_id PK, voice_disabled CHECK 0/1, updated_at)` | Per-relationship restrictions. No row means no extra restriction. |

### How a link is made (no discovery)

The **learner's own session** asks `POST /api/profile/parent-link-code` for a code (10 characters, no look-alike letters, 15 minutes, single use; a new code replaces the previous one). The parent submits it to `POST /api/parent/children`. Consuming the code and creating the link are one transaction, so a refused attempt (already linked, limit reached) does not burn the code. Wrong codes are throttled per parent (5 per 15 minutes, per process, like the login throttle). No endpoint searches, lists or accepts a learner id, so a parent cannot find or claim a learner who did not hand over a code. A child may have up to 4 parents and a parent up to 10 children (`settings.py`).

### Authorization

Parent endpoints require the `parent` role (learners and admins get 403, as everywhere in the existing RBAC; admins gain no special access). The child is named by the **parent's own link id**, never a user id, and every read starts from `(parent_id, link_id)`; an id that is unknown or belongs to another parent gives the same 404. The portal composes the existing services (lesson/situation/listening/speaking/pronunciation progress, confidence, weaknesses, daily plan) and the `learner_attempts` view; it keeps no progress of its own and returns no email, date of birth, handle, user id, transcript or recording reference. Weaknesses are re-worded for a parent and stripped of internal ids.

### Controls and the child-safety boundary

One control exists, because it is the only one the product needs and can enforce on the server: **`voice_disabled`**. A control can only **restrict**. `parent/controls.py` is the single decision point, called before a speaking session is created, a recording is accepted, audio is transcribed, and a new pronunciation analysis is made:

1. the child age group has voice off whatever any control says (Phase 8). No control value, and no parent, can switch it on; the controls view reports `voice_unavailable_reason: "age_group"`;
2. any linked parent's switch turns voice off for that learner (the strictest of several parents applies; unlinking removes that parent's restriction).

Reading results already produced (history, progress) is not blocked. A learner who grows out of the child group gets voice, unless a parent switched it off. Linking changes nothing for a child until a parent acts, and no biometric or new personal data is collected.

### API

| Endpoint | Role | Behaviour |
|---|---|---|
| `POST /api/profile/parent-link-code` | learner | `{code, expires_in_seconds}` |
| `POST /api/parent/children` | parent | `{code}`: links the child. 404 for any bad code, 409 duplicate/limit, 429 throttled. |
| `GET /api/parent/children` | parent | Linked children (name, age group, language, level). |
| `DELETE /api/parent/children/{id}` | parent | Stop following (the learner's data is untouched). |
| `GET .../{id}/overview`, `progress`, `weaknesses`, `confidence`, `activity` | parent | Read-only views. |
| `GET/PUT .../{id}/controls` | parent | `{"voice_disabled": true|false}` (strict boolean, unknown fields rejected). |

### Frontend

`parent.js` (`#/parent`, `#/parent/:id`): list and add a child, then a dashboard with the stats, areas to improve, confidence, recent activity, pronunciation evidence and the voice switch. `agemode.js` adds "My Children" to a parent's navigation; the profile page lets a learner make a link code and sends a parent to the family page. Child, teen and adult experiences are unchanged.

### Limitations

- A learner cannot yet see or revoke who follows them; only the parent can unlink. Anyone the learner gives a live code to becomes a follower, so older learners should treat the code like a password (it expires in 15 minutes).
- Only the voice control exists. Session or time limits, content visibility and per-feature switches were left out because enforcing them cleanly would touch every learning endpoint.
- The code throttle is per process and resets on restart.
- Mock pronunciation scores are shown to parents, labelled as test scores.
- Frontend tests run the real page code in JavaScriptCore (macOS only); visual layout was not checked in a browser.

## 18. Phase 10: gamification and a minimal social layer

Migration `0022_gamification_social.sql`. **Local Confidence (Phase 6) remains the learning metric**; XP is only a reward layered on top of the existing progress tables and the CEFR level in the learner profile stays authoritative. There is no second progression system: everything is derived from rows the earlier phases already write.

### How XP works (server-authoritative, idempotent)

The only thing that changes gamification state is `gamification.service.sync`, which reads what the learner has **already done** and credits it, once per thing, into the append-only ledger `xp_events` (`UNIQUE (user_id, kind, source_id)`, a trigger forbids edits). It runs when the learner (or a friend, for the leaderboard) loads a gamification page, so refreshing never pays twice, and no endpoint accepts an XP amount, a level, a date, a streak, a freeze or an achievement (bodies are `extra="forbid"`; tests confirm there are no such routes).

| Event | XP | Credited when |
|---|---|---|
| `exercise` | 5 | first correct answer to an exercise (`exercise_attempts`) |
| `listening` | 5 | first correct answer to a listening activity |
| `speaking` | 10 | first completed speaking practice of a phrase |
| `lesson` | 20 | a lesson with `completed_at` |
| `situation` | 25 | a situation with `completed_at` |
| `daily_task` | 10 | a task whose underlying lesson/situation is really completed (or a confidence check-in really recorded); marking a task done by hand earns nothing |
| `challenge` | by definition (1-100) | claiming a finished challenge |

Activity XP is capped at **150 per local day**; an over-cap thing is still recorded (once) with 0 XP so it can never pay later. Challenge rewards are outside the cap and never count as activity, toward streaks, or toward XP challenges. `xp_events.source_id` has no foreign key on purpose (it points into a table chosen by `kind`) so the ledger survives content edits.

**Levels**: level L starts at `50 * L * (L - 1)` XP (1: 0, 2: 100, 3: 300, 4: 600, 5: 1000 ...), maximum 20, with rank names Explorer / Traveller / Local / Insider / Native. Total XP, level, streak, freeze balance and challenge progress are derived, never stored.

### Streaks and freezes

A day is active if the learner earned XP from an activity on it, by the learner's **own timezone** (`learner_gamification.timezone`, validated against the IANA list; crediting runs before a timezone change so history keeps the day it happened on). `streak_days` holds one row per active day, so repeating activity never inflates a streak. A freeze (`streak_freezes`, an audit ledger) is earned on every 7th day of a run (max 2 held) and is spent, one per missed day and all-or-nothing, only when the learner returns after a gap it can fully cover. `streaks.compute` is a pure function; the database triggers also refuse overdrawing or exceeding the cap, and `UNIQUE (user_id, kind, day)` means a day can be frozen once. A streak is alive through today and yesterday.

### Achievements and challenges

Achievements are rows (metric + threshold, 9 seeded) computed from the ledgers; `learner_achievements` has `PRIMARY KEY (user_id, achievement_id)` so unlocking is idempotent. Challenges are definitions (`daily`/`weekly`, metric exercises/listening/lessons/xp/streak) with one `learner_challenges` instance per learner per period (weeks run Monday-Sunday). Progress is recomputed on every read; claiming is allowed only while the period is current and the target is met, as one transaction (guarded `UPDATE ... claimed_at IS NULL` plus the unique ledger row), and a replay gets 409.

### Social (friends only)

Learners of the **teen and adult** age groups only; the **child group is refused by the server on every social endpoint** (and a learner who becomes a child disappears from friends' lists). Friends must be in the same age group (checked when requesting and whenever shown). There is no search or user listing: a request needs the other learner's **friend code** (created on first use, replaceable at any time), wrong codes are throttled (5 per 15 minutes per process) and every failure looks the same (404). One pending request per pair in either direction (a partial unique expression index); a rejected request cannot be repeated for 7 days; up to 30 friends and 20 pending requests. Only the addressee can accept or reject (anyone else gets 404); either friend can remove the friendship. People are shown by display name, level and XP only: no e-mail, date of birth, handle or user id. There is no chat or messaging.

The **leaderboard** is friends-only (you and your same-age-group friends), week or all time, ordered by XP then name, ties sharing a rank. It has no input; scores come only from the ledger.

### API (learner role; the user always comes from the session)

`GET /api/gamification`, `PUT /api/gamification/settings` (timezone), `GET /api/gamification/achievements`, `GET /api/gamification/challenges`, `POST /api/gamification/challenges/{id}/claim`, `GET /api/social/friends`, `POST /api/social/friend-code`, `POST /api/social/friends/requests`, `POST /api/social/friends/requests/{id}/accept|reject`, `DELETE /api/social/friends/{id}`, `GET /api/social/leaderboard?period=week|all`. Ids in paths are the challenge/request/friendship rows' own ids and are ownership-checked.

### Frontend

`gamify.js`: `#/rewards` (level, XP, streak, freezes, challenges with a Claim button, achievements, recent XP, a timezone button) and `#/friends` (friend code, add by code, requests, friends, leaderboard). The navigation gains Rewards and Friends; the child navigation is unchanged (children never see them and their routes open the adventure), and parents do not get them.

### Limitations

- XP is credited when gamification is next read (opening Rewards/Friends, or a friend viewing the leaderboard), not the instant an answer is submitted, because the earlier phases were deliberately left unmodified.
- The prototype's own client-side XP/streak numbers (side card) are demo state and are not the account's XP.
- Children have XP, streaks and achievements through the API but no UI for them yet.
- Code throttles are per process. A freeze can be spent on a day that later turns out to have activity if that activity is synced late.
- Friend codes are bearer tokens: anyone given one can send a request (never see anything until the learner accepts).
- Frontend tests run the real page code in JavaScriptCore (macOS only); layout was not checked in a browser.

## 19. Phase 11: AI tutor and roleplay

Migration `0023_ai_tutor_roleplay.sql`. Both features sit on top of what already exists (profile, curriculum, situations, weaknesses, confidence, voice rules, parent controls, XP ledger) and add no second source of truth.

### Provider architecture (`backend/ai/`)

Domain code talks to `ai.base.Provider` only (`tutor_reply`, `roleplay_reply`, `roleplay_feedback`) with small bounded request objects; no vendor, URL or key appears outside the adapters. Everything a provider returns goes through `clean` (text only, control characters removed, trimmed, cut at 1,200 characters, empty or non-text is an error) and runs under a hard timeout (`runner.run`, `AI_TIMEOUT_SECONDS`, default 15).

| Provider | When |
|---|---|
| `MockProvider` (`ai/mock.py`) | **Default**, and the only one the test suite uses. Rule-based, deterministic and offline: it composes replies from the request it is given (stored facts, phrases from the learner's own content, the server's verdict) and never states anything that is not in it. It is not a language model. Works with no API key. |
| `LLMProvider` (`ai/llm.py`) | Only if `AI_PROVIDER=llm` **and** an LLM is configured through the existing settings (`GROQ_API_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `OLLAMA_URL`, the same ones `/api/ai` uses, via `main.call_llm`). A configured key alone changes nothing. Without a key, `llm` falls back to the built-in provider. |

`registry.FACTORY` is what teen and adult requests ask for (tests replace it); **children are always given `registry.offline()`**, enforced in the services, so a child's text never reaches an external model.

### Tutor

Tables `tutor_conversations`, `tutor_messages` (composite FK `(conversation_id, user_id)`, `UNIQUE (conversation_id, seq)`, optional `client_id`), `tutor_message_facts`. A conversation may be about one lesson, situation or topic (availability and age filters apply). The tutor is told the learner's language, CEFR level, mode (never the date of birth), the conversation context and at most 8 **stored facts** from the same services the learner can see (top weaknesses, lowest self-rated confidence, recent mistakes, answer counts) plus up to 5 phrases from their own content. The facts are stored with each reply (`tutor_message_facts`) and returned apart from the reply, whose text is labelled generated advice. It is never given a name, e-mail, id, password, session, recording, parent data or another learner's data (tested by recording the exact request object).

Bounded context: the last 8 messages go to the model however long the stored history is, the whole prompt is cut to 6,000 characters (oldest history first), a message is at most 500 characters, a conversation holds 100 messages and a learner 50 conversations. A send is: read and gather context, call the provider (no transaction held), then write the learner message, the reply and the facts together. **If the provider fails, nothing is stored** (502) and the same request, carrying the same `client_id`, can be repeated; a replayed `client_id` returns the stored pair without calling the model again.

Children: no free text. They send one of three built-in helper questions (`teach_me_a_phrase`, `say_it_again`, `what_does_it_mean`), receive a phrase from age-appropriate content, and are given no learner facts.

### Roleplay (built on Phase 5)

A session points at an existing situation and walks its existing steps; nothing is copied and Phase 5 progress is untouched. Each step becomes an objective shown to the learner (for a phrase step: its meaning in their language; otherwise the step prompt). The learner replies in their own words; **the server decides** whether it matches the stored answers (normalised), up to 3 tries per step with a hint ladder (word count, then first word); the model answer is revealed only when the step is answered correctly or missed on the third try, and is **never sent to the provider while a step is open**. The provider only voices the character; if it fails, the built-in provider answers and the turn is judged the same. Starting the same situation resumes the active session; a turn can carry a `client_id` (replay-safe). Completing returns evidence-based feedback (counts from the turns plus short texts), is idempotent, and calls the existing `gamification.sync` in the same transaction.

Spoken answers: a turn may reference the learner's own completed speaking session (Phase 7B); its transcript is the answer. That path calls `parent/controls.require_voice`, so the child restriction and any parent voice switch apply exactly as for speaking. A roleplay judges what was said, never how it sounded: the feedback always says there is no pronunciation analysis, and no pronunciation data is stored. The web page is text-only.

### XP

Tutor chat earns nothing. A roleplay completed with at least half its steps correct is credited **as that situation** through the existing ledger (`xp_events`, kind `situation`, 25 XP, once per situation, shared with completing the situation itself; daily cap applies). This is one additive source query in `repositories/gamification.py`; the schema, rules and service of Phase 10 are unchanged. No endpoint accepts XP, a verdict, an answer or a step id.

### API (learner role; the user comes from the session; another learner's id is a 404)

`GET/POST /api/tutor/conversations`, `GET /api/tutor/conversations/{id}`, `GET .../{id}/messages?after_seq&limit`, `POST .../{id}/messages`; `GET/POST /api/roleplay/sessions`, `GET /api/roleplay/sessions/{id}`, `POST .../turns`, `POST .../complete`, `GET .../feedback`. Errors: 401/403 (role), 404, 409 (profile, full, state), 422, 502 (provider failure, nothing stored).

### Frontend

`ai.js`: `#/ai-tutor` (conversations, history, input, "Thinking…", error with the text kept for a safe retry, stored facts shown apart, child helper buttons) and `#/ai-roleplay` (situation list, scene, objective, hint, tries left, progress, model answers once resolved, feedback and XP). Navigation gains Tutor Chat and Roleplay; the child navigation and parent navigation are unchanged.

### Limitations

- The default provider is rule-based, not a language model: replies are templates over real data. A real model is optional and unverified in the test suite (only its request formatting is tested).
- Roleplay matches answers by exact normalised comparison with the stored answers: a correct answer worded differently is judged incorrect. There is no fuzzy or semantic grading and no grammar analysis.
- Roleplay steps come from Phase 5 content, so most turns are "say this phrase"; free-form branching dialogue is not authored yet.
- The roleplay page has no microphone UI (the API accepts a transcribed speaking session).
- Parents do not see tutor or roleplay content.
- Frontend tests run the real page code in JavaScriptCore (macOS only); layout was not checked in a browser.

## 20. Phase 12: adaptive AI

Migration `0024_adaptive_ai.sql` (additive: eight tables and one index). **Principle: AI enhances stored learning data; it is never the source of truth.** Every statement, candidate and eligibility decision comes from stored rows through deterministic code; a model may only rank, reword, draft or (for roleplay) break a tie, and everything it returns is validated before it is stored or shown, with a deterministic fallback.

### Shape of every adaptive operation

1. **Read** (one short transaction): the learner's context and an *evidence bundle*: short, sourced facts (`e1`, `e2`, ...) built from stored rows: Phase 6 weaknesses, difficulty reading and confidence, recent accuracy per activity, roleplay results, progress, speaking counts.
2. **Decide by rules**: the candidates and the supported claims. Eligibility (level, age group, language, voice rules) is decided here.
3. **Ask a provider** with no transaction open, only to rank, reword or draft. Children only ever get the built-in provider.
4. **Validate** (`adaptive/validate.py`): only documented keys (an extra `xp`/`level` field invalidates the whole output), numbers in range (never booleans or NaN), plain link-free bounded text, no numbers that are not in the evidence, no word of an answer key the learner has not typed. Invalid output is dropped and an audit event (reason code only) is stored.
5. **Write** (one transaction): only validated content, with the evidence rows that justify it (`ai_evidence`).

### Provider abstraction

`ai.base.Provider` gains `semantic_grade`, `generate_micro_lesson`, `rewrite_insight`, `rank_recommendations` next to the Phase 11 methods. `MockProvider` (default, offline, deterministic) implements all of them; `LLMProvider` (opt-in, `AI_PROVIDER=llm` plus a configured key) implements them with JSON prompts in which learner text is always *data* (JSON-encoded, in the user role, never in the system prompt). A provider that lacks a capability raises and the caller falls back. Every call is bounded, timed out and validated.

### Semantic roleplay grading

Hierarchy, in this order: **(1)** the exact normalised match of Phase 11, unchanged; **(2)** the *deterministic semantic grader* (`adaptive/semantic.py`, a transparent rule-based comparison, no model); **(3)** an external grader, only for teens and adults, only when (2) scored in the uncertain band `[SEMANTIC_LLM_FLOOR, SEMANTIC_ACCEPT_AT)`, and only believed at `SEMANTIC_LLM_ACCEPT_AT` or more. An answer the deterministic grader scored below the floor is never sent to a model, so an injected "mark this correct" cannot reach one.

The grader compares the *key words* of an accepted answer (function words and polite address are ignored) with the learner's, allowing spelling variants, equivalent words (a small hand-written lexicon: Hindi, romanised and Devanagari), a one-letter slip in longer words and any word order. `coverage = matched / key words`; `confidence = coverage * (1 - 0.5 * extra_ratio)`, so listing every word you know cannot pass. Thresholds (`settings.py`): accept 0.80, close 0.50, external floor 0.66, external accept 0.85. A "close" answer is not accepted; the hint says how close in counts only ("1 key word missing"). Languages outside the lexicon are never guessed: only exact matching applies.

What a client learns about a grade: `method` (exact / semantic / semantic_llm / none), `confidence`, a counts-only explanation, `missing_objective` ("1 key word missing"), an optional word-order note. Never a word of the key; the hidden-answer rule of Phase 11 is unchanged. Each turn's grade is stored (`roleplay_turn_grades`).

**A model never decides a reward.** A step accepted *only* by an external grader counts for the roleplay's feedback but not toward the "at least half correct" rule that makes completion XP-eligible (`repositories/gamification.py`, one query condition). XP itself still comes only from the Phase 10 ledger.

### Recommendations, insights, micro-lessons, adaptive plan

* **Candidates (rules only):** the Phase 6 recommendations plus easier/harder practice (from the Phase 6 difficulty reading), listening practice (weak recent listening), speaking practice (only if voice is allowed for that learner and they have answered at least 10 questions), roleplay practice (after a lesson in that topic, never while the topic is weak), targeted-vocabulary drills (weak or repeatedly-missed phrases) and post-roleplay remediation. A model can reorder candidates, never add or drop one. The CEFR level is never touched.
* **Ranking:** deterministic by kind then an evidence-based boost (`adaptive/ranking.py`); an external ranker is validated (known ids, no duplicates, notes may only use numbers from that candidate's evidence) and any gaps are filled in rule order.
* **Insights:** deterministic templates over evidence (accuracy trend between two solid windows, repeated weakness, confidence-versus-accuracy gap, latest roleplay, practice gap). No evidence, no insight: the API says "not enough evidence". A provider may only reword, and the reworded text must contain exactly the original's numbers.
* **Micro-lessons:** supplemental drills in their own tables, never curriculum. Each is anchored to one canonical vocabulary item from the learner's *own reachable content*; distractors are other canonical items; the right answer must be the canonical one; the drill's evidence never quotes its answer. Shown only while validated, unexpired (7 days), in the learner's current language and for the age group they were made for. Answering awards no XP and changes no progress or weakness.
* **Adaptive plan:** the stored Phase 6 plan is left exactly as it is; its candidates are ranked and explained, with the plan's own task status alongside.
* **Tutor:** receives one stored, evidence-backed suggestion as a stored fact (the existing facts cap applies). **Roleplay:** semantic grading, targeted hints, and remediation drills after completion.

### Child safety

Children get the built-in provider only (enforced in the services, not the factory), deterministic template drills only (a database CHECK forbids a non-template generator for the child mode), the built-in grader, no speaking suggestion, no external model anywhere, and nothing about them in any request beyond mode, language, level and canonical content.

### API (learner role)

`GET /api/ai/recommendations`, `POST /api/ai/recommendations/{id}/apply` (idempotent; changes nothing but its own status), `GET /api/ai/insights`, `GET /api/ai/micro-lessons`, `POST /api/ai/micro-lessons/{id}/answer`, `GET /api/ai/adaptive-plan`; the roleplay turn and complete responses gain `grading` and `remediation`. 

### Measured quality of the deterministic grader

On `tests/semantic_cases.py` (110 hand-labelled cases over 15 real seeded phrases; labels were written before running the grader): 57 true positives, **0 false positives**, 4 false negatives, 49 true negatives, accuracy 96.4%, recall 93.4% on acceptable answers. The four misses are documented and pinned in the tests (a different verb form: `karo` for `kijiye`, `piyoge` for `piyenge`, `bulao` for `bulaiye`; and asking the price a different way). The set was written by the same author as the grader: it shows the grader does what it was designed to do, not that it generalises to everything a learner types.

### Limitations

- The default provider is rule-based; the real LLM paths are verified only for request shape and validation, not for answer quality.
- Semantic grading covers Hindi only (romanised and Devanagari) with a small hand-written lexicon; an English answer to a Hindi step is not accepted (no translation), and unusual verb forms are missed.
- Candidate generation is rule-based and limited to the kinds above; grammar-revision recommendations and pronunciation-based evidence were left out.
- Micro-lessons exist for canonical vocabulary phrases only.
- Frontend tests run the real page code in JavaScriptCore (macOS only); layout was not checked in a browser.


## 21. Phase 13: admin CMS and analytics

An admin-only layer to manage the curriculum safely and to see how learners are doing in aggregate. It is additive (one migration, no change to learner evidence), reuses the
layering of every earlier phase (router → service → repository → `db.connect()`), and is deliberately small: a whitelist of content, an archive-first lifecycle, one
immutable audit log, derived analytics, and a thin admin console.

### Shape

| Layer | Files |
|---|---|
| Router (the only new one) | `backend/routers/admin.py`: `APIRouter(prefix="/api/admin", dependencies=[admin_only, csrf_guard])`, mounted once in `main.py` |
| Security | `backend/admin/security.py` (`admin_only = require_roles("admin")`, `csrf_guard`, server-made `request_id`); a middleware in `main.py` adds `Cache-Control: no-store` to every `/api/admin/*` response (errors and 401/403 included) |
| Services (no HTTP, no SQL) | `audit.py`, `validators.py` (pure), `validation.py`, `cms.py` (lessons, exercises, vocabulary links), `cms_situations.py`, `cms_listening.py`, `cms_vocabulary.py` (vocabulary, translations, topics, reference data), `lifecycle.py`, `analytics.py`, `learners.py`, `health.py`, `rules.py`, `codes.py`, `errors.py`, `schemas.py` |
| Repositories (all SQL) | `admin_audit.py`, `admin_content.py` (snapshots, guarded writes), `admin_analytics.py`, `admin_learners.py` |
| Frontend | `frontend/admin.js`, `frontend/admin.css`; admin mode in `frontend/agemode.js`; one `views` entry and nav handling in `app.js` |

The older `GET /api/admin/users` (Phase 3, `routers/auth.py`) is unchanged. **It returns every account's email, handle and display name to an admin**, which an existing contract test
locks, so Phase 13 neither changes nor scans it; it is pinned in `tests/test_admin_privacy.py` and flagged as an open privacy decision (see Limitations).

### Migration 0025 (`0025_admin_cms.sql`, the only one)

* `admin_audit_log`: id, `occurred_at` (UTC), `actor_user_id` (FK → users, `ON DELETE SET NULL`), `actor_label` (the handle at the time), `action`, `entity_type`, `entity_id`,
  `entity_key`, `outcome` (`ok`/`rejected`), `meta_json` (valid JSON, at most 4096 **bytes**), `request_id`. CHECK whitelists for action and entity type; there is no `delete` action.
  Indexes on time, (entity_type, entity_id, time) and (actor, time). **Immutable:** triggers abort every UPDATE and every DELETE, with one exception that the foreign key itself needs:
  `actor_user_id` may go from a value to NULL (an account removed later) provided every other column is untouched, so the log still reads through `actor_label`.
* `lessons`, `situations`, `listening_activities` gain `published_at`, `archived_at`, `updated_at`, `revision INTEGER NOT NULL DEFAULT 1` (backfilled; published content stays published).
  `revision` is the optimistic-concurrency token. Triggers **stamp** `archived_at` whenever a row is archived (insert or update) without one, so "archived ⇒ has a time" always holds while
  the earlier phases' own bare `UPDATE … SET status='archived'` keeps working.
* **Delete protection** (triggers), derived from `PRAGMA foreign_key_list` and re-derived by a test that fails if a new cascade appears that nothing covers: lessons, situations, listening
  activities, exercises, situation steps, vocabulary items and topics cannot be deleted while learner evidence hangs off them (progress, attempts, roleplay sessions/turns, listening attempts,
  weaknesses, completed or skipped plan tasks). Two references are deliberately **not** guarded because earlier phases document and test them: a *pending* daily task is a plan row (it cascades with
  its lesson), and `SET NULL` context links keep the learner's own row. References that were already `RESTRICT` still refuse.
* Eight time-window indexes `(timestamp, user_id)` on the evidence tables. Every cross-learner window query was a `SCAN` before and is a `SEARCH` on a covering index now; a test asserts the plan for each.
* No analytics or rollup table: every metric is derived on demand.

### Content lifecycle

`draft → published → archived`. Allowed: draft→published (validated), published→draft (unpublish), draft→archived, published→archived, archived→draft (restore). **archived→published is refused:** restore, then publish through
validation again. Every transition needs the caller's current `revision` and bumps it. Published and archived content **cannot be edited** (409 `not_draft`): unpublish or restore first. An edit that changes nothing is not an
edit (no revision bump, no audit event). Nothing in the CMS deletes: there is no DELETE route, answers and options can be corrected but not removed, and evidence-bearing fields lock once learners have used them
(an answer a learner chose keeps its correctness and allows only typo-level text changes; an exercise, step or activity with attempts keeps its vocabulary item / mode / difficulty; vocabulary in use keeps its CEFR level, kind, and
the meaning of its text). Learner visibility is unchanged: the existing `status = 'published'` filters, CEFR rank, age targeting and language decide, so a draft, an unpublished or an archived unit is simply not selectable.
Learner evidence is never written by the CMS, and archiving leaves progress, attempts, XP, weaknesses and plan rows byte-identical (tested).

### Validation

One set of pure functions (`validators.py`) over snapshots loaded by the repository powers the dry run (`POST /validate/{type}/{id}`), the publish gate (inside the publish transaction) and the integrity sweep
(`GET /validate/all`, also `GET /health/integrity`), so they cannot disagree. A finding is `{code, severity, entity, message}`; errors block publication, warnings do not. Rules: lessons need an exercise, a topic and
vocabulary; multiple-choice needs 2+ answers with exactly one correct; typed exercises need an accepted answer and no incorrect rows; situations need steps with the same answer rules; listening needs exactly
three options and the target among them with no duplicate option text; every vocabulary item used needs an **English** translation and a CEFR rank not above the unit's; age targeting must name real groups once (empty means universal);
no duplicate answers (the way the graders compare them) or exercise prompts; control characters and bad slugs are refused; lifecycle state must be consistent; dependencies must be published (the 0001–0025 schema has no
status-bearing dependency below a lesson, so that rule is exercised on synthetic snapshots only). The sweep adds whole-database checks (SQLite integrity, dangling foreign keys, orphan vocabulary and topics).
The seeded curriculum passes with zero errors. Service-level rules (shapes, language consistency, revisions, uniqueness) run on every write; DB constraints stay as before.

### Audit log

`audit.record(conn, actor, …)` runs on the caller's connection, so the event and the change commit or roll back together (a failing audit write rolls the change back; tested for every kind of write). The actor is the
authenticated user object: there is no parameter a request body could use. Metadata is a closed allow-list with typed values: revisions, `changed_fields` drawn from a fixed list of field **names**, `finding_codes` drawn from the
fixed catalogue, statuses. Answer text, learner content, tokens and keys cannot be logged because nothing else is accepted. A refused publish is recorded as `validation_failed` / `rejected` on its own connection after the rollback.
`config_change` and `login_denied` are reserved (Phase 13 has no admin configuration and does not log denied sessions, which any learner could otherwise flood). Reading the log writes nothing.

### Analytics (derived; never stored)

Learners are users with the learner role, no admin role, and not `demo-alex`. Time is UTC; a window is whole UTC days, `from` and `to` inclusive, at most 365 days (7d/30d/90d on the dashboard). A learner is **active** on a day if any of eight kinds
of learning evidence exists that day (exercise, situation-step and listening attempts; recorded speaking sessions; pronunciation assessments; roleplay turns; micro-lesson attempts; XP events). A login is never activity.

| Metric | Source | Definition |
|---|---|---|
| total / new / active learners | `users`, evidence union | learners; created in window; active in window |
| DAU / WAU / MAU | evidence union | distinct active learners on the end date / the 7 / the 30 days ending on it |
| language, CEFR, age-group distribution | `learner_profiles` (+ `age_groups`) | learners by target language / level / age **band** derived from the date of birth, which never leaves the query |
| lesson, situation completion | `lesson_progress`, `situation_progress` | completed ÷ started, for units **started** in the window |
| exercise accuracy, listening accuracy | `learner_attempts` view | correct attempts ÷ attempts in the window (attempt-level) |
| speaking participation | `speaking_sessions` | learners with a recorded speaking session ÷ active learners |
| pronunciation usage | `pronunciation_assessments` | attempts of any outcome and the learners; usage only, no score is read |
| roleplay success | `roleplay_sessions` | completed sessions with no missed step ÷ completed sessions |
| confidence vs measured | `confidence_scores` (self-reports), `learner_attempt_topics` | per topic: mean latest self-report vs mean per-learner accuracy, for learners with both |
| weakness distribution | `weaknesses` | active weaknesses by rule and by topic, as of now |
| adaptive usage | `ai_recommendations`, `ai_micro_lessons`, `ai_micro_lesson_attempts` | recommendations shown and applied; micro-lessons made, attempted, accuracy |
| XP, streak, achievement, challenge activity | `xp_events`, `streak_days`, `learner_achievements`, `learner_challenges` | totals, learners, claim rate |
| content performance | `learner_attempts` + unit tables | per unit: attempts, learners, accuracy, completion; a review flag at 30+ attempts and accuracy below 20% or above 98% |

Rules for every figure: an empty denominator is `null` with status `no_data` (never 0) and shows numerator and denominator when it is shown; **fewer than 5 learners behind a figure suppresses it** (value, numerator and denominator
are withheld; a count of exactly zero involves nobody and is shown); a rate whose numerator is itself a count of learners is also suppressed when that count is 1–4; breakdowns fold small buckets into `other` (measured as a *set*, so a
learner in two folded buckets counts once) and, if `other` is still too small, the smallest visible bucket joins it, so a hidden bucket cannot be recovered by subtraction. Not offered, because the schema cannot support them: session duration,
time on task, retention cohorts, pronunciation quality, tutor answer quality. A test recomputes figures from real learner API activity and compares them with what the learners themselves see.

### Admin security and privacy

Every `/api/admin/*` route sits behind `require_roles("admin")` (401 anonymous, 403 learner, parent and the demo learner), enumerated from the route table by a test that fails for any unguarded route. Every state-changing request needs
`Content-Type: application/json` **and** `X-Requested-With: XMLHttpRequest` (403 otherwise; authentication is checked first). Responses are explicit Pydantic allow-lists and `no-store`. Admins have no access to learner or parent
routes and there is **no impersonation** (no route, no session issued for a learner; tested). Learners appear only as an opaque reference, an HMAC of the id under `ADMIN_REF_SECRET` (or a per-process random key), and the list and detail views
are withheld below 5 learners; attributes shared by fewer than 5 learners are shown as null. Health reports provider configuration as booleans only. A canary test plants markers for tutor messages, transcripts, emails, password hashes,
session tokens, recording references, roleplay text, parent emails, dates of birth, API keys and paths, then requests every admin GET endpoint and fails if any marker or forbidden key appears.

### Frontend

`#/admin`, `#/admin/curriculum[/lessons|situations|listening[/:id]|vocabulary|topics]`, `#/admin/analytics`, `#/admin/learners[/:ref]`, `#/admin/audit`, `#/admin/health`. An account with the admin role gets `AdminView.NAV` and nothing else (admin
mode in `agemode.js`); anyone else asking for `#/admin` is sent to their own home once their role is known (the server refuses their API calls regardless: the guard is UX only). All page state is in the URL query, so filters, pagination
and windows are refresh-safe. Loading, empty, error (with retry) and forbidden states everywhere; inline-SVG charts; tables, filters and pagination; a publish workflow that shows validation findings; a confirmation before archiving;
revision conflicts offer "Reload latest". All server text is HTML-escaped. There is no delete control and no code path that sends DELETE.

### Testing

New test modules cover the migration, authorization (every route × every caller), CSRF, audit, validators (one case per rule, plus a catalogue-coverage test), validation through the API, each CMS entity, the lifecycle and learner
visibility, analytics (rules, correctness, boundaries, suppression, agreement with learner-facing numbers), learner overview, health, privacy canaries and the admin frontend (the real page code in JavaScriptCore against a live server).
Mutation testing (exact-pattern replacement with byte-identical restore) targeted authorization, CSRF, validators, publish guards, visibility, analytics filters, audit attribution, revision and archive protection, privacy and
delete protection. Final run: **326 mutants, 325 killed, 1 equivalent, 0 genuine survivors** (migration 30, authorization/CSRF/audit 21, validators 82, lifecycle/CMS rules/visibility 110, analytics/learners/health/privacy 63, admin frontend 20). Several mutants first survived and each exposed a missing assertion that was then added (revision races, conflict causes, WAU/MAU edges, small-cell edges, refused-publish audit codes). The one equivalent mutant removes the outer `source = 'self_report'` filter in the confidence query: the row is already pinned to a self-report by the `c.id = (SELECT … c2.source = 'self_report' …)` condition, so the outer filter cannot change any result.

### Limitations

- `GET /api/admin/users` (Phase 3) still returns emails, handles and display names of every account to an admin. It is outside the new surface and left untouched; narrowing it needs a decision (it is locked by an existing test).
- A daily plan generated before a lesson is archived still names that lesson (its title stays readable; opening it is refused and tomorrow's plan omits it). Plan rows are a record, not live content.
- Learner attempt responses still reveal the correct answer after an attempt (earlier phases' tested design); only content *reads* never carry the key.
- Vocabulary and topics have no revision token (last write wins); units use `revision`.
- Position changes inside a unit (exercises, steps, options) must use a free position; there is no swap.
- Analytics are computed on demand with no cache; a very large installation would want rollups (deliberately not built).
- References change on restart unless `ADMIN_REF_SECRET` is set.
- Frontend tests run in JavaScriptCore on macOS only; layout was not checked in a browser.

### Deferred (not built, by design)

2FA and any admin sign-in hardening (admins remain CLI-created), hints, content version history/diff/rollback, bulk import/export and analytics CSV, audio upload/asset management, scheduled publishing, session-duration analytics and
retention cohorts, learner impersonation (excluded permanently), AI-authored curriculum, new AI models, pronunciation-model changes, new semantic grading, advanced parent analytics, new social or gamification features, mobile/offline, camera vocabulary, a knowledge graph, and Phase 14.


## 22. Phase 14A: legacy attack-surface lockdown

The first step of Phase 14 (security). It closes the prototype-era surfaces the Phase 14 audit found exploitable, with no schema change (no migration) and nothing from later Phase 14 steps (2FA, sessions, CSRF, headers, throttling).

### Legacy state (`/api/state/{handle}`, `frontend/engine.js`)

- **No shared state.** `authorize_state_access` no longer has a demo exception: a signed-in user reads and writes only their own handle's state (403 for any other, 401 anonymous), in every `DEMO_MODE`. A `demo-alex` row left in an existing database is kept but never served.
- **The frontend follows the account.** `engine.js` no longer hard-codes a user. `Engine.hydrate()` asks `/api/auth/me`: anonymous visitors keep their state in `localStorage` only (no server request at all); a signed-in user's state is synced to `/api/state/<their handle>`, and the server copy wins on load. Each identity has its own `localStorage` key (`llb-state-v1` anonymous, `llb-state-v1:<handle>` per account), so signing in never uploads the anonymous visitor's progress and signing out never shows the account's. `profile.js` calls `Engine.hydrate()` after signing in, registering and signing out.
- **What may be stored** (`backend/legacy/state.py`): the raw body is limited to `LEGACY_STATE_MAX_BYTES` (64 KB; larger is 413, read in chunks and never truncated); it must be a JSON object with `v` exactly 1; only the keys the frontend writes are accepted, each with its expected type (text lengths, CEFR codes from the database, 0–100 percentages, whole-number counters, bounded lists and maps). Anything else is a 422 and nothing is stored.
- **Rendering.** Every place `app.js` puts a saved-state value into markup was checked: text values are escaped (`esc`), values used as numbers are forced to be numbers (`num`: anything else shows as 0, so nothing can reach text, an attribute or a style), and the tutor message topic that goes into an `onclick` is used only if it is one of the known topic keys.

### Legacy AI (`POST /api/ai`, `backend/legacy/ai.py`)

- **Who reaches the model:** an anonymous visitor only if `DEMO_LIVE_AI=1` (default off); a signed-in learner only if their profile puts them in the teen or adult group. A child never does (whatever `DEMO_LIVE_AI` says), and neither does a learner without a profile (age unknown), a parent or an admin; they all get `{"ok": false, "reason": "offline"}` and the built-in engine answers, as before.
- **What reaches it:** a strict body (`extra` fields refused). The roleplay scene is sent by id (`auto`, `food`, ...) and its text comes from the server's copy of the legacy scenes, never from the client; `city` and `level` must exist in the database; `language` is one of two labels; at most `LEGACY_AI_MAX_HISTORY` (12) messages of at most `LEGACY_AI_MAX_MESSAGE_CHARS` (500) characters. Anything larger or different is a 422, never truncated; a body that is not a JSON object is a 422, never a 500.
- **Failures:** the provider call is bounded by `AI_TIMEOUT_SECONDS`; any failure (timeout, provider error, unusable reply) is `{"ok": false, "reason": "unavailable"}` with no exception name, message, path or provider detail. Only the exception type goes to the server log.
- **Rate limit:** `LEGACY_AI_MAX_REQUESTS` (20) requests per caller per `LEGACY_AI_WINDOW_SECONDS` (60), keyed by user, or by client address when anonymous, then 429 with `Retry-After`. Like the login throttle it is per process; it remembers at most `LEGACY_AI_MAX_TRACKED_CALLERS` callers.

### Date of birth while a parent is linked (`backend/learner/service.py`)

A learner with at least one parent link cannot save a date of birth that moves them into another age group (409). Edits inside the same group, other profile changes, a first profile and unlinked learners are unaffected; once every parent has unlinked, the change is allowed. Growing up by time passing is unaffected. No parent notification yet.

### Tests and provider safety

`tests/conftest.py` blanks every provider variable before `backend.main` is imported, so a developer's real `.env` key is never loaded by tests or by the test servers the frontend tests start, and an autouse fixture replaces `main.call_llm` with one that fails loudly. Tests that want a model stub it themselves. `tests/test_legacy_hardening.py` (backend) and `tests/test_legacy_frontend.py` with `tests/frontend/legacy_harness.js` (the real `engine.js` and `app.js` in JavaScriptCore) were run against the pre-14A code as well: every security test fails there (the ones that pass there are the "legitimate use still works" checks). Focused mutation run: **93 mutants, 93 killed, 0 equivalent, 0 survivors** (state authorization 2, state size and validation 25, AI gates 8, AI bounds 16, AI error handling 3, rate limit 10, date-of-birth lock 6, frontend escaping 12, frontend identity and AI payload 11). The first run left 6 survivors, each a missing assertion that was then added: the limits stated as literal numbers rather than read back from settings, non-finite numbers in fields without a range, a declared Content-Length over the limit, and the account's server copy winning over an older copy in the browser.

### Compatibility

- Anonymous visitors no longer share or sync a server-side state; existing anonymous `localStorage` state keeps working.
- A signed-in user's state now loads from the server first; a state with unknown keys or wrong types is refused on write.
- Parents, admins and learners without a profile now get the offline engine from the legacy `/api/ai` (previously any caller reached the model).
- The legacy frontend sends the roleplay scene by id; an older client that sends the scene object gets a 422 and falls back to the offline engine.

### Deferred to later Phase 14 steps

Session hardening, password change, 2FA (TOTP, AES-GCM secret storage, a vendored QR encoder), security events, login and registration throttling, and narrowing `GET /api/admin/users`. (The global CSRF guard and security headers followed in 14B, section 23; sessions, password change and throttling in 14C, section 24; 2FA in 14D, section 25; security events and admin privacy in 14E, section 26.)


## 23. Phase 14B: global CSRF guard and security headers

Closes audit findings F3 (no CSRF protection outside `/api/admin`) and F4 (no security headers). One HTTP middleware in `backend/main.py` (`browser_security`) runs on every request before any route; the rules live in `backend/security/csrf.py` and `backend/security/headers.py`. No schema change.

### Browser-request (CSRF) policy

Every state-changing request (`POST`, `PUT`, `PATCH`, `DELETE`), on any path, must carry:

- `X-Requested-With: XMLHttpRequest` (exact value), and
- `Content-Type: application/json` (parameters such as `; charset=utf-8` allowed), with or without a body.

A cross-site page cannot make a browser send a custom header or a JSON content type without a CORS preflight, and the app grants no CORS (there is no CORS middleware; a test pins that no `Access-Control-Allow-Origin` is ever sent). So a forged form post, a body-less `POST` (the audit's `POST /api/profile/parent-link-code` bypass), a `text/plain` "JSON" post, `<img>`, `fetch(mode: "no-cors")` and `sendBeacon` are all refused, even though the `SameSite=Lax` session cookie may come along. Safe methods (`GET`, `HEAD`, `OPTIONS`) are never refused by the guard.

**Origin.** When a write names an `Origin`, it must be one of this application's own origins, otherwise it is refused. `null` is refused too. The own origins are `TRUSTED_ORIGINS` (comma-separated, for a proxy that rewrites `Host`) when set. Otherwise they are the request's own scheme and `Host`, plus `https://<Host>` when `COOKIE_SECURE=1` (a TLS-terminating proxy usually forwards plain HTTP). A browser always sends the real `Host` of the site it talks to, so matching against `Host` accepts only this site. No production hostname is hard-coded.

**Referer** is a secondary signal: only when there is no `Origin`, a `Referer` from another origin (or one that is not an http(s) URL) is refused. A write with neither header still has to pass the header rules: a missing `Origin` is never a bypass.

**Raw media.** The only route that takes a non-JSON body is `POST /api/speaking/sessions/{id}/recording` (listed by method and anchored path in `RAW_MEDIA`). It still requires `X-Requested-With`, which on its own already forces a preflight. The route keeps its own media check (audio allow-list plus leading-byte signature, 415 otherwise). Every other route refuses a non-JSON write, `audio/*` included.

**Refusals** are `403` JSON responses whose `detail` starts with `CSRF check failed:`. They carry the same security headers as any other response, and name only what to send, never internals. The global guard runs before authentication, so an unsignalled write is refused as CSRF even when anonymous. With the signal, authentication and roles decide as before. The admin router keeps its own `csrf_guard` dependency as a second layer. Because the global guard is at least as strict on every admin route, that layer can no longer refuse anything itself (see mutation testing below).

**Authentication endpoints** follow the same rule. The frontend's login, registration and logout go through `api()` and send the signal, and a cross-site login (login CSRF) or registration is refused.

**No synchronizer tokens** (deferred, as the audit recommended).

### Frontend

The central helper `LBApi.api()` (`frontend/profile.js`, used by every learner, parent, social, AI and adaptive page) sends `X-Requested-With` and `Content-Type: application/json` on every non-GET call, with or without a body. Three other places write directly, and send the same: `admin.js` (unchanged, it already did), `engine.js` (legacy state sync and `/api/ai`, `WRITE_HEADERS`), and `voice.js` (the recording upload: its audio `Content-Type` plus `X-Requested-With`). A test pins that no other frontend module calls `fetch` with a method.

### Security headers (every response: pages, static files, API, 4xx, CSRF refusals)

| Header | Value |
|---|---|
| `X-Content-Type-Options` | `nosniff` |
| `X-Frame-Options` | `DENY` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Content-Security-Policy` | `object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'` |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains`, only when the request arrived over HTTPS or `COOKIE_SECURE=1`, so local plain-HTTP development is never pinned to HTTPS |

An unhandled exception's 500 is produced outside the middleware and carries none of these.

**CSP decision.** The CSP restricts only what the current frontend provably does not use: plugins (`<object>`), `<base>`, being framed, and form submission to other sites (the two composer forms call `preventDefault()`). `script-src` and `style-src` are **not** restricted. The prototype renders through `innerHTML` with 54 inline event handlers (`onclick=`, `onsubmit=`, `onkeydown=` in `app.js`) and inline `style` attributes. A `script-src` without `'unsafe-inline'` would break it, and one with `'unsafe-inline'` would add little. Removing the inline handlers so a strict, nonce-based `script-src` can be set is deferred. It is a frontend rewrite, not a header change.

### Cache policy

Every `/api` response is `Cache-Control: no-store`, errors included: API answers are per-user, session-dependent or security-sensitive, and the few public ones (health, languages, cities) are cheap. This replaces the Phase 13 middleware that did it for `/api/admin` only. Pages (`/`) and static files keep the default caching behaviour.

### Tests

`tests/test_csrf_security.py` (292 tests):

- every one of the 59 unsafe routes, taken from the app's OpenAPI document, refuses an unsignalled write from a signed-in browser and from an anonymous one;
- every GET route is never refused, even with a foreign `Origin`;
- header combinations, exact values and content types;
- body-less writes (parent link code, friend code, daily plan, logout);
- Origin, Referer, `COOKIE_SECURE` and `TRUSTED_ORIGINS` handling;
- the audio upload: allowed with the signal, refused without it or from a foreign origin, and the route's own 415 preserved;
- admin writes;
- register, login and logout, plus login CSRF and cross-site registration;
- nine end-to-end attacks, each checked for its effect on the database;
- the headers on HTML, static, public, authenticated, admin, 404, 405, 401, 422 and CSRF responses;
- HSTS over HTTP, with `COOKIE_SECURE`, and over HTTPS;
- `no-store` on login, register, me, state, profile, parent, admin, errors and logout, and not on pages or static files.

The legacy frontend harness now also checks that the real frontend's login, logout, state sync and AI calls carry the signal. All the existing frontend harnesses (tutor, roleplay, adaptive, kids, parent, gamification, voice upload, admin) run against the guarded server.

The test "browsers" (`client`, `client2`, `conftest.browser()`) send the frontend's headers by default. Tests about the guard itself use a bare `TestClient(main.app)`, which sends neither.

Intentional test changes:

- `test_admin_security.py` no longer expects authentication to be checked before CSRF. The global guard answers first, and the test now checks both orders' outcomes.
- The Phase 13 test that non-admin API routes are *not* `no-store` now checks the opposite, and that pages and static files still are not.

**Mutation testing:** 62 mutants, 62 killed, 0 equivalent, 0 survivors.

| Area | Mutants |
|---|---|
| Guard on/off, methods, header and content-type checks | 14 |
| Origin, Referer, `COOKIE_SECURE`, `TRUSTED_ORIGINS` | 16 |
| Raw-media route | 5 |
| Refusal shape | 3 |
| Admin router guard | 1 |
| Headers, HSTS and cache | 18 |
| Frontend helpers | 5 |

The first run left three survivors, each a missing assertion that was then added:
- a mixed-case `Content-Type`;
- a mixed-case `TRUSTED_ORIGINS` entry;
- a non-http(s) Referer that only a misconfigured trusted origin could ever match.

Disabling the admin router's own `csrf_guard` is killed by its direct unit test, not by any HTTP test: over HTTP the global guard refuses everything that guard would.


## 24. Phase 14C: sessions, password change and authentication throttling

Closes audit findings F5 (a weak, unbounded login throttle and no registration throttle) and F8 (no password change, no logout-all, no session list, no idle timeout, sign-in did not deal with the session already in the browser). One additive migration, `0026_session_hardening.sql`. No 2FA yet (14D).

### Session model

A session is a random 256-bit token in the `llb_session` cookie. The database keeps only its SHA-256, as before, plus:

| Column (0026) | Meaning |
|---|---|
| `public_id` | 32 random lowercase hex characters, unique. The only way a session is named outside the server (listing, revoking). |
| `last_seen_at` | Last use, server-written. |
| `auth_method` | `'password'` today. The CHECK already allows the 14D values (`'password+totp'`, `'password+recovery'`), so 14D needs no table rebuild. |
| `mfa_level` | `0` today, reserved for 14D. |

Triggers enforce what `ALTER TABLE` cannot express:

- a new row needs a well-formed `public_id` and a `last_seen_at` within its lifetime;
- an existing row's user, token hash, public id, creation, expiry, method and level never change;
- `last_seen_at` only moves forward and never past the expiry.

Rotation is therefore always a new row, and revocation always a deletion: a revoked token simply no longer exists. Existing sessions are kept by the migration and backfilled with `last_seen_at = created_at`, so one already unused for longer than the idle timeout ends at its next use.

### Lifecycle

- **Sign-in and registration** always issue a fresh token. The session the browser presented, whoever's it was, is revoked in the same transaction, so a session never changes hands and an attacker-planted cookie never becomes valid (session fixation). Several sessions per account may coexist (several devices).
- **Absolute lifetime:** `SESSION_TTL_DAYS` (7) after sign-in. It is never extended by activity, and the cookie's `Max-Age` matches.
- **Idle timeout:** `SESSION_IDLE_MINUTES` (default 30, bounded 1 minute to 7 days).
  - A session whose `last_seen_at` is at least that old is refused and deleted when presented.
  - `last_seen_at` is updated by the server, only for a valid session, and only when it is at least `SESSION_TOUCH_SECONDS` (60) old. That keeps SQLite free of a write per request.
  - Because of that, a session can end up to a minute earlier than 30 minutes after its very last request.
  - Requests that do not look up a session (public endpoints, unknown tokens) never touch it, and nothing a client sends can set it.
- **Logout** (`POST /api/auth/logout`) deletes the current session.
- **`POST /api/auth/logout-all`** deletes every *other* session of the account and keeps the current one: `{"ok": true, "revoked": n}`.
- **`GET /api/auth/sessions`** lists the account's live sessions: `id` (the public id), `created_at`, `last_seen_at`, `expires_at`, `auth_method`, `current`. It never includes the token, its hash or the row id. `current` comes from the cookie the request was made with, never from anything the client sends.
- **`DELETE /api/auth/sessions/{id}`** revokes one of the account's own sessions (`{"ok": true, "current": bool}`). Revoking the current session also clears the cookie. Any id that is not the caller's own, someone else's included, is the same `404 {"detail": "Not found"}`.
- Every account manages only its own sessions, learners, parents and admins alike. There is no endpoint that reaches another account's sessions, and no impersonation.

### Password change (`POST /api/auth/password`)

- **Body:** `{current_password, new_password}` only. The account is the session's, and any other field is a 422.
- **Wrong current password:** a generic `403 "The current password is not correct"`. Nothing changes.
- **On success, in one transaction:** the new scrypt hash (the existing `passwords.py` format and parameters) is stored, every session of the account is deleted, and one fresh session is issued in a new cookie. The old cookie, every other device's session, and the old password all stop working at once.
- **Policy** (new passwords and registration): 8 to 128 characters, any Unicode, not only whitespace. Passwords are used exactly as typed (never trimmed), never logged, never echoed in errors (the Phase 2 validation handler strips input), and never returned.
- Password reset by e-mail does not exist (no e-mail infrastructure).

### Throttling (`backend/auth/throttle.py`)

Sliding-window limiters, in memory per process:

| Limiter | Key | Counts | Limit (default) | Window |
|---|---|---|---|---|
| `login_account` | normalised email (known or not) | failed sign-ins, from any address | `LOGIN_ACCOUNT_MAX_FAILURES` 5 | 15 min |
| `login_ip` | client address | failed sign-ins, for any accounts | `LOGIN_IP_MAX_FAILURES` 20 | 15 min |
| `register_ip` | client address | every registration attempt | `REGISTER_IP_MAX` 30 | 60 min |
| `password_change` | user id | wrong current passwords | `PASSWORD_CHANGE_MAX_FAILURES` 5 | 15 min |

- **What a refusal looks like:** a `429` with `Retry-After`, the exact whole seconds until the oldest counted event leaves the window. The check comes before any work, so a throttled sign-in does no password hashing.
- **Counted before the check (Phase 14F):** each attempt is checked and counted in one locked step (`Limiter.acquire`) *before* the password is verified, and given back (`release` / `clear`) when the password was right. Before 14F, concurrent guesses all passed the check before any was counted (section 27, DEFECT-2/3).
- **A successful sign-in clears only the account's count, never the address's.** Otherwise an attacker holding one real account could reset their address between guesses at others. A successful password change clears that user's count.
- **Rotating emails or addresses doesn't help:** many emails from one address hit `login_ip`, and many addresses against one account hit `login_account`.
- **Lock-out risk (accepted):** guessing at an account can lock its owner out for up to 15 minutes. That is the cost of stopping distributed guessing.
- **Memory is bounded:** each limiter remembers at most `THROTTLE_MAX_KEYS` (10,000) keys. When a new key would exceed that, keys whose window has passed are dropped first, then the longest-remembered ones. Merely checking a key never stores it.
- **Overriding limits:** each limit can be raised or lowered through an environment variable of the same name (`REGISTER_IP_MAX=200` for a classroom behind one public address). Invalid or non-positive values are ignored.
- **Known limitation:** the limiters are per process and reset on restart. Several workers multiply every limit, and behind a proxy every client may share the proxy's address. A shared store would be needed for that.
- **No separate admin limits:** admins use the same limits as everyone. Admin-specific thresholds would reveal which accounts are admins. Stronger admin sign-in comes with 2FA (14D).

### Account enumeration

- Sign-in failures are identical for unknown emails and wrong passwords. Same response, same throttle, and the dummy scrypt hash is still verified for unknown emails.
- Throttled responses are identical too.
- Session ids of other accounts are indistinguishable from unknown ones.
- **Kept, deliberately:** registration still answers `409 "That email is already registered"`. Without e-mail verification, hiding it would leave a person who mistyped unable to tell why they cannot sign in. Every probe counts against `register_ip`, which bounds how fast it can be used.

### Cookies

The session cookie is unchanged and re-checked on every place that sets it (registration, sign-in, password change, logout):

- `HttpOnly`, `SameSite=Lax` and `Path=/`;
- `Max-Age` equal to the absolute lifetime;
- `Secure` exactly when `COOKIE_SECURE=1`, so local plain-HTTP development keeps working.

The token never appears in a response body or in JavaScript-readable storage.

### Frontend

There is no new UI yet: password change, the session list and logout-all are API-only until the frontend step. An idle-expired session behaves like any signed-out one: pages show their existing "sign in" states.

### Tests

- **`tests/test_session_security.py`** covers:
  - sign-in rotation and fixation, concurrent sessions, logout, logout-all, listing (safe fields, the current flag from the cookie), and revocation (own, current, foreign, forged, malformed);
  - the idle boundary at exactly 30 minutes, configurable idle, the bounded `last_seen_at` writes, no client control, the absolute lifetime under constant use, and no revival;
  - password change (wrong and right current password, rotation, other sessions, the policy table, Unicode, untrimmed spaces, no account fields, throttling);
  - layered sign-in throttling (stuffing from one address, one account from many addresses, identical treatment of unknown accounts, success resetting only the account, exact `Retry-After`, no hashing when throttled, the dummy hash when unknown, bounded and stale-first memory, environment overrides) and registration throttling;
  - authorization for learners, parents and admins, fourteen named attack tests, and the cookie flags.
- **`tests/test_session_migration.py`** covers 0026 on a clean database, idempotency, that only `sessions` changes, existing sessions surviving the upgrade with their backfill, and every trigger rule.
- **Existing tests that changed on purpose:**
  - the Phase 13 and migration-history tests now expect 0026 as the last migration;
  - the migration upgrade tests write pre-0026 sessions directly into the old schemas;
  - the absolute-lifetime test lifts the idle timeout to isolate what it tests;
  - the admin helper that plants a demo-learner session now plants a fresh one;
  - the frontend test servers, which stand in for many people behind 127.0.0.1, raise only their per-address limits through the documented environment override.
  - fixtures that planted sessions with raw pre-0026 SQL now use the session repository.

**Mutation testing:** 58 mutants, 58 killed, 0 equivalent, 0 survivors.

| Area | Mutants |
|---|---|
| Sessions | 21 |
| Password change | 11 |
| Throttling | 18 |
| Cookies | 3 |
| Migration triggers and backfill | 5 |

The first runs left five survivors, each a weak test that was then fixed:
- **Absolute lifetime (2 mutants).** The test reached the 7-day mark only after a gap longer than its own idle limit, so the idle timeout, not the absolute expiry, was what ended the session.
- **Idle-session listing.** The listing test signed in on a new browser first, and sign-in cleans idle sessions, so the listing filter itself was never exercised.
- **Eviction order.** The oldest key was also the stale one, so the order didn't matter in the test.
- **Session owner.** The ownership trigger was tested by moving a session to a user that did not exist, so the foreign key refused it before the trigger could.


## 25. Phase 14D: TOTP two-factor authentication and admin MFA

The last step of Phase 14's authentication work. One additive migration, `0027_two_factor.sql` (new tables only). No WebAuthn, SMS, e-mail codes or password reset.

### TOTP

Implemented locally with the standard library (`backend/auth/totp.py`), RFC 6238:

| Parameter | Value |
|---|---|
| Algorithm | HMAC-SHA1 |
| Code | 6 digits |
| Step | 30 seconds |
| Secret | 160-bit random |
| Clock drift | the previous and the next step are also accepted (±1), never further |

- Time is whole UNIX seconds, and the step is `seconds // 30` (no floating point).
- A code must be exactly six ASCII digits. Spaces, other scripts' digits and other lengths are refused before any comparison.
- Every candidate step is compared with `hmac.compare_digest`.
- The RFC 6238 Appendix B SHA-1 vectors pass.

### Secret storage (`backend/auth/totp_crypto.py`)

- **Encryption:** AES-256-GCM via the `cryptography` package (a new dependency in `requirements.txt`). Each encryption uses a fresh 96-bit nonce.
- **What is stored:** the database holds only the 36-byte ciphertext (the secret plus GCM's 128-bit tag) and the 12-byte nonce. Both lengths are CHECK constraints.
- **Bound to the account:** the associated data is `lingobuddy/totp-secret/v1/user/<id>`, so a ciphertext copied onto another account does not decrypt.
- **`TOTP_ENC_KEY`:** exactly 32 bytes, base64url-encoded (43 characters, an optional trailing `=`). Generate one with `python -c "import secrets,base64;print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())"`. It is read from the environment on every use and never generated, stored, logged or returned.
- **Missing or malformed key (fail closed):**
  - 2FA cannot be set up (503), and `GET /api/auth/2fa` reports `available: false`.
  - Existing codes cannot be checked: sign-in with a code answers 503.
  - Recovery codes still work, because they do not depend on the key.
- **Changed key or tampered row:** the same outcome as a missing key. **Losing the key means every user signs in with recovery codes and sets 2FA up again.** Back the key up like a password database.

### Setup

1. **`POST /api/auth/2fa/setup {password}`** (signed in). The current password is required, so a stolen session alone cannot enrol an attacker's authenticator. It stores a pending, encrypted secret for `TOTP_SETUP_SECONDS` (10 min); a new setup replaces an older pending one. It returns, once, `{secret, otpauth_uri, qr, expires_in_seconds}`.
   - `otpauth://totp/LingoBuddy:<email>?secret=<base32>&issuer=LingoBuddy&algorithm=SHA1&digits=6&period=30`, with every label part percent-encoded. It contains no user id, token or password.
   - `qr` is the QR module matrix of exactly that URI, made by the vendored encoder.
   - The manual key is always shown, with a Copy button.
2. **`POST /api/auth/2fa/confirm {code}`** turns it on and returns 10 recovery codes once. This browser's session is replaced by a new one with `mfa_level 1`. Other existing sessions keep their level (0), and nothing turns an older session into an MFA one.
3. Once 2FA is on, the secret is never returned again, and a new setup is refused (409).

### QR code

- **Encoder:** Project Nayuki's QR Code generator 1.8.0, vendored unmodified as `backend/vendor/qrcodegen.py` (MIT; source, licence and SHA-256 in `backend/vendor/README.md`). It is pure Python, with no network, CDN or image service.
- **Rendering:** the API returns a matrix of `0`/`1` rows. `frontend/twofactor.js` validates it and draws an SVG from numbers only, so nothing in it can be markup. If the picture cannot be made, setup continues with the manual key.
- **Tests:** an independent test decoder (`tests/qr_decode.py`) reads the matrix back and checks the payload is byte-for-byte the `otpauth://` URI.

### Signing in

For an account with 2FA:
- **Password step:** a correct password creates **no session**. `POST /api/auth/login` answers `{"mfa_required": true}` and nothing about the account. It sets a separate `llb_mfa_challenge` cookie: an opaque random token (only its SHA-256 is stored), HttpOnly, SameSite=Lax, Secure when `COOKIE_SECURE=1`, `Max-Age` 300, and `Path=/api/auth/2fa`, so it is sent nowhere else. It can never authenticate a request.
- **Code step:** `POST /api/auth/2fa/verify {code}` or `{recovery_code}` (exactly one).
  - The challenge must be unexpired (`MFA_CHALLENGE_SECONDS`, 5 min), not completed, and have attempts left (`MFA_CHALLENGE_MAX_ATTEMPTS`, 5).
  - Only success creates the session, with `mfa_level 1` and `auth_method` `password+totp` or `password+recovery`. The session this browser presented is revoked, the challenge is completed and its cookie cleared.
  - A wrong code is a generic 401 and counts. An unusable challenge is a 401 asking to sign in again.
- **Replay:** a code is accepted only for a time step strictly later than the credential's `last_used_step`. A recovery code can be spent once.
  - Both checks are conditional UPDATEs inside the transaction that creates the session, so concurrent requests with the same code cannot both succeed. A test races four.
  - The schema adds a second line of defence: `last_used_step` only increases, a spent code cannot be unspent, and a challenge completes once.

### Recovery codes

- **Format:** 10 per account, each 80 random bits (16 base32 characters, shown `XXXX-XXXX-XXXX-XXXX`; case, dashes and spaces are ignored on entry).
- **Storage:** only SHA-256 hashes, scoped to their account. They are returned once at confirmation and once per regeneration, never again.
- **New codes:** `POST /api/auth/2fa/recovery-codes {password, code}` replaces all of them.

### Turning 2FA off (`POST /api/auth/2fa/disable {password, code | recovery_code}`)

- It needs the password AND a current code or a recovery code. A password alone is a 422; a wrong pair is a generic 403, and a wrong password never spends a code.
- **Refused for administrators** (403), whatever they send.
- On success, the credential and the recovery codes are deleted, every session of the account ends, and this browser gets a fresh password-only session.

### Admin enforcement

`admin_only` (`backend/admin/security.py`), the single dependency on every `/api/admin/*` route and on `GET /api/admin/users`, now requires the admin role **and** a session with `mfa_level >= 1`.
- The level is the session row's, read by `authenticate()`. Rows are immutable since 0026, and the level is set only when a session is created after a verified second factor.
- No header, query parameter, cookie, body field, `DEMO_MODE` or role grants it.
- **Bootstrap:**
  1. An admin signs in with the password and gets an ordinary session. The admin API answers `403 {"detail": {"code": "mfa_required", ...}}`.
  2. The admin console shows "Turn on two-factor authentication" with the setup card in place.
  3. Confirming replaces that browser's session with an MFA one, and the console opens.
  4. From then on, every admin sign-in needs the code.
- Admin sessions created before enrolment stay at level 0 and never pass. There is no bypass route.

### `mfa_level` (sessions, since 0026)

- `0`: password only.
- `1`: password plus a verified second factor.

The level is never accepted from a client. Password changes and logout-all keep a session's level on rotation, as 14C's rotation does for everything else.

### Throttling (in the database, `mfa_failures`)

- **Counting:** every wrong second-factor attempt is recorded per user, whether it is a sign-in code, a recovery code, a setup confirmation, a disable or a regeneration (a wrong password on setup counts too).
- **Limit:** `MFA_MAX_FAILURES` (10) within `MFA_WINDOW_SECONDS` (15 min) blocks every second-factor check for that user, with a 429 whose `Retry-After` is exactly when the oldest failure leaves the window.
- **Durable:** this is database-backed, so a restart or a second worker does not reset it.
- **No permanent lock-out:** rows older than the window are deleted as the check runs.
- **Per challenge:** a challenge also ends after 5 wrong codes.
- **Reserved up front (Phase 14F):** an attempt reserves its failure row (one conditional `INSERT ... SELECT`) and takes one of the challenge's attempts (one conditional `UPDATE`) before the code is checked. A success, or a stop before any answer was judged (no setup, no key, a dead challenge), gives the failure row back. So concurrent requests cannot exceed either limit, and none can hit the schema's `attempts <= 5` CHECK (section 27, DEFECT-1/4).
- **Before the code step:** the 14C password throttles still apply to the password step.

### Frontend

- **`frontend/twofactor.js`** (loaded after `profile.js`; it uses the shared `LBApi.api()`, so every write carries the 14B CSRF signal):
  - the sign-in code step: a 6-digit field with `autocomplete=one-time-code`, a recovery-code option, and plain error messages;
  - the two-factor card on the profile page for learners, parents and admins: status, setup with the QR and the manual key, confirmation, recovery codes shown once with a warning, new codes, and turning it off (hidden for admins);
  - the admin console's mandatory enrollment.
- Nothing is put in `localStorage` or logged. The setup key and the codes exist only in the page while they are shown.

### Tests

- **`tests/test_two_factor.py`** covers crypto, TOTP, the QR, setup, confirmation, sign-in, recovery codes, the throttle, admins, turning it off, regeneration, and 25 named attacks.
- **`tests/test_two_factor_migration.py`** covers 0027 on a clean database and as an upgrade, every constraint and trigger, and cascades.
- **`tests/test_two_factor_frontend.py`** with `tests/frontend/twofactor_harness.js` runs the real UI against a live server, computing codes from the displayed key with a JavaScript HMAC-SHA1.
- **Existing tests changed on purpose:**
  - the admin API helpers plant an MFA session (`conftest.plant_mfa_session`, the admin harness's planted sessions) instead of the password-only one the admin API now refuses;
  - the Phase 2 admin-listing test now also checks the `mfa_required` refusal;
  - migration pins now expect 0027.

**Mutation testing:** 63 mutants, 61 killed, 2 equivalent, 0 genuine survivors.

| Area | Mutants |
|---|---|
| Crypto | 7 |
| TOTP | 10 |
| Sign-in challenge | 9 |
| Recovery codes | 4 |
| Throttling | 7 |
| Setup, confirmation, turning off, regeneration | 11 |
| Admin enforcement | 5 |
| Challenge cookie | 5 |
| Frontend | 5 |

The two equivalents, with proof:
- **Removing the decoded-key length check.** The key-format rule accepts exactly 43 base64url characters plus an optional `=`. 43 characters are 258 bits, which always decode to exactly 32 bytes, so no input can reach the length check with another length. It stays as a second line of defence. (Checked empirically too: 20,000 random 43-character keys all decode to 32 bytes.)
- **Removing only the time filter from the failure-count SELECT.** The same function first deletes every failure older than the window, in the same transaction, so no older row remains for the filter to exclude. Removing both the delete and the filter is killed by the throttle-expiry test, so expiry itself is covered.

### Known limitations

- **TOTP only:** no WebAuthn/passkeys, no SMS or e-mail codes.
- **No self-service recovery:** without an authenticator or any recovery codes there is no way back in. An administrator's 2FA can't be reset without database access (no reset command is included).
- **Losing `TOTP_ENC_KEY`** disables every TOTP credential (recovery codes keep working).
- **Per-process throttles:** the 14C password throttles are still per process. The second-factor throttle is in the database.
- **One extra code per enrolment:** confirmation spends one time step, so the very next sign-in within the same 30 seconds needs the following code.


## 26. Phase 14E: security events, admin security view and privacy hardening

One additive migration, `0028_security_events.sql`. No external logging or monitoring is involved.

### What is already covered elsewhere

Admin **content** changes (the CMS) are recorded in Phase 13's append-only `admin_audit_log` and are not duplicated. Security events cover authentication and account security only. That table's fixed CHECK lists are also why security events have their own table rather than extending it.

### Security event taxonomy (`security_events.event_type`)

| Area | Events |
|---|---|
| Sign-in | `login_success`, `login_failure`, `login_throttled` |
| Sessions | `logout`, `logout_all` (with the number revoked), `session_revoked` |
| Password | `password_changed` (with the number of sessions ended), `password_change_failed`, `password_change_throttled` |
| Two-factor | `mfa_setup_started`, `mfa_enabled`, `mfa_challenge`, `mfa_success`, `mfa_failure`, `mfa_throttled`, `mfa_recovery_code_used` (with codes left), `mfa_recovery_codes_regenerated`, `mfa_disabled`, `mfa_disable_failed` |
| Admin | `admin_login` (an admin's sign-in completed with a second factor), `admin_access_denied_mfa` (an admin API refused for a password-only session; recorded at most once a minute per admin) |

Every event has an `outcome` (`ok`, `failed`, `denied`). It may also have:
- `method`: `password`, `password+totp` or `password+recovery`;
- `reason`: `wrong_credentials`, `wrong_code`, `wrong_recovery_code`, `expired_challenge`, `throttled`, `not_configured` or `admin_cannot_disable`;
- `stage`: `sign_in`, `setup`, `confirm`, `disable` or `regenerate`;
- `count`: an integer from 0 to 100,000;
- `ip_ref`: see below.

### Privacy

- **Closed columns only.** Every column is a CHECK-constrained closed value, and there is no free-text or JSON metadata column (a test pins the column list). No password, password hash, session token or hash, TOTP secret, recovery code, challenge cookie, e-mail address, request body or header can be stored, by design rather than by filtering.
- **The account:** `user_id`, which is NULL for an unknown e-mail. A failed sign-in for an existing account is attributed to it, and one for an unknown e-mail to no one; the e-mail is never stored.
- **The client address** is stored only as `ip_ref`, a 16-hex HMAC under `ADMIN_REF_SECRET`, so attempts from one address can be grouped without keeping the address. Without `ADMIN_REF_SECRET` the key is per process, so references group only within one run.
- **Admin display:** admins see the account as the same opaque HMAC reference the learner overview uses (`admin/learners.ref_for`), never the id.

### Immutability

- **Append-only:** triggers refuse every UPDATE and DELETE. The one exception is the foreign key's own `ON DELETE SET NULL` when an account is removed (all other columns untouched), the same rule as `admin_audit_log`.
- **No API edits:** no endpoint changes or deletes events. **Retention is not defined:** events are kept indefinitely, and pruning them would need a deliberate, separately reviewed change to the trigger.

### Write policy (`backend/auth/events.py`)

- **With a state change:** events that belong to a state change are written in the **same transaction** as the change (a session created or revoked, a password changed, two-factor enabled or removed, a challenge completed). Change and event commit together or not at all. A test makes the event fail and checks that the password change did not happen.
- **Without a state change:** failed, throttled and refused attempts are written in their own transaction, **best-effort for transient errors only**. A `sqlite3.OperationalError` (such as "database is locked") is logged by its type and swallowed, so a busy database cannot turn a wrong password into a server error.
- **Programming errors are never swallowed:** an unknown type or field value (`ValueError`) or an integrity violation raises.
- **Free-to-repeat refusals are recorded quietly (Phase 14F):** `record_quiet` writes at most one event per 60 seconds for the same type, outcome, account, reason, stage and address. It covers throttled sign-ins, throttled password changes, throttled second factors, dead login challenges and an admin asking to turn off 2FA. Its lookup reads only the time index. Before 14F, one anonymous client could add about 400 rows a second (section 27, DEFECT-6).
- **Nothing a client sends** becomes an event field.

### Admin views (admin role + MFA session, `/api/admin`, `no-store`, behind the 14B guards)

- **`GET /api/admin/security-events?limit=&before=&type=`** lists events newest first.
  - `limit` is 1 to 100 (default 25). `before` is the previous page's `next` cursor. `type` is one exact event type from the closed list.
  - Anything else is a 422. Unknown parameters are ignored, so there is no filter by account, address or e-mail, and no free-text search.
  - New events never shift a page in progress.
  - Each item is `{occurred_at, type, outcome, account (reference), method, reason, stage, count, network (ip_ref)}`.
  - Reading records nothing.
- **`GET /api/admin/users?limit=&offset=`** replaces the Phase 2 listing, which returned every account's e-mail, name and handle, unpaginated.
  - It now returns `{items: [{ref, roles, created (date), two_factor}], total, limit, offset}`: `limit` 1 to 100 (default 25), ordered by account.
  - It moved into the Phase 13 admin router (CSRF guard, MFA) and is now part of the admin privacy canary scan, which has no exceptions left.
  - No frontend used the old shape.
- **Admin console → Security** (`#/admin/security`) shows the configuration warnings and flags, recent security events with a type filter and "Older events" paging, and the accounts with their two-factor status. It never shows a key, password, code, token, e-mail or address.

### Security health (`GET /api/admin/health` → `security`, admin + MFA)

The block reports `cookie_secure`, `totp_key` (`valid` / `missing` / `malformed`, never the value), `demo_mode`, `demo_live_ai`, `admins` and `admins_with_two_factor`, plus `warnings`:

| Code | Severity | When |
|---|---|---|
| `cookie_not_secure` | warning | `COOKIE_SECURE` is off |
| `totp_key_missing` / `totp_key_malformed` | critical if any admin account exists, otherwise warning | the TOTP key is missing or malformed |
| `admins_without_two_factor` | warning | an administrator has not turned on two-factor |
| `demo_mode_on` | warning | `DEMO_MODE` is on |
| `demo_live_ai_on` | warning | `DEMO_LIVE_AI` is on |

- "Production" is not guessed from host names: the settings are reported as they are.
- Nothing about startup changed: local plain-HTTP development and the TOTP fail-closed behaviour are as before.
- **Public `GET /api/health`** is now `{ok, ai}` with `ai` a yes/no. It used to name the configured provider.

### Tests

- **`tests/test_security_events.py`** covers:
  - every recorded event and its fields;
  - the denial quiet period, and that admin CMS changes stay in `admin_audit_log`;
  - the failure policy: atomic with the change, best-effort only for transient errors, integrity errors raised;
  - append-only and closed columns, and privacy: no secret, code, token, hash, e-mail or address in the table or the view;
  - who may read, and the parameter bounds;
  - cursor pagination, including stability while events arrive;
  - the account listing (fields, bounds, stable and complete pages), the health warnings, and the coarse public health check;
  - the 20 named attacks.
- **`tests/test_security_events_migration.py`** covers 0028 on a clean database and as an upgrade that keeps users, admins, sessions, two-factor credentials and recovery codes byte-identical.
- **The admin harness** gained the Security page scenario.
- **A new conftest safety net** points `main.DB_PATH` at a temp file for every test, so a test that forgets the `client` fixture can never open the real database. One test did, read-only, during development; `buddy.db` was verified unchanged.
- **Existing tests that changed on purpose:**
  - the account-listing tests (Phase 2 and 9) and the Phase 13 privacy pin now expect references instead of e-mails;
  - migration pins now expect 0028;
  - the admin nav now has seven pages;
  - the public health check is now a yes/no.

**Mutation testing:** 66 mutants, 66 killed, 0 equivalent, 0 survivors.

| Area | Mutants |
|---|---|
| Event writer and failure policy | 9 |
| Append-only and closed schema | 6 |
| Event hooks in sign-in, sessions, password and two-factor | 24 |
| Who may read | 2 |
| Event view (bounds, order, cursor, filter, no raw ids) | 7 |
| Account listing | 6 |
| Security health and the public check | 9 |
| Admin console | 3 |

The first run left two survivors, each a test that could not see the difference, and both were fixed:
- **Two-factor status:** an account with a pending, unconfirmed setup had not been checked; it must show two-factor off.
- **The console check:** it found event names in the page text, but they also appear in the type filter's options. It now checks the table rows.

### Known limitations

- **No retention:** security events are kept indefinitely (no retention or archiving), and the table grows with sign-in traffic. Only security-sensitive actions are recorded, never ordinary requests.
- **Network references reset on restart** unless `ADMIN_REF_SECRET` is set.
- **No export or alerting:** events stay in the application database, with no export, alerting or external monitoring.
- **Admin activity coverage:** admin reads of the security views are not themselves recorded (to keep the log to security-sensitive changes), and admin CMS writes are in `admin_audit_log`, not here.

## 27. Phase 14F: final security verification

Phase 14F added no features. It attacked the whole Phase 14 stack (14A to 14E) from the outside, over HTTP. Where a stored value or a race was the point, it also read the isolated test database directly. It fixed only the defects it could demonstrate, each with a regression test that fails on the 14E code and passes now.

### Defects found and fixed (`tests/test_security_regressions_14f.py`)

| # | Defect (14E behaviour) | Fix |
|---|---|---|
| 1 | Concurrent wrong codes on one login challenge all passed the "attempts left" check. The extras broke the `attempts <= 5` CHECK, so they were a **500** and their failures were rolled back uncounted. | One of the challenge's attempts is taken by a conditional `UPDATE` before the code is checked (`two_factor.take_attempt`). The losers get the normal "sign-in expired" 401. |
| 2 | Concurrent wrong passwords for one account were all checked: **15 checked against a limit of 5**. The same held per address. | `Limiter.acquire` checks and counts in one locked step before the password is verified; a right password gives its count back. |
| 3 | The same race in the password-change throttle. | The same fix. |
| 4 | The same race in the database-backed second-factor limit (`MFA_MAX_FAILURES` per user). | A failure row is reserved by one conditional `INSERT ... SELECT` before anything is checked (`two_factor.reserve_failure`). It is given back on success or an early stop (`mfa._attempt`). |
| 5 | A whole number beyond SQLite's 64-bit range was a **500** on many routes: in a path id, a query parameter (`offset`, `entity_id`) or a JSON field (`option_id`, `situation_id`, `lesson_id`). | One app-wide handler turns SQLite's integer `OverflowError` into a structured 422 (security headers included). Any other `OverflowError` is still a 500. |
| 6 | Refusals that cost nothing to repeat (a throttled sign-in does no hashing; a forged challenge cookie) wrote **one security event per request**. That was an unauthenticated write amplifier: about 400 rows a second from one client. | `events.record_quiet` (see section 26, write policy). Every attempt that is actually checked (a wrong password or code) is still recorded. |

Reproduction scripts ran against temp databases before any fix. Reverted to the 14E backend, 33 of the file's 49 tests fail, including all 22 DEFECT tests. The tests that pass on both versions check behaviour the fixes had to keep: successes don't count, wrong answers count exactly once, and other overflow errors stay 500s.

### What Phase 14 protects, as verified (`tests/test_final_security.py`)

- **Authentication:**
  - The sign-in matrix covers unknown e-mail, wrong or right password, case, untrimmed passwords, missing, extra or oversized fields, wrong types, and malformed, binary and deeply nested JSON. Unknown e-mail and wrong password give identical responses, and no password is ever echoed.
  - Unicode, tab and space passwords work exactly as typed; whitespace-only and short passwords are refused at registration.
- **Throttles:**
  - The account limit holds across addresses and the address limit across accounts. Changing e-mail case, `User-Agent`, `X-Forwarded-For`/`X-Real-IP`/`Forwarded`, other headers, a foreign or valid session cookie, or the JSON formatting does not bypass them.
  - Requests refused by validation neither count nor bypass.
  - Windows expire exactly, and memory stays within `THROTTLE_MAX_KEYS`.
  - Registration is limited per address (a taken e-mail still counts), and password change per user across sessions.
- **Sessions:**
  - **Tokens:** a token or its hash never appears in a response. Only the hash is stored, and the raw token is not in the database file. Only the raw token authenticates: a public id, the hash, the handle, an empty value and an oversized value all get 401.
  - **Public ids:** they are 128-bit random hex values unrelated to the token.
  - **Ownership:** revoke and logout-all are owner-scoped.
  - **Password change:** it revokes every other session and rotates the current one, and the old token is dead.
  - **Expiry:** the idle and absolute boundaries were checked at -1 s, 0 s and +1 s, including a session used every 20 minutes for its whole week. An expired session stays dead even if the clock goes back.
  - **Exposure:** the session list has safe fields only, and every session or 2FA operation needs a session.
- **Two-factor:**
  - **Setup and confirmation:** setup needs the current password. An unconfirmed setup is not 2FA, an expired setup cannot be confirmed, and a setup cannot be confirmed twice.
  - **Code format:** malformed codes (other scripts' digits, full-width, spaces, signs, NUL) are wrong answers. Oversized or mistyped codes are refused before anything is checked.
  - **Window and replay:** the RFC 6238 window is exactly ±1 step, and a step is spent once.
  - **The challenge:** a correct password gives only a challenge cookie (`Path=/api/auth/2fa`, `HttpOnly`). The challenge is not a session, and a session is not a challenge. A challenge belongs to one user, is used up after 5 wrong codes, expires, and completes once.
  - **Recovery codes:** they are single-use and stored hashed, never in plain text or the database file. They are never shown again. Regeneration needs the password and a current TOTP code (not a recovery code) and kills the old set.
  - **Disable:** it needs the password and a second factor, and is refused for admins.
  - **No leaks:** no secret, code, token, password, key or e-mail reaches the logs, and the frontend never stores 2FA material.
- **Admin:**
  - **MFA gate:** every admin GET route refuses a password-only admin session (`403 mfa_required`) as well as learners and parents (403) and strangers (401). A pre-MFA admin session stays locked out after 2FA is turned on.
  - **No private data:** the account and event listings carry no e-mail, name, handle, raw address, `User-Agent` or password.
  - **Paging and filters:** they are bounded and closed. `limit` 1 to 100, `before` 1 to 2^62, `offset` up to 10 M; the event type is an exact enum, so SQL-shaped values get 422. Paging through cursors returns exactly the plain listing, and paging parameters never bypass authorization.
  - **MFA denials:** they are recorded once a minute.
- **CSRF:**
  - **The matrix:** it covers 25 endpoints (anonymous, learner, parent, admin, auth, 2FA, AI, state, audio and social) against 12 attacks: no or wrong signal, no, form or text content type, and foreign, `null`, malformed and look-alike Origin and Referer. Every combination is refused, except the three content-type attacks on the raw-audio upload, which takes audio by design.
  - **Other properties:** body-less writes have no bypass, refusals have no effect, and the own origin and referer are accepted. A legitimate audio upload works and a wrong media type gets 415. Every admin write still runs the admin router's own `csrf_guard` (the second layer).
- **Headers and cookies (real responses):**
  - **Every kind of response:** page, static file, API 200/401/404/422 and CSRF 403 all carry `nosniff`, `DENY`, the referrer policy and the partial CSP.
  - **API responses:** every one is `no-store`, and none carries a CORS grant.
  - **HSTS:** only when `COOKIE_SECURE=1`.
  - **Cookies:** every cookie set or cleared (registration, confirm, challenge, verify, password change, disable, sign-in, revoke, logout, dead challenge) is `HttpOnly; SameSite=Lax`. It is `Secure` exactly when `COOKIE_SECURE=1`.
  - **Where cookies are set:** only `backend/routers/auth.py` sets or deletes a cookie.
- **Legacy endpoints:**
  - **`/api/ai` access:** it is offline for anonymous visitors unless `DEMO_LIVE_AI` is on, and for children, profile-less learners, parents and admins always. Only teen and adult learners reach the model.
  - **`/api/ai` input:** history, length, role, mode, language, scenario and extra fields are allow-listed. City and level must exist in the database, and the scene text is the server's.
  - **`/api/ai` failures:** provider errors leak nothing; the log names the exception type only. Malformed bodies get a structured 4xx, and requests are rate-limited per caller.
  - **`/api/state`:** it is private to its owner, with no shared or demo state. It is validated (unknown fields, types, ranges, version and size: 413 unread), and XSS payloads come back as inert JSON data.
- **Authorization (IDOR):**
  - **The sweep:** one fixture creates a learner who owns a tutor conversation, a roleplay session, a speaking session, daily-plan tasks, a parent link and sessions. Another learner, another parent and an anonymous caller then requested every route that names an object, with her ids and public ids (300+ requests). Nothing of hers came back and nothing was a 500.
  - **Her objects:** direct reads and writes on them get 403/404 and leave them unchanged.
  - **Request bodies:** identity is never taken from a body.
  - **Anonymous callers:** in lockdown, every route except reference data, health, the page, register, login, logout and verify returns 401.
- **Security events:**
  - **Coverage:** one full flow produced all 21 event types.
  - **No secrets stored:** no event and no byte of the database holds a password, token, challenge token, TOTP secret, recovery code, raw address or `User-Agent`; no event holds an e-mail or name.
  - **Schema:** malformed rows, updates and deletes are refused. Deleting a user keeps their events, unlinked.
  - **Atomicity:** an event failure inside a password change rolls the change back and is a 500, not swallowed. A transient failure leaves the throttles counting.
- **Configuration:**
  - **TOTP key:** a missing or malformed `TOTP_ENC_KEY` fails closed (setup 503, a code 503 with no session), while recovery codes still work. Health reports the key's status, never the key.
  - **Warnings:** they match the settings exactly.
  - **Repository:** no `.env`, database or key file is tracked, no provider-key pattern appears in tracked files, and the test TOTP key is not in `backend/`. A full flow with a recording adds no file to the repository.

### Test isolation (`tests/conftest.py`)

- **No network from the test process:** every TCP/UDP `connect` and host-name lookup for a non-loopback host raises, and is remembered. The `_network_isolation` fixture fails any test during which one was attempted, even if the code under test swallowed the error.
- **The real provider call is proven blocked:** it was exercised with a key for Groq, Anthropic and OpenAI and refused before leaving the machine.
- **Test servers:** the frontend tests' uvicorn servers cannot be patched, so they inherit blank provider keys and `HTTP(S)_PROXY`/`ALL_PROXY` pointing at a dead loopback port, with `NO_PROXY` for loopback. Every non-local request from httpx (the backend's only HTTP client) fails there.
- **Databases and the model:** temp files only; `main.call_llm` is stubbed and the real `buddy.db`, `buddy.db.bak` and `.env` are checked unchanged around a full flow.

### Mutation testing (focused on the code this phase touched)

A copy-based runner changed one exact snippet at a time in a copy of the repository (never the real one, never `.env` or `buddy.db`) and ran the targeted tests.

| Area | Mutants | Killed | Equivalent |
|---|---|---|---|
| Limiter (`throttle.py`: acquire, release, locking) | 6 | 5 | 1 |
| Sign-in, registration, password change (`service.py`) | 11 | 11 | 0 |
| Quiet event writer (`events.record_quiet`) | 13 | 13 | 0 |
| Reserved second-factor attempts (`mfa.py`) | 14 | 14 | 0 |
| Repository (`two_factor.py`: reserve, release, take_attempt) | 10 | 9 | 1 |
| Out-of-range numbers (`main.py`) | 3 | 3 | 0 |
| **Total** | **57** | **55** | **2** |

The first run had 4 survivors. Two were real test gaps, and new tests now kill them:

- **"quiet: ignores the outcome":** a refusal with the same type and fields but another outcome is now shown to get its own event.
- **"quiet: up-front check removed":** without the up-front check, a malformed event against an unusable database was swallowed as an `OperationalError` and a database file was created. A test now proves it raises before the database is touched.

The two remaining survivors were proved equivalent from the code; the tests passing was not taken as proof:

- **"limiter: record unlocked"** (the `with self._lock` inside `Limiter.record` removed). The only call to `record` in `backend/` is inside `Limiter.acquire` (`throttle.py`), which already holds the same re-entrant lock for the whole check-and-count. Removing the inner acquisition changes no reachable behaviour. It is kept so that direct callers (tests) get the same guarantee.
- **"repo: reservation ignores the window"** (`AND occurred_at > ?` dropped from the counting subquery of `reserve_failure`). `occurred_at` is `NOT NULL`. The DELETE just before it, in the same transaction, removes every row of this user with `occurred_at <= since`. That DELETE is a write, so the connection holds SQLite's write lock until commit and no other writer can insert in between. Every row the subquery can see for this user therefore already has `occurred_at > since`, and the predicate is redundant.

### Configuration for production

| Setting | Production value | Why |
|---|---|---|
| `COOKIE_SECURE` | `1` | Cookies get `Secure` and HSTS is sent. Leave it unset (0) for local plain-HTTP development, where cookies must work over `http://`. |
| `TOTP_ENC_KEY` | 32 random bytes, base64url (`python -c "import base64, secrets; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip('='))"`) | Without it, 2FA can be neither set up nor checked, and admins cannot use the console. Keep it out of the repository and back it up: losing it makes every stored secret unreadable (users then need recovery codes). |
| `ADMIN_REF_SECRET` | a long random value | Keeps admin references and network references stable across restarts. |
| `DEMO_MODE` | `0` | The legacy AI endpoint then needs a session. |
| `DEMO_LIVE_AI` | unset | Anonymous visitors stay on the offline engine. |
| `TRUSTED_ORIGINS` | the site's origin(s) | Needed when a proxy rewrites `Host`. |
| Workers | one, or a shared limiter store | The in-memory limiters are per process. |
| Proxy | pass the client address with uvicorn's `--forwarded-allow-ips` set to the proxy only | Otherwise every client shares the proxy's address in the address limits. |

### What the address limits really provide

- **What the address is:** it is the connection's address (`request.client.host`). Under uvicorn, forwarded headers are honoured only from `--forwarded-allow-ips` (default 127.0.0.1); that is uvicorn's behaviour and the in-process tests do not exercise it. In-process, a client cannot change the address with a header (verified for `X-Forwarded-For`, `X-Real-IP` and `Forwarded`).
- **Many addresses get no bypass per account:** an attacker with many addresses (a botnet or IPv6 rotation) gets `LOGIN_IP_MAX_FAILURES` per address. The account limit still caps guesses at **5 per 15 minutes per account from all addresses together**.
- **Spread-out guessing is only slowed:** such an attacker can still spread guesses over many accounts. The address limit only slows that; it cannot prevent it.

### Known limitations (after 14F)

- **Throttles:**
  - **Per process:** the sign-in, registration and password-change throttles are per process and reset on restart (the second-factor limit is in the database).
  - **Lock-out risk (accepted):** anyone can lock an account's password sign-in for 15 minutes by guessing at it.
- **Enabling 2FA keeps other sessions:** enabling 2FA replaces only the current session; the account's other existing sessions stay signed in, as at most sites. Logout-all is one click away. Admin sessions without a second factor cannot reach the console either way.
- **Events:**
  - **Distributed refusals:** quiet recording is per address, so a refusal flood from many addresses still adds up to one row per address per minute.
  - **Retention:** events are kept indefinitely.
- **Phases 9/10 code throttles:** the parent link-code and friend-code throttles still check, then count. They are fast database lookups against code spaces of 32^10, and they were left unchanged (outside the Phase 14 stack).
- **Partial CSP:** `script-src`/`style-src` are not restricted, since the legacy UI renders with inline handlers.
- **Explicitly deferred:** WebAuthn/passkeys, password reset, e-mail verification, SMS, the strict CSP migration, external logging/SIEM, and a shared limiter store.

## 28. Phase 15A: responsive, mobile-first experience

Phase 15A makes the existing SPA usable on phones, tablets and every desktop size without rebuilding it, and (at the product owner's request during review) shows the app to signed-in accounts only.
- **Unchanged:** there is no schema change, no new dependency, and no change to the server's authentication, authorization, CSRF, cookies, sessions, 2FA, throttling, AI providers or privacy.
- **The 2FA screens:** they were deliberately left alone (deferred by request), apart from the existing sign-in code step continuing to work behind the new sign-in screen.

### What a real-browser survey found (headless Chrome, before any change)

- **Navigation gap:** on phones (860px and below) the sidebar is hidden and the bottom bar showed 6 fixed learner links. Profile (sign-in, 2FA), the parent portal and most learner pages (lessons, listening, voice, plan, rewards, friends and more) had no navigation entry on a phone.
- **Admin bar overflow:** the admin bottom bar packed 7 items, and "Health" was off-screen (and clipped) at 320 and 375px.
- **SOS button over the send button:** the 🆘 button covered the chat's send button. The input's built-in minimum width also pushed the button out of the card.
- **Overflow:** the lesson "situation" card overflowed at 320px and squeezed its text into one-word lines, and Progress overflowed at 768px (a long achievement title).
- **Phone keyboard:** fields at 14–15px make iOS zoom the page on focus. Chat heights used `100vh` with a 520px minimum, and the viewport meta lacked `viewport-fit=cover`, so the existing safe-area padding had no effect.
- **Small touch targets and focus:** back links were 21px tall, chat chips 25–29px, small buttons and admin selects 22–38px, and sliders 16px. Several fields removed the focus outline.

### Desktop and laptop problems found on review (headless Chrome at 1024×768 to 2560×1440)

- **Sign-in unreachable:** the sidebar was `height: 100vh`, sticky, with 1,122px of content and no scrolling of its own. On a 768px or 900px-tall laptop (and even at 1920×1080), the lowest links (Rewards, Friends, **Profile, the only way to sign in**) were below the screen and could never be scrolled into view.
- **Phantom scrolling:** the spilled sidebar stretched every page to at least 1,122px, so short pages scrolled into empty space.
- **Expensive scrolling:** `background-attachment: fixed` on `body` made the browser repaint the whole page on every scroll frame.
- **Proportions:** the content was capped at 1,180px and pinned to the left, leaving a wide empty band on large screens. Headings and spacing were fixed pixel sizes.
- **Fake progress:** a signed-in account with no saved progress was given the built-in demo state ("Alex": 78% confidence, a 4-day streak, Day 4), so a brand-new learner saw someone else's numbers in the sidebar and on the confidence, progress and tutor pages.

### Changes

- **Signed-in accounts only (`frontend/app.js` `gate`, `frontend/profile.js` `ProfileView.gate`):** until the app knows who is looking it shows "Loading…". A visitor who is not signed in gets only a sign-in screen, whatever the route: no navigation, no pages.
  - **The screen:** a split-screen design. On the left is an animated brand panel (aurora, a blur-in headline, rotating "Learn to handle ___ like a local", floating phrase cards and count-up stats), which fits the screen and drops cards on shorter laptops. On the right is the card.
    - **Tabs:** **Sign in** and **Create account**, with a sliding indicator and arrow-key support (WAI-ARIA tabs).
    - **Account type:** learner and parent are picked with cards, since there was previously no way to create a parent account in the UI.
    - **Fields:** real `<label>`s and a show/hide password button.
    - **Submitting:** Enter submits, the button shows a spinner while busy, an empty form explains itself without a request, an error shakes the card, and success fades it out.
    - **Phones and tablets:** the panel becomes a compact banner above the card.
    - **Motion:** all of it is off under `prefers-reduced-motion`.
    - **2FA:** the existing 2FA code step still appears for accounts that have it on.
  - **🆘 for everyone:** the 🆘 button and its emergency phrases stay available without an account, and the screen also offers "Emergency phrases" and a **📞 Call 112** link. On the phone sign-in screen 🆘 sits in the banner's corner and scrolls with it (any fixed spot would cover the full-width form while scrolling). Once scrolled past, the help strip right below the form is on screen, so help is in view at every scroll position.
  - **Signing in or out:** the app re-reads the account and mode and redraws (`A.identityChanged`), and signing out returns to the sign-in screen.
  - **Presentation only:** the server's rules are unchanged. Every learner, parent and admin API already refuses requests without a session. The legacy `/api/ai` still answers signed-out callers when `DEMO_MODE=1` (offline unless `DEMO_LIVE_AI`); set `DEMO_MODE=0` in production.
- **Your own progress (`frontend/engine.js`):** a signed-in account with no saved progress starts from empty progress and its own display name. The "Alex" demo state is now only a fallback that the sign-in screen never shows. "Reset" says "Start my progress over" for an account.
- **Account controls always in view:** the top of the sidebar (and a slim top bar on phones) shows the account's name, linking to its profile, and a **Sign out** button, for every mode. Before this, sign-out lived only inside the Profile page, and an **admin could not sign out at all** because the console has no Profile page. Sign out ends the session on the server and returns to the sign-in screen.
- **Sidebar:** it scrolls by itself (`height: 100dvh; overflow-y: auto`) and is more compact on screens up to 1,000px tall, so nothing is ever cut off and it no longer stretches the page.
- **Proportions:** the content is centred beside the sidebar (`margin-inline: auto`, up to 1,240px, or 1,360px from 1,700px wide). Page padding, headings, the hero and its title scale with the screen (`clamp()`) instead of fixed pixels.
- **Smooth scrolling:** the background glow moved to a fixed, composited `body::before` layer.

- **Phone navigation (`frontend/app.js`, `mobileNav`):** the bottom bar holds 4 pages of the user's mode plus **More**. More is a dialog (`#more-sheet`, `role="dialog"`, `aria-modal`) listing the rest of the *same* list the sidebar shows (`AgeMode.filterNav`, unchanged).
  - **Per mode:** a child's 3 pages need no More. Parents get My Children, Home, Progress and Profile. Admins get their first 4 console pages.
  - **Behaviour:** opening moves focus into the menu and Tab stays inside it. Escape, the backdrop or ✕ close it and return focus to More, and choosing a page closes it.
  - **Labelling:** the current page carries `aria-current="page"`, nav icons are `aria-hidden`, and both navs are labelled "Main".
- **CSS (`frontend/styles.css` Phase 15A section, `frontend/admin.css`):**
  - **Bottom bar:** equal slots that always fit, with ellipsis for long labels.
  - **Focus:** a visible `:focus-visible` ring everywhere.
  - **Fields:** 16px on screens of 860px and below.
  - **Chat:** `dvh` heights with a 360px minimum; the composer keeps the send button clear of 🆘.
  - **Fit fixes:** the situation card and achievements wrap, selects are capped at the container width, and admin selects are styled.
  - **Touch screens (`pointer: coarse`):** controls are at least 44px tall. Per-message chat tools are 36px (above WCAG 2.5.8's 24px minimum), and inline links inside sentences are exempt.
- **Markup:**
  - **Meta:** `viewport-fit=cover`, `theme-color`, and the toast is a polite live region.
  - **Fields:** accessible names and keyboard hints (`enterkeyhint="send"`, `inputmode="numeric"`, `autocomplete`, `autocapitalize`) on sign-in, the 2FA sign-in step, chat, answer, parent-code and friend-code fields.
  - **Cache:** the static cache-busting stamp was bumped.
- **On-screen keyboard:** the repository has none (no code, docs or tests); 15A adds none, and a test asserts that no virtual keyboard is drawn. The phone's own keyboard is supported through the 16px fields, keyboard hints and `dvh` chat heights. The roadmap's "multilingual keyboard" remains future work.
- **Voice, children, parents, admins:** these were unchanged in behaviour. The microphone is still only requested after the Record tap (tested in the browser). A child's navigation is still exactly Adventure, Listen and Me, a parent still cannot see the social or AI pages, and nobody but an admin sees the console.

### PWA groundwork (and why there was no service worker in 15A)

*Superseded by Phase 15B (section 29), which adds icons and a static-only service worker on exactly the plan below.*


- **What exists:** `frontend/manifest.webmanifest` (name, `start_url`/`scope` `/`, `standalone`, theme colours) is linked from `index.html` and served as `application/manifest+json` with the usual security headers.
- **No icons:** the repository has no icon assets (the favicon is an inline emoji), so the manifest has none and the app is **not installable yet**. Browsers require 192px and 512px icons.
- **Deliberately no service worker:** a worker that caches anything risks serving one person's pages or data to the next person on a shared device, or serving stale code after a deploy. A test asserts that no worker is registered and no cache exists.

**Plan for Phase 15B (safe offline):**
- **What may be cached:** a worker scoped to `/` that pre-caches only the versioned static files (`/static/*.js|css?v=…`) and the app shell.
- **What may not:** `/api/*` stays network-only and is never cached: personal data, recordings, security events and admin content.
- **Offline:** the page falls back to the existing offline engine.
- **Cache lifetime:** caches are keyed by the `?v=` stamp and deleted on activation, and are cleared on sign-out.
- **Writes:** no queued or retried writes.
- **Prerequisites:** icon assets.

### Verification

- **Automated, in a real browser (`tests/test_mobile_layout.py`, 87 tests, headless Google Chrome via `tests/cdp.py`):**
  - **Setup:** the client uses the standard library only. The browser can reach only 127.0.0.1, and the live test server runs on a temp database with no provider.
  - **Layout:** no sideways overflow at 320, 375, 414, 768, 1024 and 1280px on 35 routes across anonymous, adult, child, parent and admin users. The desktop layout is unchanged.
  - **Navigation:** every navigation page is reachable on phones in every mode, with no mode gaining pages. The More menu works by touch and keyboard, and the current page is announced.
  - **Touch, focus and fields:** 44px targets, 16px fields and visible keyboard focus.
  - **Chat and SOS:** 🆘 never covers send, and the chat shrinks to a short screen.
  - **The sign-in screen:** every route shows only the sign-in screen to a signed-out visitor at phone and laptop sizes. The 🆘 panel and the 112 link work without an account. Signing in by typing and tapping opens the app with the account's name in view, while a wrong password stays on the sign-in screen. Learner and parent accounts can be created there. The tabs work by touch and arrow keys, the password can be shown and hidden, and an empty form is explained without any request. 🆘 never covers a form control on a phone at any scroll position, and help is always in view. Motion stops under reduced-motion and runs otherwise. Every kind of account (learner, parent, admin) can sign out from the sidebar or the phone top bar, and the server session really ends.
  - **Your own progress:** a new account starts at 0% with a 0-day streak, and the tutor greets it by name, not "Alex".
  - **Laptops and desktops:** at 1024×768, 1366×768, 1440×900 and 1920×1080 the sidebar scrolls so Profile is reachable, and the page is never taller than its content. The account name is visible without scrolling at phone and laptop sizes. The content is centred on 1920 and 2560px screens.
  - **Voice:** no microphone request without a tap.
  - **PWA:** the manifest is served, and there is no service worker.
  - **Regression proof:** at 74 tests, 60 failed against the Phase 14 frontend; the 13 sign-in and sign-out tests added since all depend on screens that frontend did not have. The 14 that pass on both are guards (microphone, no service worker, no on-screen keyboard, routes that already fitted).
- **Harness updates for the new behaviour:** `legacy_ui_still_works` now first checks that every page shows only the sign-in screen, then signs in and checks every page and the account's own level and streak. Its "reset stays local" check was removed, because it described the signed-out demo mode, which no longer exists. `signed_in_uses_own_identity` now expects the change on top of the account's own (empty) progress instead of the demo's 70%.
- **Existing suites:** the JavaScriptCore harnesses (169) pass, and the full suite passes.
- **Looked at, not asserted:** screenshots at 375px of each surveyed page and of the More menu were inspected by eye.

### Not verified / known limitations

- **Not tested:** physical devices, iOS Safari (zoom-on-focus behaviour, `dvh` with the keyboard open, safe-area insets), Firefox, Android Chrome on hardware, landscape orientation, and screen readers (VoiceOver/TalkBack). Chrome's device emulation is not a phone: in particular, that `dvh` tracks the on-screen keyboard where `vh` does not can only be confirmed on a device.
- **2FA deferred:** all 2FA screens (setup with the QR code, recovery codes, turning it off, the sign-in code step) were left exactly as they were and were not verified on phones, by request. The admin console still requires 2FA, as Phase 14D enforces server-side.
- **Children and 🆘:** in child mode the 🆘 button is still hidden (a Phase 8 decision); signed-out visitors and every other mode have it.
- **The legacy anonymous demo:** it is no longer reachable from the UI. Signed-out visitors see only the sign-in screen.
- **Scrolling and sizing:** the chat composer can sit just below the fold on short phones (the page scrolls to it). Content still scrolls under the 🆘 button, which only guarantees the chat's send button.
- **Not installable:** see the PWA notes above.

## 29. Phase 15B: installable app and safe offline foundation

Phase 15B makes LingoBuddy installable and gives it an honest offline behaviour, using the plan from section 28. There is no schema change, no new dependency, and no change to authentication, sessions, CSRF, 2FA or any API.

### What was added

- **Icons (`frontend/icons/`, original artwork):** a speech bubble around a globe on the brand gradient. `icon.svg` and `icon-maskable.svg` are the sources.
  - **Generator:** `tools/make_icons.py` renders the PNGs with headless Chrome (`tests/cdp.py`; Chrome is needed only to regenerate them).
  - **PNGs:** `icon-192.png` and `icon-512.png` (rounded, transparent corners); `maskable-192.png` and `maskable-512.png` (full-bleed, artwork inside the 80% safe zone); `apple-touch-icon.png` (180, opaque, since iOS fills transparency black); `favicon-32.png`.
  - **No emoji artwork:** the 🌍 favicon was replaced, because emoji artwork is copyrighted by its font vendors.
- **Manifest (`frontend/manifest.webmanifest`):** adds `id`, `categories` and the five icons above (192 and 512 for `any`, 192 and 512 for `maskable`, plus SVG). `index.html` links the favicons and the apple-touch-icon locally; nothing is remote.
- **Service worker (`frontend/sw.js`):** served at **`/sw.js`** by `backend/main.py` so its scope is the whole app (a worker under `/static/` could only control `/static/`), with `Cache-Control: no-cache` so a new release is found on the next visit.
- **Page side (`frontend/pwa.js`):** registration, the update offer and the install offer.
- **Offline page (`frontend/offline.html`):** static, with no personal data. It reads "You're offline: nothing can be loaded or saved", offers Try again, lists the five 🆘 emergency phrases and has 📞 Call 112. It returns to the app by itself when the connection comes back.
- **Inside the app:** an offline banner ("Nothing can be loaded or saved until you reconnect", with Retry) and a "new version ready, Refresh" card. A failed request now says "Can't reach LingoBuddy right now. Check your connection and try again."
- **The start page `/`:** it is now served with `Cache-Control: no-cache`. Found in browser testing: without it, Chrome's ordinary HTTP cache could serve an old copy of the sign-in screen when the server was down, instead of the offline page.

### Exactly what is cached, and what never is

- **Cached (one cache, `lingobuddy-static-<version>`, filled once at install, every entry by its exact URL):** 31 files.
  - **Versioned files (23):** the CSS (3) and JavaScript (20) files `index.html` loads, at this release's `?v=` stamp.
  - **Icons (6):** the six PNGs.
  - **Also:** the manifest and the offline page.
  - **Consistency:** a test keeps this list equal to what `index.html` loads, and the worker's `VERSION` equal to the page's stamp.
- **Never cached, never answered from the cache:**
  - **APIs:** every `/api/*` request (accounts, sign-in, registration, sign-out, sessions, password, 2FA, profiles, progress, lessons, attempts, plans, tutor and roleplay, recordings and transcripts, parent portal, admin CMS, security events, health).
  - **Pages and writes:** page loads themselves, and any POST, PUT, PATCH or DELETE.
  - **Other origins:** for example web fonts.
  - **Anything else:** any file not on the list, including an allowlisted file requested under a different URL or query.
  - **How it's enforced:** the worker makes no runtime cache writes at all (no `cache.put`); the only write is the install-time `addAll` of the list.
- **Updates and cleanup:** a new release (a new `VERSION`) installs alongside and **waits**. The page shows "A new version of LingoBuddy is ready. Refresh", and nothing reloads until the learner taps it. On activation every older `lingobuddy-static-*` cache is deleted.
- **Failures:** if installation fails (a missing file, say), the app stays online-only, exactly as before. If service workers are missing or registration is refused, nothing changes either.
- **Signing out:** nothing personal was ever cached, so signing out leaves nothing to clear. API responses are `no-store` (Phase 14B), and the browser's HTTP cache does not keep them either.

### What works offline, and what does not

- **Works offline:** the offline page with the emergency phrases and the 112 link, the app's static files, and (in an already-open page) anything that does not need the server, such as the 🆘 panel.
- **Needs the server:** everything else. Signing in, every lesson, exercise, listening and speaking activity, the tutor and roleplay, plans, rewards, friends, the parent portal and the admin console all need it.
  - **Nothing is queued:** progress made while offline is not saved, nothing is queued or retried later, and the app never says otherwise.
  - **No stale data:** an open page whose data requests fail shows the offline banner and the requests' own errors, never old data.
- **Offline progress later:** an offline learning mode with saved progress would need its own offline data and synchronisation design; it is not part of 15B.

### Installing

- **Where the worker registers:** the app registers its worker only on **HTTPS**, or on `localhost` / `127.0.0.1` for development, because browsers allow service workers nowhere else. On a plain-HTTP LAN address there is no worker and no install offer; the app works online as before.
- **Chrome check:** Chrome's own check (`Page.getInstallabilityErrors`) reports **no installability errors**, verified in headless Chrome on `127.0.0.1`.
- **Chromium browsers (Chrome, Edge, Android):** the **📲 Install app** button appears in the sidebar, the phone's More menu and the sign-in screen **only when the browser fires `beforeinstallprompt`**. Tapping it opens the browser's own install prompt, once.
- **Safari and Firefox:** there is no install button, because these browsers do not offer the event. On iPhone and iPad, Share → Add to Home Screen uses the apple-touch-icon.
- **Production:** HTTPS is required, set `COOKIE_SECURE=1` (section 27), and serve `/sw.js` from the site root.

### Verification

- **Server-side (`tests/test_pwa.py`, 21 tests):**
  - **Served correctly:** `/sw.js` (served from the root, `no-cache`, security headers, not in the API schema), and the start page (`no-cache`).
  - **Version and allowlist:** the worker's version equals the page's asset stamp. The worker caches exactly the page's 23 static files plus the icons, manifest and offline page; the allowlist holds only public `/static/` files, all of them served.
  - **Code checks:** the worker contains no run-time cache writes. Only `lingobuddy-static-*` caches are cleaned up, and an update waits for the learner.
  - **Manifest and icons:** the manifest is complete and local, each icon is served at its declared size (PNG dimensions checked), maskable and apple icons are opaque, and the page links the local icons.
  - **Offline page:** it is static and honest (no `fetch`, storage, cookies or remote resources), and everything it needs is cached.
- **Real browser (`tests/test_pwa_browser.py`, 15 tests, headless Google Chrome via `tests/cdp.py`, live test servers on temp databases):**
  - **Registration:** the worker registers with scope `/` and controls the page, and Chrome reports the app installable with no manifest errors.
  - **Cache contents:** after learner, child, parent and admin accounts use the app (including direct private API reads), the cache holds **exactly** the allowlist and no account data or session token in any body.
  - **Offline (page and worker):** API requests, an allowlisted file under another query, and an unlisted file are all **refused**, not answered from the cache, while allowlisted files still work. A reload shows the offline page, with no personal data and no fake progress, and the app returns by itself when the connection is back. The open app shows the offline banner.
  - **Server stopped:** the offline page appears, and Try again shows it again (not an old copy of the app). A sign-in attempt says the server cannot be reached and stays signed out.
  - **Signing out:** after signing in, browsing and signing out, nothing of the account is in the cache or on the offline page.
  - **Updates:** a genuine new release (a changed `sw.js` on a copy of the app) is offered and does **not** reload on its own. Tapping Refresh reloads once and leaves only the new cache.
  - **No worker:** with no service worker, or with registration refused, sign-in and the app work with no exceptions and nothing cached.
  - **Install button:** it appears only when the browser offers installation, and taps through to the browser's prompt once.
  - **Console:** no console errors or exceptions while learners, parents and admins use the app.
- **Earlier tests changed:** the 15A test "no service worker caches anything" was removed, because 15B deliberately replaces it with the stricter allowlist tests above. The 15A manifest test no longer expects the manifest to have no icons.
- **Not verified:**
  - **Installation itself:** the browser's install dialog and the installed app window.
  - **Other platforms:** Android or iOS hardware, Safari's Add to Home Screen, Firefox, and update timing on real devices.
  - **Offline emulation:** Chrome's offline mode was applied to the page and to each service-worker target. A worker instance Chrome starts afterwards is not covered by it, so the "try again while still offline" check uses a really stopped server instead.

### Known limitations and decisions still needed

- **No offline learning:** a design for offline learning and synchronisation is a separate decision.
- **One release stamp:** `VERSION` in `sw.js` and the `?v=` stamp in `index.html` must be bumped together for each release (a test fails if they differ).
- **Web fonts offline:** they are not cached (they live on another origin), so offline pages use the system font.
- **No Windows tile:** there are no Windows-specific tile icons or screenshots in the manifest. Richer install sheets on Android (screenshots) would need product imagery.
- **2FA deferred:** the final 2FA review remains deferred to the end of the project, by decision. 15B does not touch 2FA.

## 30. City packs: Mumbai

"I'm New Here" offered Delhi as the only ready city. **Mumbai** is now ready too; Bengaluru, Hyderabad and Chennai still show "Soon".

### What a city pack is

- **The First Week pack (`frontend/content.js`, `PACKS.<city>`):** 7 days, one per everyday situation (greetings, transport, food, shopping, directions, college or work, a real conversation). Each day has a situation, a tip and 4–6 phrases (Devanagari, romanised, literal, natural).
- **Roleplays (`SCENARIOS`):** one per day, each with its own character, place, goal, opening line, suggested replies and the offline reply rules used when no model is configured.
- **Server allowlist (`backend/legacy/ai.py` `SCENARIOS`):** the same scenes, word for word. The server only lets allowlisted scene text reach a model (Phase 14A), and the prompt now names the learner's city ("a real Mumbai taxi driver"). The city is checked against the catalogue first, as before.
- **Catalogue (`cities.is_ready`):** migration `0029_mumbai_pack_ready.sql` marks Mumbai ready. It is data only, with no schema change; `tests/test_schema.py` keeps the catalogue and the frontend in step.

### The Mumbai pack

- **Language:** Hindi as Mumbaikars speak it, with Bambaiya and Marathi touches ("Kasa kay?", "ek cutting", "bindaas", "jhakaas").
- **Days:**
  1. A housing society in Andheri West, including the water timings.
  2. Local trains (fast or slow, Dadar) and taxis by the meter.
  3. A vada pav stall at Dadar.
  4. Bargaining at Colaba Causeway.
  5. A station's East and West sides, and the footbridge.
  6. A first day at an office in BKC.
  7. Monsoon chai on Marine Drive.
- **Roleplays:** seven, `mum_greetings` … `mum_smalltalk`, each with its own Mumbai character.
- **Price checker:** Mumbai prices. Autos and taxis are marked "by meter", so the advice is to ask for the meter rather than to bargain, and train tickets are marked as fixed fares.
- **"Right now" card:** Mumbai suggestions (packed locals, sea-face chai, meters at night).

### What now follows the learner's city

- **Pack screens:** the First Week page and lessons, the onboarding's "coming soon" message and build steps.
- **Roleplay links:** the confidence page's "Practice now", the tutor's practice links, and a roleplay page's "More scenarios" (only the city's own).
- **Home and tools:** the home page's count of roleplay partners, the price checker, and the "Right now" card.

### Tests

- **Packs (`tests/test_city_packs.py`):**
  - **Content:** every ready city has a complete 7-day pack and its own 7 roleplays, one per situation. Mumbai uses no Delhi roleplay and mentions no Delhi place.
  - **Roleplays:** each Mumbai roleplay is complete, and **every suggested reply leads to a real answer**. This found 7 gaps, which were fixed. The taxi answers what was asked.
  - **Server side:** the allowlist equals the frontend's scenes, the AI prompt names Mumbai or Delhi correctly, an unknown city is still refused, and the catalogue marks Mumbai ready.
- **Running app (`tests/frontend/legacy_harness.js` `mumbai_pack_works`, against a live server):**
  - **Mumbai:** the pack and all 7 days render Mumbai content (no Delhi places), with Mumbai prices and vada pav for food. The roleplay and its side panel are Mumbai's only, offline replies use Mumbai places and the meter, the home page counts 7 partners and shows "Right now in Mumbai", and practice links go to Mumbai roleplays.
  - **Delhi:** unchanged.
- **Migration pins:** the existing "latest migration" tests were updated to 0029. The upgrade tests that compare schemas are unchanged, since 0029 is data only.

### Known limitations

- **Bengaluru, Hyderabad and Chennai:** their packs would teach Kannada, Telugu and Tamil, which the app does not have yet (scripts, voices, catalogue languages, level combinations). They need language support before their content.
- **Tutor answers:** the offline tutor's answers (`TUTOR_INTENTS`), the readings, the placement test and the achievements' names are still the shared, Delhi-flavoured ones. The First Week pack, roleplays, prices and "Right now" card are per city.
- **A Delhi quirk:** in Delhi's original auto-rickshaw roleplay, the general "okay" rule matches inside "chaloge", so "Bhaiya, airport chaloge?" skips straight to "Baithiye!". Mumbai's taxi orders its rules to avoid this. Delhi's content was left as it was.

## 31. Destination previews: every state capital and union territory

"I'm New Here" now previews where LingoBuddy is going: all 28 state capitals and the capitals of all 8 union territories. **Delhi** is "Available", **Mumbai** is "In Development" (usable, with an "Early version" note), and the other 32 cards are "Coming Soon" and cannot be picked.

### How it works

- **Display data (`frontend/content.js` `DESTINATIONS`):** 34 cards. Each has an `id`, a `name`, an `emoji`, a `status` (`available`, `in_development` or `coming_soon`), the states and union territories it `serves`, an optional `note`, and an optional `city` that links it to a learning pack. Chandigarh is one card serving Punjab, Haryana and its own territory. Jammu and Kashmir has one card for its two capitals.
- **Learning packs are unchanged:** `CITIES` (kept in step with the database by `tests/test_schema.py`) still decides what can be learnt. A destination can be picked **only** if its status is not `coming_soon` **and** its linked city is ready in `CITIES`, so a mistake in the display data can never enable a city without a pack.
- **The screen (`frontend/app.js` `destinationsGrid`):** the selectable cards first, then a "Coming soon" banner, then the state capitals and the union territories in two groups. Coming-soon cards are `aria-disabled`; tapping one only shows a toast naming the cities you can start in today. Picking Delhi or Mumbai builds the same pack as before.
- **Layout (`frontend/styles.css`):** compact cards, two columns on phones and one below 340px, long names wrap, no horizontal scroll.
- **No schema, data or progress change:** no migration, no API change; a learner's saved city and progress are untouched.

### Tests (`tests/test_destinations.py`)

- **Data:** every state capital and union territory is listed exactly once with the right capital, ids and names are unique, only Delhi and Mumbai are selectable, and every coming-soon destination linked to a pack (Bengaluru, Hyderabad, Chennai) points to a pack that is not ready.
- **Real browser (headless Chrome, phone and laptop widths):** Delhi shows "Available", Mumbai "In Development", 32 cards "Coming Soon" and disabled, the banner and both groups are shown, nothing scrolls sideways. Tapping a coming-soon card (Jaipur, Bengaluru, Kavaratti, Chandigarh) picks nothing. Delhi and Mumbai still offer their languages and build "Your First Week in Delhi/Mumbai".

### Also in this change

- **PWA browser test made deterministic:** the "back online" step of `tests/test_pwa_browser.py` sometimes failed (about 1 run in 5) because Chrome's offline emulation does not always reach a newly started service worker. When the page has not returned on its own, the test now lifts the emulation again and taps the offline page's Try again, then still requires the app to come back. `tests/test_pwa.py` now checks, without a browser, that the offline page returns to the app by itself when the connection comes back.
- **Release stamp bumped** in `index.html` and `sw.js`, as for every release that changes static files.

## 32. City packs: Mumbai in Marathi

Mumbai can now be learnt in **Marathi** as well as Hindi and English ("I'm New Here" offers Hindi · Marathi · English for Mumbai). Before, the language choice only changed how the same Hindi phrases were shown (Devanagari, romanised or English); Marathi is a language of its own, with its own content.

### How it works

- **Catalogue:** migration `0030_marathi_for_mumbai.sql` (data only) adds Marathi (`mr`, मराठी, `mr-IN`) to `languages` and makes Mumbai's languages Hindi, Marathi, English. It adds no CEFR levels, so Marathi is not yet a target for the server curriculum; it does appear in the profile's "I speak" list. `tests/test_schema.py` keeps the catalogue and `frontend/content.js` (`LANGUAGES`, `CITIES`) in step.
- **Pack per language (`frontend/content.js` `LANGUAGE_PACKS.mumbai.mr`):** a 7-day Mumbai Marathi First Week pack (35 phrases), same shape as every pack. `hi` holds the Devanagari text, which here is Marathi. `Engine.pack()` picks the learner's city in the language they chose, else the city's own pack, so lessons, flashcards, practice links and "More scenarios" follow the language.
- **Roleplays:** seven Marathi scenes (`mum_mr_greetings` … `mum_mr_smalltalk`) with their own characters (Joshi kaka, Shinde kaka, Ganesh bhau, Pawar kaka at Dadar's Ranade Road market, Kulkarni kaku, Sayali, Aditya) and offline rules for romanised Marathi. They are on the server's scene allowlist, word for word.
- **Speech:** the mic listens in `mr-IN` for a Marathi learner, and phrases are read by a Marathi voice where the device has one, otherwise by a Hindi voice (same script).
- **AI:** a Marathi roleplay is sent as `language: "Marathi"`; the server accepts it (`backend/legacy/ai.py`) and the prompt asks the character for "natural romanised Marathi". Hindi prompts are unchanged.
- **Also in Marathi:** the fair-price advice (ask for the meter, bargain, train ticket), the "Right now" card, and the roleplay input's hint.
- **Only the city's own languages:** `Engine.language()` is the language the learner chose if their city offers it, else the city's first language; the pack, speech, AI request and every Marathi-aware screen use it. On "I'm New Here", switching city clears a language the new city does not offer, and Build only accepts one of the chosen city's languages (its message lists them). This fixed a checkpoint finding: picking Mumbai, then Marathi, then Delhi built "Delhi in Marathi", with a Marathi mic, Marathi price advice and a Marathi roleplay hint on Delhi's content.
- **The server checks the pair too:** a saved state (`PUT /api/state/…`) whose city is in the catalogue must have one of that city's languages (`backend/legacy/state.py`, from `city_languages`), and `/api/ai` refuses a Marathi request for a city that does not offer Marathi (both 422 on `language`). A state holding only one of the two fields is still accepted. So that an older saved pair never stops a learner's progress from saving, the frontend repairs it on the next save (`Engine.save()` keeps `Engine.language()`); the rest of the state is kept as it was.

### Tests

- **Content (`tests/test_city_packs.py`):** the Marathi pack is complete (7 days, one per situation, 4–6 phrases each), it is Marathi rather than the Hindi pack again (only "Kasa kay?" and "Ekdum jhakaas!" are shared, and they are Marathi already), it has its own 7 roleplays with no Delhi places, each roleplay is complete, every suggested reply leads to a real answer, and the taxi answers what was asked. A language pack can only exist for a ready city and one of its languages.
- **Server:** the catalogue and Mumbai's languages agree with the frontend, Delhi's are unchanged, a Marathi roleplay prompt asks for Marathi (and a Hindi one still for Hinglish), and an unknown language is still refused.
- **Running app (`tests/frontend/legacy_harness.js` `mumbai_in_marathi_works`):** the pack and all 7 days render Marathi, with no Hindi pack phrases; the roleplay, side panel, home page, practice links, speech language and flashcards are Marathi; the AI request asks for Marathi and the server accepts it; switching back to Hindi gives the Hindi pack.
- **Real browser (`tests/test_marathi_browser.py`):** Mumbai offers the three languages at phone and laptop widths (Delhi is unchanged); picking Marathi builds the Marathi pack; the price advice and a roleplay reply are in Marathi. Switching city after picking Marathi builds nothing until a language the new city offers is picked, and a saved combination a city does not offer (Delhi + Marathi, Mumbai + Hinglish) falls back to that city's first language.
- **Pins:** the "latest migration" tests move to 0030 and the language count to 12. The upgrade tests that compare schemas are unchanged, since 0030 is data only.

### Known limitations

- **Native review:** the Marathi was written for this pack and has not yet been reviewed by a native speaker.
- **Tutor in Hindi:** the offline tutor's answers (`TUTOR_INTENTS`) and AI tutor answers stay in Hindi for everyone. The tutor page says so to a Marathi learner.
- **Gendered verbs:** the learner's phrases use the masculine form ("mi navin aalo aahe"), as the Hindi pack does ("main naya aaya hoon"); the feminine form ("aale aahe") is understood in roleplays but not taught yet.
- **Flashcard progress:** cards are identified by day and position, so a learner who switches between Hindi and Marathi shares review history between the two packs (as Delhi and Mumbai already do).

## 33. Completing Mumbai

Mumbai was usable but not product-ready. This pass audited it and fixed what kept it from being consistent. Mumbai stays labelled
**In Development**; native-speaker approval is a separate release gate (`docs/CONTENT_REVIEW.md`).

### Content review (`docs/CONTENT_REVIEW.md`)

- **Review status in the data:** `content.js` `CONTENT_REVIEW` records `awaiting_native_review` for Mumbai Hindi and Marathi. The First Week
  page and every lesson show "Early version: … awaiting review by a native speaker". Only a real review may change it.
- **Gender:** characters no longer assume a male learner, suggested replies are gender-neutral where a natural form exists, and a learner
  phrase that changes with gender shows the feminine form too ("Women say …", with its own 🔊, from the phrase's `fem`).
- **Marathi without Hindi fillers:** "achha", "yaar" and "saheb" are gone from the Marathi roleplays.

### Each pack keeps its own progress

- **Before:** flashcard ids (`d1-0`…) and completed days were shared by every pack, so finishing Delhi's day 3 marked Mumbai's day 3 done and
  Delhi's review history was applied to Marathi cards.
- **Now:** `Engine.packKey()` names the pack ("" for Delhi, `mumbai`, `mumbai:mr`). Delhi keeps its keys (`completedDays`, `d1-0`), so existing
  progress means what it did. Every other pack has its own days (`packDays[key]`) and prefixed card ids (`mumbai:mr:d1-0`). The English view
  shares the Hindi pack's progress because it shows the same phrases.
- **Server:** `packDays` is a validated state field (`backend/legacy/state.py`): pack-shaped keys only, at most 20 packs, day lists as for
  `completedDays`.
- **Not migrated:** Mumbai progress saved before this change sits in the shared fields and now counts as Delhi's. It could not be told apart.

### The tutor and shared content follow the city and language

- **Data:** `content.js` `LOCAL_CONTENT[city][language]` holds the tutor's ready-made answers, places, starters, greeting, glossary and politeness
  rules, the readings, the level check and achievement names. The English view uses the Hindi entry. A city without an entry uses the shared
  (Delhi) content exactly as before.
- **Mumbai:** local trains instead of the Delhi metro, meters, vada pav, Colaba/Dadar bargaining, Mumbai readings ("Asha in Mumbai",
  "A snack at Dadar"), "Mumbai foodie", "Meter pro".
- **Marathi:** answers in Marathi, a Marathi-only glossary, Marathi place endings ("Dadarla", "Bandryala"), Marathi politeness rules and
  "Said your first Marathi phrase".
- **AI tutor:** a Marathi learner's tutor requests ask for Marathi too. The server's tutor prompt then asks for romanised Marathi; the Hindi
  prompt is unchanged. Marathi is still refused for a city that does not offer it.
- **Honest audio:** a Marathi learner whose device has no Marathi voice is told once that a Hindi voice is reading (same script).

### Marathi in the server curriculum (`0031_marathi_lessons.sql`, data only)

- **Catalogue:** Marathi joins `language_levels` at A1 and A2, like the others, so a profile can target it and the admin CMS can author it.
- **Content:** 7 published A1 lessons, generated from the Marathi First Week pack. They hold its 35 phrases plus the feminine form, 14 words with
  an example each, 3 grammar notes ("-a" polite requests, "ka?" questions, "-la" for places) and 21 exercises (meaning, translation in Roman or
  Devanagari, fill in a word). The office lesson is for teens and adults, as in Hindi. It passes the content sweep with no findings.
- **Unchanged:** Hindi learners get exactly their 7 lessons; another language's lesson is a 404 for them.
- **Not yet in Marathi:** situations (server roleplays), listening activities, speaking prompts and the adaptive semantic grader (its lexicon is
  Hindi only, so it reports "unsupported"). The situations and listening pages say "No … for this language and level yet". Marathi B1 and above
  are not offered.

### Tests

- **Content:** `tests/test_city_packs.py` covers the local content for both languages (every topic answered, readings and level check valid,
  no Delhi places, the Marathi has no Hindi markers or danda), the review status matching the review document, feminine forms, characters not
  assuming a male learner, and the tutor prompt in both languages.
- **Running app:** `tests/frontend/legacy_harness.js` scenarios `each_pack_keeps_its_own_progress` and
  `learn_tools_follow_the_city_and_language`. The Marathi scenario now checks the tutor in Marathi, where it used to check the "Hindi for now"
  note.
- **Server curriculum:** `tests/test_marathi_lessons.py` covers the catalogue, the 7 lessons matching the pack, Hindi learners unaffected, age
  targeting, grading in both scripts, progress, the content sweep, and the admin listing, authoring and publishing of a Marathi lesson
  (Hindi vocabulary refused). It also checks the empty situations and listening.
- **State:** `tests/test_legacy_hardening.py` validates `packDays`.
- **Adjusted tests:** tests that counted every lesson, exercise or vocabulary item now count the Hindi seed they were written for, plus
  Marathi's explicitly. The shared helper `tests/pers.py` `exercise_ids` picks Hindi by default (slugs are unique only per language).
  Migration pins move to 0031.

## 34. Mumbai's Marathi learning flows

Mumbai's Marathi now runs end to end through A2 on the existing relational architecture. Mumbai stays labelled **In Development**, and the
content is **AI-assisted editorial review only; native review pending** (`docs/CONTENT_REVIEW.md`).

### Curriculum (`0032_marathi_curriculum_a1_a2.sql`, data only)

- **Source:** `tools/marathi_curriculum_data.py` (the content) and `tools/gen_marathi_curriculum.py` (the SQL). The output is committed, and a
  released migration is never edited.
- **A1 (11 lessons):** the 7 First Week lessons of 0031, then numbers and money, time and days, about me, and help and health.
- **A2 (10 lessons):** the past, plans, favours, likes, comparing, travel, problems in a shop, work and study, problems at home, and a longer
  conversation.
- **Each lesson:** 5–6 phrases, plus the feminine form of any gendered one as its own item. It also has 1–2 words with an example and three
  exercises (what a phrase means, translate it in Roman letters or Devanagari, fill in a word).
- **Grammar notes:** 4 at A1 and 5 at A2: polite "-a" requests, "ka?", "-la", telling the time, the past, the future, "…al ka?", "aavadta"
  and "-peksha".
- **Totals:** 155 items, 63 exercises.
- **Wiring:** a profile at A2 sees A1 then A2. The office lessons and situation are for teens and adults, as in Hindi. Admins list, edit,
  validate, publish, unpublish, archive and restore Marathi content through the existing CMS.

### Server roleplays and listening (`0033_marathi_situations_listening.sql`, data only)

- **Situations:** 12 (A1 8: the First Week roleplays and Getting help; A2 4: a problem in your flat, a bus to Pune, exchanging a shirt,
  planning a trip). Steps study the lesson phrases, answer the partner's opening line, reply to the partner and, for two, translate a phrase.
  The existing roleplay service runs them unchanged.
- **Language of the roleplay:** the scene greets in the language of the roleplay ("Namaskar" for Marathi). The built-in (offline) character
  praises in Marathi ("Chhan!", "Ekdum barobar!", "Shabbas!"), where it used Hindi for every learner. Hindi's lines are unchanged.
- **Listening:** 42 activities, a "what does it mean?" and a "which phrase?" for every Marathi lesson, using the existing schema. No audio files
  are shipped: the browser speaks the phrase in `mr-IN` (the `locale` of the audio source).

### Grading typed and spoken answers

- **Semantic grader:** `backend/adaptive/lexicon.py` now has one lexicon per language (`for_language`). Hindi's data is exactly what it was.
  Marathi's has its own function words, same-meaning groups and spelling folds, so Hindi words are never Marathi synonyms or the reverse.
- **Typed answers:** lessons, situations and roleplay exact matches compare `textnorm.answer_key(text, language_code)`.
  - **Hindi and every other language:** exactly `normalize`, as before.
  - **Marathi:** also folds the documented romanisation variants: long vowels (aa/a, ee/i, oo/u), doubled letters, w/v, a final h, and
    zh/jh/z. Wrong words, Hindi phrasing and incomplete answers are still refused.
  - **Unchanged:** empty, oversized and malformed answers are still refused by the existing validation.
- **Adaptive practice:** a phrase's feminine form is never offered as a second, near-identical wrong option.

### Speaking

- **Capabilities up front:** `GET /api/speaking/prompts` adds `capabilities`: the language, its locale, `transcription` and `pronunciation`
  (each "available", "unsupported_language" or "not_configured") and `alternatives: ["typed"]`. The existing `stt` and `pronunciation`
  fields are unchanged.
- **Whisper:** it declares its published language list (Marathi included) instead of "any language".
- **Voice practice:** it says when recognition doesn't support the language. It also offers a typed check, labelled as comparing letters, not
  hearing you.
- **Prototype phrase practice:** for Marathi it no longer shows an invented "estimate" score. Without a transcript it says nothing was
  assessed; with one it shows a word check, labelled as not a pronunciation score. A browser that can't recognise Marathi
  (`language-not-supported`) is told to type instead.

### Honest audio

- **The rule:** `Engine.hasVoice(locale)` says whether the device has a voice for the language, and `Engine.speak(…, {locale})` uses only that
  language's voice. A Marathi phrase is never read by a Hindi voice.
- **Without a Marathi voice:** listening shows a labelled transcript ("Transcript mode (text, not audio)"). The kids game, voice practice and
  the First Week pack say there is no Marathi voice and show the words.
- **Hindi:** keeps its old fallbacks.

### Review metadata (`0034_content_reviews.sql`)

- **The table:** `content_reviews(language_id, editorial_status, native_review_status, last_editorial_reviewed_at, known_limitations)`, with
  CHECKs so nothing but the known values can be stored.
- **Marathi's row:** `ai_assisted_review`, `pending`.
- **API:** `GET /api/content-review` returns the learner's own language's record, or null where none is recorded (Hindi).
- **Where it shows:** the lessons, situations, listening and voice pages show it.
- **The First Week packs:** `frontend/content.js` `CONTENT_REVIEW` uses the same four fields.

### Tests

- **Server flows:** `tests/test_marathi_learning.py` covers counts, progression, grading variants and Hindi exactness, roleplay discovery,
  turns, hints and completion offline, listening, speaking capabilities, the review record, CMS lifecycle, plan, recommendations and
  adaptive practice.
- **Editorial lint:** `tests/test_mumbai_content_lint.py` checks scripts, Hindi leakage, duplicates, one spelling per word, feminine forms,
  review consistency and the sourced fares.
- **Browser:** `tests/test_marathi_flows_browser.py` covers the review banner, transcript mode with and without a Marathi voice, the typed
  check, a server roleplay in Marathi, no invented score, Delhi unchanged, and the admin console at 390 px and 1366 px.
- **Adjusted older tests:** those that assumed only Hindi content exists now look up Hindi explicitly (`tests/pers.py`, `tests/aih.py`,
  `tests/adm.py` helpers and seed tests) and count Marathi separately. Schema snapshots add `content_reviews`, and migration pins move to 0034.

### Known limitations

- **Native review:** none has happened; the content may read unnaturally to a fluent speaker.
- **No real speech assessment for Marathi:** Marathi is assessed only by what a recogniser heard. There is no acoustic pronunciation provider
  for any language.
- **Device dependence:** browser speech recognition and voices for Marathi depend on the device and browser; the app detects and says so.
- **Beyond A2:** the curriculum ends at A2, and B1 and above are not offered for Marathi.
- **Listening format:** activities are single phrases; there are no longer dialogues or comprehension passages on the server.
- **Fares:** checked against press reports of the September 2026 revision, not the official order.

## 35. Mumbai is available

On 2026-10-18 Mumbai's destination status changed from `in_development` to `available` (`frontend/content.js` `DESTINATIONS`), at the product
owner's request, after the work of sections 30–34. Nothing else about Mumbai's content or rules changed.

- **The card stays honest:** a city with a review record that a native speaker has not approved (`CONTENT_REVIEW`) shows "Native-speaker review
  pending: phrases may still change" on its card, whatever its status. This is data-driven (`reviewPending` in `frontend/app.js`), so Delhi,
  which has no record, is unchanged, and the note goes away by itself once a review is recorded as `approved`.
- **The review state is unchanged:** `editorial_status: ai_assisted_review`, `native_review_status: pending`, and every in-app note.
  "Available" means the city can be learnt; it does not mean the content has been validated (docs/CONTENT_REVIEW.md, "Availability decision").
- **Still not done:** the native review, the official-tariff fare check, a real pronunciation provider, and B1 and above.
- **Tests:** `tests/test_destinations.py` checks Delhi and Mumbai both available, Mumbai's card saying its review is pending, Delhi's card
  unchanged and the other 32 still "Coming Soon".

## 36. Marathi B1, sourced fares, and pronunciation scoring research

### Marathi B1 (`0035_marathi_b1.sql`, data only)

- **Catalogue:** Marathi joins B1, so a profile can choose it.
- **Content:** 6 lessons (obligations, if and when, can and can't, opinions, complaints, telling what happened), 44 items, 5 grammar notes
  ("…ayla pahije / …ava lagel", "jar … tar", "yeta / shak-", "mala vaatta ki", "jo … to / jevha … tevha / … ki"), 18 exercises.
- **Practice:** 2 situations (a complaint about the water, late for a meeting) and 12 listening activities.
- **Generator:** the same one as A1 and A2 (`tools/gen_marathi_curriculum.py`), refactored so 0032 and 0033 regenerate byte for byte.
- **Totals:** Marathi now has 27 lessons, 199 items, 81 exercises, 14 grammar notes, 14 situations and 54 listening activities.
- **Levels:** B2 and above are not offered. Like everything else, B1 is AI-assisted editorial review only, native review pending.

### Fares

- **Sources:** the September 2026 auto and taxi revision and the 25% night surcharge (midnight to 5 am) are confirmed by several independent
  outlets (docs/CONTENT_REVIEW.md). The MMRTA order itself is not published online, so they remain secondary sources.
- **Test:** the fare test (`tests/test_mumbai_content_lint.py`) pins the ranges to them.

### Pronunciation scoring: researched, not built

- **Azure AI Speech:** its pronunciation assessment (Microsoft's documentation, checked 2026-10-18) supports Hindi (hi-IN) and Indian English
  but **not Marathi**, so it cannot score Marathi at all.
- **Audio format:** its REST API takes WAV or OGG, while Chrome's MediaRecorder records WebM, so it would also need server-side transcoding the
  project does not have.
- **Decision:** an adapter that fails for most recordings and cannot be tried without a paid account was not added. The app keeps reporting
  pronunciation scoring as unavailable, and Marathi speaking stays a transcript-based word check plus the typed check.
- **What a real provider needs:** a service that supports mr-IN, plus WAV capture or transcoding.

## 37. City packs: Bengaluru in Kannada

- **Catalogue (`0036_kannada_for_bengaluru.sql`, data only):** Kannada (`kn`, ಕನ್ನಡ, `kn-IN`) joins the languages; Bengaluru is learnt in
  Kannada, then English, and its pack is ready. Hindi is not offered for Bengaluru: no Bengaluru Hindi content exists. The server refuses a
  saved state pairing Bengaluru with any other language, as it does for every city (`city_languages`).
- **Destination:** "In Development", with its other name (Bangalore), an introduction and a First Week preview (`DESTINATIONS` `alt`,
  `intro`, `preview`), shown only for a destination that has them, so Delhi's and Mumbai's cards are unchanged. Changing city clears a
  language the new city does not offer; an old saved pair falls back to Kannada and is repaired on the next save.
- **Content (`content.js`):** `PACKS.bengaluru` (7 days, Kannada script in the `hi` field like every pack), `SCENARIOS.blr_*` (7 offline
  roleplays, also on the server's allowlist), and `LOCAL_CONTENT.bengaluru.kn`: tutor, readings, level check, achievements, plus two new
  optional fields, `rightNow` (the home card's time slots) and `priceSay` (the fair-price phrases). The English view uses the same pack and
  the same local content.
- **One rule for the pack's language:** `Engine.packLanguage()` is the learner's language, or for the English and Hinglish views the city's
  own (Hindi in Delhi and Mumbai, Kannada in Bengaluru). It decides the review record, the local content, the speech locale (`kn-IN`), the
  voice and the AI language label ("Kannada"). Any language but Hindi is played only by a voice of its own and practised with the word check,
  never a score; this also removed an estimated percentage that the prototype's roleplay feedback still showed for Marathi.
- **Server:** `/api/ai` accepts "Kannada" only for a city that offers `kn` (`legacy_ai.CITY_LANGUAGE_CODES`). It asks for romanised Kannada,
  and the tutor asks for Kannada script where Hindi and Marathi use Devanagari.
- **Fonts:** Noto Sans Kannada joins Noto Sans Devanagari in the Google Fonts link and the `--deva` stack.
- **Prices:** `BENGALURU_PRICES`: auto by meter, Namma Metro (fixed), kurta, T-shirt, masala dosa, filter coffee. Sources are in
  docs/CONTENT_REVIEW.md.

## 38. Kannada learning on the server

- **Curriculum (`0037_kannada_a1.sql`, data only, generated):** Kannada joins the CEFR catalogue at A1 only, with its `content_reviews` row
  (AI-assisted, native review pending). It has 9 lessons: the 7 First Week lessons, built from the pack, plus numbers and money, and help and
  health. They hold 66 items, 3 grammar notes (polite "-i" requests, "-aa" questions, "-kke / -ige / -ge"), 27 exercises, 8 situations and
  18 listening activities.
- **Generator:** `tools/gen_kannada_curriculum.py` reuses the Marathi generator's SQL writers, pointed at Kannada (`LANG`, `LANGUAGE_NAME`,
  `SCRIPT_NAME`). Those names were added to the Marathi generator without changing its output: 0032, 0033 and 0035 regenerate byte for byte.
- **Grading:**
  - **Lexicon:** `backend/adaptive/lexicon.py` has a Kannada lexicon (`kn` in `SUPPORTED`).
  - **Script detection:** each lexicon says which script is its own (`Lexicon.native`): Devanagari for Hindi and Marathi, Kannada script for
    Kannada. The semantic grader and `textnorm.answer_key` compare a learner's text only with accepted answers in the same script.
  - **Romanised folding:** on top of the shared rules, "th"→"t", "dh"→"d" and "ai"→"ay" (thumba / tumba, aithu / aaytu).
  - **Kannada-script folding:** long vowel signs fold into the short ones, and the zero-width joiners of loanwords are dropped before the text
    is split (`Lexicon.prepare`).
  - **Isolation:** Hindi stays exact and Marathi keeps its own rules (tests pin both).
- **Speaking:** the word check (`content_match.script_of`) recognises Kannada script and compares it with the phrase's own text.
  Capabilities report Kannada like any language. Whisper's published list includes Kannada, and there is no pronunciation provider. The
  voice page's typed check says "Roman letters or Kannada script".
- **Roleplay:** the built-in character greets with "Namaskara" and praises in Kannada ("Chennaagide!", "Sakkath!", "Bhale!").

## 39. Kannada A2 and B1, and Bengaluru is available

- **Curriculum (`0038_kannada_a2_b1.sql`, data only, generated):** Kannada joins A2 and B1 with Marathi's topics, set in and around Bengaluru.
  - **A2 (10 lessons):** the past, plans, favours, likes, comparing, a trip to Mysuru, shop problems, work and study, problems at home, a
    longer conversation.
  - **B1 (6 lessons):** having to, if and when, can and can't, opinions, complaints, telling what happened.
  - **Grammar:** 9 notes ("-e / -dri" past, "-tini / -ona", "…tira?", "nanage … ishta", "-ginta", "-beku", "-dre / -aaga",
    "baratte / -oke aagutte", "anta").
  - **Practice:** 48 exercises, 6 situations (a power cut, a bus to Mysuru, exchanging a shirt, planning a trip, a water complaint, late for a
    meeting) and a listening pair for every new lesson.
  - **Totals:** Kannada now has 25 lessons, 178 items, 75 exercises, 12 grammar notes, 14 situations and 50 listening activities. 0037
    regenerates byte for byte.
- **Status:** Bengaluru's destination is "Available" at the product owner's request (docs/CONTENT_REVIEW.md). Like Mumbai's, its card says
  "Native-speaker review pending", because its review record is not approved.
- **Tests:** `tests/test_kannada_learning.py` checks the levels, the order of lessons a B1 learner gets, upper-level grading and an A2/B1
  roleplay. `tests/test_destinations.py` and `tests/test_bengaluru_browser.py` check the Available card with its review note.

## 40. City packs: Chennai in Tamil, available

Chennai is built the same way as Bengaluru (sections 37–39), with Tamil.

- **Catalogue (`0039_tamil_for_chennai.sql`, data only):** Tamil (`ta`, தமிழ், `ta-IN`) joins the languages, Chennai is learnt in Tamil then
  English, and its pack is ready.
- **Destination:** "Available" at the product owner's request, with its other name (Madras), an introduction and a First Week preview. Like
  the other available cities, the card says "Native-speaker review pending".
- **Content (`content.js`):** `PACKS.chennai` (7 days of spoken Chennai Tamil), `SCENARIOS.chn_*` (7 roleplays, also on the server's
  allowlist) and `LOCAL_CONTENT.chennai.ta` (tutor, readings, level check, achievements, `rightNow`, `priceSay`).
  - **Prices (`CHENNAI_PRICES`):** the auto item is an agreed fare, not a meter fare, because Chennai's official meter fare dates from 2013
    and drivers quote their own. Metro tokens cost ₹10–50.
- **Engine and app:** the rules from section 37 cover Tamil with a few additions: the speech locale `ta-IN`, the AI language label "Tamil",
  Tamil words in the English-reply check, the "please read" line, the language card, and Noto Sans Tamil in the font stack.
- **Server:** `/api/ai` accepts "Tamil" only for a city that offers `ta`. The tutor asks for Tamil script, and the built-in character greets
  with "Vanakkam" and praises in Tamil.
- **Curriculum (`0040_tamil_a1.sql`, `0041_tamil_a2_b1.sql`, generated by `tools/gen_tamil_curriculum.py`):** Tamil from A1 to B1, with the
  same topics as Kannada: 25 lessons, 177 items, 12 grammar notes, 75 exercises, 14 situations and 50 listening activities. The generator
  reuses the Marathi generator's writers, as the Kannada one does. 0032–0038 are unchanged.
- **Grading:**
  - **Lexicon and script:** a Tamil lexicon (`ta` in `SUPPORTED`) whose own script is Tamil (`has_tamil`).
  - **Romanised folding:** "th"→"t" and "dh"→"d" (thanni / tanni). "zh" (ழ) is **not** folded, because "mazhai" (rain) and "malai" (hill)
    are different words.
  - **Tamil-script folding:** long vowel signs fold into short ones, and joiners are dropped.
  - **Word check:** the speaking word check recognises Tamil script, and voice practice's typed check names it.
- **Tests:** `tests/test_chennai_content.py`, `tests/test_tamil_learning.py`, `tests/test_chennai_browser.py` (375, 390 and 1366 px) and the
  harness scenario `chennai_in_tamil_works`.

## 41. More Chennai practice

- **Migration (`0042_tamil_more_practice.sql`, data only, generated):**
  - **Lessons:** two more A1 lessons, Time and Days and About Me (sort orders 10 and 11), with their words, exercises and a listening pair
    each.
  - **Situations:** four more: meet your neighbours and paying at a provision store (A1), a cab to the airport (A2), and looking for a flat
    (B1).
- **Generator (`more_practice_sql` in `tools/gen_tamil_curriculum.py`):** the new lessons' multiple-choice options come from all eleven A1
  lessons, so the A1 writer runs over all of them and keeps only the new lessons' statements. 0040 and 0041 regenerate byte for byte.
- **Totals:** Tamil now has 27 lessons, 191 items, 81 exercises, 12 grammar notes, 18 situations and 54 listening activities. That matches
  Mumbai's Marathi in lessons and listening and has more server roleplays (18 against 14); `tests/test_tamil_learning.py` pins this.

## 42. City packs: Puducherry, in Tamil and French

Puducherry is learnt in Tamil, French or English. It is the first city with a language written in Roman letters.

- **Catalogue (`0043_puducherry.sql`, data only):** Puducherry joins the cities, learnt in Tamil, French, English (French was already in the
  catalogue).
- **Destination:** "Available" at the product owner's request, with its other name (Pondicherry), an introduction and a preview.
- **Content (`content.js`):** `PACKS.puducherry` (Tamil) and `LANGUAGE_PACKS.puducherry.fr` (French), 7 roleplays each (`pdy_*`,
  `pdy_fr_*`), and `LOCAL_CONTENT.puducherry.ta` and `.fr`.
  - **French phrase fields:** `hi` is the French as written, `roman` the same without accents, and `pron` an English-speaker's pronunciation
    guide.
  - **French local content:** not graded, so `roman` is the French itself.
- **Shown once:** French has no second script, so a phrase is never shown twice. The line under a phrase is its `pron` if it has one, else
  its `roman` only when that differs from `hi` (`alt()` in app.js). The "show to a local" card shows French as written.
- **Accents:**
  - **Engine:** the roleplay engine and the practice word check ignore Latin accents (`noAccents` in engine.js), so "très" and "tres" match
    the same rule. The rules' keywords are written without accents.
  - **Server:** the server's word check (`content_match`) and voice practice's typed check ignore them too.
  - **Other scripts:** their vowel signs are untouched.
- **Engine and app:** the speech locale is `fr-FR` and the AI label "French". A French phrase is played only by a French voice, and practice
  is the word check, never a score. The "please read" line says "Merci de lire".
- **Server:** `/api/ai` accepts "French" only for Puducherry. Its prompt asks for natural French, not "romanised", and keeps the accents. The
  built-in character greets with "Bonjour" and praises in French.
- **French A1 (`0044_french_a1.sql`, generated by `tools/gen_french_curriculum.py`):**
  - **Content:** 9 lessons, 66 items, 3 grammar notes ("vous" and "tu", questions by intonation, masculine and feminine), 27 exercises,
    8 situations and 18 listening activities.
  - **Items:** each item keeps its accents in `text` and stores the unaccented form as its `pronunciation`. Both are accepted, and the
    translation prompts say "Accents are optional".
  - **Lexicon:** `fr` folds accents and case. Its own script is "none", so every text is compared as Roman letters.
- **Tamil for Puducherry (`0045_tamil_puducherry.sql`):** an A2 lesson (A Weekend in Puducherry) with its listening pair, and three
  situations set there. Tamil content is per language, so Chennai's learners see it too.
- **Generators:** the Marathi generator gained `TRANSLATE_NOTE` and drops a repeated answer when an unaccented form equals the phrase.
  0032–0042 regenerate byte for byte.

## 43. City packs: Jaipur and Lucknow, in Hindi

Jaipur and Lucknow are learnt in Hindi or English. They are the first new cities whose language (Hindi) the app already taught.

- **Catalogue (`0046_jaipur_lucknow.sql`, data only):** both cities join, learnt in Hindi, then English.
- **Destinations:** "Available" at the product owner's request, with their other names ("The Pink City", "The City of Nawabs"), an
  introduction and a preview.
- **Content (`content.js`):** `PACKS.jaipur` and `PACKS.lucknow`, 7 roleplays each (`jpr_*`, `lko_*`, also on the server's scene allowlist),
  `LOCAL_CONTENT.jaipur.hi` and `.lucknow.hi`, and their review records. The helper `hiP` builds a phrase.
- **Hindi works as it does for Delhi and Mumbai:** the voice, the AI's "Hindi" label and the shared Hindi glossary are unchanged. The tutor
  merges the city's own glossary with the shared one (no `glossaryOnly`).
- **Prices (`app.js`):** `JAIPUR_PRICES` and `LUCKNOW_PRICES`. The metro items are fixed fares, and the auto items are agreed fares.
- **Server content:** Hindi lessons, situations and listening are per language, so both cities use the existing Hindi curriculum. City
  lessons and Hindi A2/B1 are a follow-up.

## 44. City packs: Kolkata, in Bengali

Kolkata is learnt in Bengali or English. Bengali is the sixth language of the city packs and the fourth with a script of its own.

- **Catalogue (`0047_kolkata_bengali.sql`, data only):** Bengali joins the languages (`bn`, বাংলা, `bn-IN`), and Kolkata joins the cities,
  learnt in Bengali, then English.
- **Destination:** "Available" at the product owner's request, with its other name (Calcutta), an introduction and a preview.
- **Content (`content.js`):** `PACKS.kolkata`, 7 roleplays (`kol_*`, also on the server's scene allowlist), `LOCAL_CONTENT.kolkata.bn` (helper
  `bnP`) and its review record. No feminine forms: Bengali verbs do not change for gender.
- **Engine and app:** the speech locale is `bn-IN` and the AI label "Bengali". A Bengali phrase is played only by a Bengali voice, and
  practice is the word check, never a score. `BN_WORDS` keeps a Bengali reply from being taken for English. The "please read" line says
  "অনুগ্রহ করে পড়ুন", and voice practice names "Bengali script".
- **Server:** `/api/ai` accepts "Bengali" only for Kolkata, and asks for romanised Bengali with the Bengali script in the tutor's `hi` field.
  The built-in character greets with "Nomoshkar" and praises in Bengali.
- **Grading (`lexicon.py`, `textnorm.py`, `content_match.py`):** a `bn` lexicon folds "chh" → "ch", "sh" → "s", "th" → "t" and "dh" → "d" in
  Roman letters, and the long vowel signs and the nukta in Bengali script. "Na" is not a stop word. Typed answers fold the same way, and the
  speaking word check compares Bengali script with the phrase's own text.
- **Bengali A1 (`0048_bengali_a1.sql`, generated by `tools/gen_bengali_curriculum.py`):** 9 lessons, 64 items, 3 grammar notes (polite
  requests, questions, "in / at" endings), 27 exercises, 8 situations and 18 listening activities.
- **Bengali A2 and B1 (`0049_bengali_a2_b1.sql`, same generator):** 10 A2 and 6 B1 lessons on the topics of Kannada's and Tamil's (a train to
  Shantiniketan instead of a bus to Mysuru), 9 grammar notes (the past in -lam, the future in -bo, "-te parben?", "bhalo lage", "-er cheye",
  "-te hobe", "-le" and "jokhon", "-te pari", "-te bollo"), 48 exercises, 6 situations and 32 listening activities. The other generators
  still regenerate their migrations byte for byte.
- **Language names:** the review banner names a language from the app's own catalogue (`LANGUAGES`) first, so `bn` is "Bengali" even where a
  browser calls it "Bangla" (`profile.js` `languageName`).
- **Font:** Noto Sans Bengali joins the Google Fonts link and the `--deva` font stack.
- **Prices (`app.js`):** `KOLKATA_PRICES`. The metro is a fixed fare and the yellow taxi goes by the meter (its range is an estimate).

## 45. City packs: Hyderabad, in Telugu and Urdu

Hyderabad is learnt in Telugu, Urdu or English. Urdu is the first language the app shows right to left.

- **Catalogue (`0050_hyderabad_telugu_urdu.sql`, data only):** Telugu (`te`, తెలుగు, `te-IN`) and Urdu (`ur`, اردو, `ur-IN`) join the languages,
  Hyderabad's learning languages become Telugu, Urdu, English and the city is ready. Every city in the catalogue is now ready.
- **Destination:** "Available" at the product owner's request, with its other name (The City of Pearls), an introduction and a preview.
- **Content (`content.js`):** `PACKS.hyderabad` (Telugu) and `LANGUAGE_PACKS.hyderabad.ur` (Urdu), 7 roleplays each (`hyd_*`, `hyd_ur_*`, on the
  server's scene allowlist), `LOCAL_CONTENT.hyderabad.te` and `.ur` (helpers `teP`, `urP`) and their review records.
- **Right to left:** phrase text (`.deva`) has `unicode-bidi: plaintext`, so each line takes the direction of its own text: Urdu is drawn right
  to left, Roman letters and every other script left to right, with no layout change elsewhere. Noto Sans Telugu and Noto Nastaliq Urdu join
  the fonts.
- **Engine and app:** the speech locales are `te-IN` and `ur-IN` and the AI labels "Telugu" and "Urdu". Each language is read only by its own
  voice (a Hindi voice never reads Urdu), and practice is the word check, never a score. `TE_WORDS` keeps a Telugu reply from being taken for
  English; romanised Urdu is already covered by the Hindi words.
- **Tutor fix:** the tutor's destination search now needs "to" to be a whole word, so "an auto to Golconda" finds Golconda, not "To Golconda".
- **Server:** `/api/ai` accepts "Telugu" and "Urdu" only for Hyderabad, asks for romanised text with the language's own script in the tutor's
  `hi` field, and the built-in characters greet with "Namaskaram" and "Assalaam alaikum".
- **Grading (`lexicon.py`, `textnorm.py`, `content_match.py`):** a `te` lexicon (th/dh folded, long vowel signs folded, joiners dropped) and a `ur`
  lexicon (romanised: the Hindi rules plus "hau", "nakko"; Urdu script: Arabic-keyboard letters folded into Urdu ones, vowel marks dropped).
  The speaking word check compares Telugu and Urdu script with the phrase's own text.
- **Curricula (`0051_telugu_a1.sql`, `0052_urdu_a1.sql`, generated by `tools/gen_telugu_curriculum.py` and `tools/gen_urdu_curriculum.py`):** A1 in
  each language, 9 lessons, 3 grammar notes, 27 exercises, 8 situations and 18 listening activities. The other generators still regenerate
  their migrations byte for byte.
- **Prices (`app.js`):** `HYDERABAD_PRICES`: the metro is a fixed fare and the auto an agreed fare.

## 46. City packs: Bhopal, in Hindi

Bhopal is learnt in Hindi or English, built like Jaipur and Lucknow (section 43).

- **Catalogue (`0053_bhopal.sql`, data only):** Bhopal joins the cities, learnt in Hindi, then English.
- **Destination:** "Available" at the product owner's request, with its other name (The City of Lakes), an introduction and a preview.
- **Content (`content.js`):** `PACKS.bhopal`, 7 roleplays (`bpl_*`, on the server's scene allowlist), `LOCAL_CONTENT.bhopal.hi` (helper `bpP`,
  merged with the shared Hindi glossary) and its review record.
- **Prices (`app.js`):** `BHOPAL_PRICES`: the metro is a fixed fare (₹20–40), the auto an agreed fare and the shared "magic" van a per-seat fare.
- **Server content:** the existing Hindi curriculum.

## 47. City packs: Jammu & Kashmir, in Kashmiri, Dogri and Urdu (In Development)

The destination "Srinagar & Jammu" links to the city `jk` ("Jammu & Kashmir"), learnt in Kashmiri, Dogri, Urdu or English. It is the first
city with three languages besides English, and the first In Development since Bengaluru: its Kashmiri and Dogri are a lower-confidence draft.

- **Catalogue (`0054_jammu_kashmir.sql`, data only):** Kashmiri (`ks`, کٲشُر, `ks-IN`) and Dogri (`doi`, डोगरी, `doi-IN`) join the languages, and
  `jk` joins the cities, learnt in Kashmiri, Dogri, Urdu, then English. The id is `jk` because a saved state's city must match `[a-z0-9-]`.
- **Content (`content.js`):** `PACKS.jk` (Kashmiri), `LANGUAGE_PACKS.jk.doi` and `.ur`, 7 roleplays each (`jk_*`, `jk_doi_*`, `jk_ur_*`, on the
  server's scene allowlist), `LOCAL_CONTENT.jk.ks`, `.doi`, `.ur` (built by `jkTutor` from per-language tables) and review records that say
  "draft" for Kashmiri and Dogri.
- **Engine and app:** the speech locales are `ks-IN` and `doi-IN` (no browser has them, so those phrases are never read aloud) and the AI
  labels "Kashmiri" and "Dogri". `KS_WORDS` and `DOI_WORDS` keep a reply from being taken for English. Kashmiri is shown right to left by the
  same `unicode-bidi: plaintext` as Urdu, in the Nastaliq font. Voice practice names "Kashmiri script" when a phrase has Kashmiri's own
  letters.
- **Server:** `/api/ai` accepts "Kashmiri" and "Dogri" only for `jk`; the characters greet with "Assalaam alaikum" and "Namaste ji".
- **Grading:** a `ks` lexicon (Urdu's folding plus every vowel sign dropped, Kashmiri's own included) and a `doi` lexicon (Hindi's Devanagari
  folding with Dogri's function words: "ai", "aan", "o", "da/di/de", "ch"). The speaking word check reports "kashmiri" when the text has
  Kashmiri's own letters, "urdu" otherwise.
- **Curricula (`0055_kashmiri_a1.sql`, `0056_dogri_a1.sql`):** A1 in each, 9 lessons, 3 grammar notes, 27 exercises, 8 situations and 18
  listening activities. The other generators still regenerate their migrations byte for byte.
- **Prices (`app.js`):** `JK_PRICES`: the Dal Lake shikara at the official hourly rate, autos as an agreed fare, Jammu's matadors per seat.
