# LingoBuddy — Feature Roadmap

**Nothing here is implemented yet.** Each phase is built only on explicit request, and must end with: app runs, DB consistent, existing features (the hackathon "I'm New Here" / Confidence flows) still work, tests pass.

Standing rules: migrations for every schema change; no language- or age-specific data hardcoded in logic; business logic separate from UI; DB access separate from presentation; secrets in env only; validate input; authorize server-side; no fake security features; no needless dependencies.

Columns: **Objective · Components · DB entities · Depends on · Testing**.

## Phase 1: Foundation + database architecture
- **Objective:** migrated relational base; existing behaviour unchanged.
- **Components:** migration runner, repository layer, connection handling, `pytest`, read-only language/city endpoints, `docs/ARCHITECTURE.md` (ER + normalisation).
- **DB:** `schema_migrations`, `users` (demo learner), `languages`, `cefr_levels`, `cities`, `city_languages`.
- **Depends on:** none.
- **Testing:** migration up from empty DB and from the existing `buddy.db`; constraint tests; existing endpoints regress-tested.

## Phase 2: Authentication + RBAC
- **Objective:** real identities; server-side authorization.
- **Components:** register/login (learner, parent, admin), password hashing, session tokens, password reset, role guards, protect `/api/state` and `/api/ai`, rate-limiting.
- **DB:** `roles`, `user_roles`, `sessions`, `login_history`, `password_resets`.
- **Depends on:** 1.
- **Testing:** authz tests per role; session expiry; brute-force limits; demo mode preserved for the pitch.

## Phase 3: Languages + CEFR + age system
- **Objective:** data-driven languages, levels and age bands.
- **Components:** learner profile (DOB → band), target language + CEFR per user, placement wired to CEFR, difficulty inputs (age + performance).
- **DB:** `age_groups`, `learner_profiles`, `user_languages`, `assessments`, `assessment_questions`, `assessment_attempts`.
- **Depends on:** 1, 2.
- **Testing:** adding a new language via SQL only works end to end; age band derivation; placement → level.

## Phase 4: Lessons + vocabulary + grammar
- **Objective:** move lesson/phrase content from `content.js` to the DB.
- **Components:** content API, lesson player, vocabulary/grammar, SM-2 flashcards on DB, mistake notebook.
- **DB:** `topics`, `lessons`, `lesson_sections`, `phrases`, `phrase_translations`, `vocabulary`, `grammar_topics`, `questions`, `answers`, `hints`, `user_lesson_progress`, `flashcards`, `flashcard_reviews`, `mistakes`.
- **Depends on:** 3.
- **Testing:** seed parity with `content.js`; SRS scheduling unit tests; transactional progress + XP writes.

## Phase 5: Situational learning
- **Objective:** make the Delhi pack and roleplays first-class, multi-city/language situations.
- **Components:** situation browser, scripted situation flow, emergency pack, scenario prompts from data.
- **DB:** `situations`, `situation_steps`, `situation_phrases`, `user_situation_progress`.
- **Depends on:** 4.
- **Testing:** existing 7 scenarios reproduce identically from DB; offline fallback intact.

## Phase 6: Confidence + personalisation
- **Objective:** confidence derived from real activity; recommendations.
- **Components:** confidence engine (server-side), weakness detection, daily plan/tasks, goals, recommendations.
- **DB:** `skills`, `confidence_scores` (+ history), `weaknesses`, `recommendations`, `daily_tasks`, `user_daily_tasks`, `learning_goals`.
- **Depends on:** 4, 5.
- **Testing:** score formulas; aggregate/reporting SQL; idempotent daily-task generation.

## Phase 7: Speaking + listening + TTS/STT
- **Objective:** measured speaking/listening with stored results.
- **Components:** session tracking, pronunciation/fluency scoring (extend `Engine.score`), optional server STT/TTS provider abstraction.
- **DB:** `speaking_sessions`, `pronunciation_scores`, `listening_sessions`.
- **Depends on:** 4, 6.
- **Testing:** scoring unit tests; graceful degradation when mic or voice is missing.

## Phase 8: Kids / teen learning experience
- **Objective:** age-appropriate UX and content.
- **Components:** under-10 simplified game UI (lives, rewards), 10–18 XP/streak UI, 18+ CEFR UI; content age-gating; child-safe AI prompts.
- **DB:** `content_age_rules`, `lives`/`rewards` (as needed), extends `age_groups`.
- **Depends on:** 3, 4, 6.
- **Testing:** age gating at API level; safety prompt tests; responsive checks.

## Phase 9: Parent portal
- **Objective:** parents link to and monitor children.
- **Components:** parent↔child linking/consent, progress/time/weakness views, controls (content, time limits).
- **DB:** `parent_child`, `parental_controls`, `activity_log`.
- **Depends on:** 2, 6, 8.
- **Testing:** strict authz (a parent sees only linked children); time-limit enforcement on server.

## Phase 10: Gamification + social
- **Objective:** XP, levels, streaks, achievements, challenges, friends, leaderboards.
- **Components:** real streak and XP engine (replaces seeded values), achievements rules, challenges, leaderboards.
- **DB:** `xp_events`, `streaks`, `achievements`, `user_achievements`, `challenges`, `user_challenges`, `friends`, `notifications`, `stories`, `story_progress`.
- **Depends on:** 2, 4, 6.
- **Testing:** streak day-boundary/timezone tests; leaderboard query performance/indexes; privacy for minors.

## Phase 11: AI tutor + roleplay
- **Objective:** context-aware AI from DB learner context.
- **Components:** context builder (language, CEFR, age band, lesson, weaknesses), personalities, persisted conversations, "Need help?" assistant, per-user rate limits and cost caps.
- **DB:** `conversations`, `conversation_messages`, `ai_personas`.
- **Depends on:** 2, 3, 5, 6.
- **Testing:** prompt construction unit tests; fallback when provider fails; injection tests.

## Phase 12: Advanced AI features
- **Objective:** generated content and richer simulation.
- **Components:** AI lesson/scenario/practice generation with admin review before publish, conversation simulator, camera vocabulary, translation mode.
- **DB:** `generated_content` (+ review status), extends content tables.
- **Depends on:** 4, 5, 11.
- **Testing:** generated content schema validation; human-review workflow.

## Phase 13: Admin CMS + analytics
- **Objective:** manage all content and see system metrics.
- **Components:** admin UI for users/languages/lessons/vocab/situations/questions, publishing, analytics dashboards, system settings.
- **DB:** `content_status/versions`, `audit_log`, `system_settings` and reporting views.
- **Depends on:** 2, 4, 5.
- **Testing:** RBAC on every admin endpoint; audit-trail tests; report query correctness.

## Phase 14: Security + 2FA
- **Objective:** harden.
- **Components:** TOTP 2FA with QR setup, recovery codes, logout-all-devices, session review, security headers, dependency audit.
- **DB:** `two_factor_auth`, `recovery_codes`, extends `sessions`.
- **Depends on:** 2.
- **Testing:** 2FA flows (valid/invalid/replay/recovery); session revocation.
- **Jammu & Kashmir in Kashmiri, Dogri and Urdu, in development (2026-10-19):** Kashmiri and Dogri join the languages and the Srinagar & Jammu destination is learnt in Kashmiri, Dogri, Urdu or English (0054). Three First Week packs with 7 roleplays each, local content in all three, prices, and Kashmiri and Dogri A1 on the server (0055, 0056). In Development because the Kashmiri and Dogri are a lower-confidence draft. Remaining: native review of every Kashmiri and Dogri phrase, Urdu lessons set in J&K on the server (ARCHITECTURE.md section 47).
- **Bhopal in Hindi, available (2026-10-19):** Bhopal is learnt in Hindi or English (0053), with a 7-day Hindi First Week pack in its own Bhopali flavour, 7 roleplays, local tutor, readings, "Right now" card and prices (Bhopal Metro ₹20–40). It uses the existing Hindi server curriculum. Remaining: native review, city server lessons, Hindi A2 and B1 (ARCHITECTURE.md section 46).
- **Hyderabad in Telugu and Urdu, available (2026-10-19):** Telugu and Urdu join the languages and Hyderabad is learnt in Telugu, Urdu or English (0050). It has a Telugu and an Urdu First Week pack (Urdu in Urdu script, shown right to left) with 7 roleplays each, local content in both languages, prices, and A1 on the server in each: 9 lessons, 27 exercises, 8 situations, 18 listening activities (0051, 0052). Remaining: native review of both languages, Telugu and Urdu A2+, voices on real devices (ARCHITECTURE.md section 45).
- **Kolkata in Bengali, available (2026-10-19):** Bengali joins the languages and Kolkata is learnt in Bengali or English (0047). It has a 7-day Bengali First Week pack, 7 roleplays, a Bengali tutor, readings, prices and a "Right now" card, and Bengali from A1 to B1 on the server: 25 lessons, 75 exercises, 14 situations, 50 listening activities (0048, 0049), with grading in Roman letters and Bengali script. Remaining: native review, speech and voices tested on real devices (ARCHITECTURE.md section 44).
- **Jaipur and Lucknow in Hindi, available (2026-10-19):** both cities are learnt in Hindi or English (0046). Each has a 7-day Hindi First Week pack in its own local flavour (Rajasthani touches for Jaipur, Lucknow's Urdu-flavoured courtesy), 7 roleplays, local tutor, readings, "Right now" card and prices. They use the existing Hindi server curriculum. Remaining: native review, city server lessons, Hindi A2 and B1 (ARCHITECTURE.md section 43).
- **Puducherry in Tamil and French, available (2026-10-18):** Puducherry is learnt in Tamil, French or English (0043). It has a Tamil and a French First Week pack with 7 roleplays each, local content in both languages, prices, Tamil practice set in Puducherry (0045) and French A1 on the server: 9 lessons, 27 exercises, 8 situations, 18 listening activities (0044). French grading ignores accents. Remaining: native review of both languages, French A2+, local Franco-Pondicherrian expressions (ARCHITECTURE.md section 42).
- **More Chennai practice (2026-10-18):** two more Tamil A1 lessons (Time and Days, About Me) with listening pairs, and 4 more server roleplays (neighbours, a provision store, an airport cab, flat hunting), in migration 0042. Tamil now has 27 lessons, 18 roleplays and 54 listening activities (ARCHITECTURE.md section 41).
- **Chennai in Tamil, available (2026-10-18):** a 7-day Tamil First Week pack, 7 roleplays, Tamil tutor, readings, prices and "Right now" card; Tamil in the catalogue with Chennai learnt in Tamil or English (0039); Tamil from A1 to B1 on the server: 25 lessons, 75 exercises, 14 situations, 50 listening activities (0040, 0041); Tamil grading and the speaking word check in Tamil script. "Available" at the product owner's request; the native review is pending and the app says so. Remaining: native review, the official auto fare once revised, speech and voices tested on real devices (ARCHITECTURE.md section 40).
- **Bengaluru available, Kannada A2 and B1 (2026-10-18):** 10 A2 and 6 B1 Kannada lessons, 9 grammar notes, 48 exercises, 6 situations and 32 listening activities (0038). Bengaluru is "Available" at the product owner's request; the native review is still pending and the app says so (ARCHITECTURE.md section 39).
- **Bengaluru in Kannada (done):** a 7-day Kannada First Week pack, 7 roleplays, Kannada tutor, readings, prices and "Right now" card; Kannada in the catalogue with Bengaluru learnt in Kannada or English (0036); the Kannada A1 server curriculum: 9 lessons, 27 exercises, 8 situations, 18 listening activities (0037); Kannada grading and the speaking word check in Kannada script. Status stays In Development (docs/CONTENT_REVIEW.md). Remaining: native review, A2+, testing speech recognition and voices on real devices (ARCHITECTURE.md sections 37, 38).
- **Marathi B1 (done):** 6 B1 lessons, 5 grammar notes, 18 exercises, 2 situations, 12 listening activities (0035); fares re-confirmed against several independent sources; pronunciation scoring researched (Azure has no Marathi; WAV/OGG only) and not built (ARCHITECTURE.md section 36). Remaining: native review, a Marathi-capable pronunciation provider, B2+.
- **Mumbai available (2026-10-18):** Mumbai's destination is "Available" at the product owner's request. The native review is still pending and the app says so (its card and every review note); remaining: native review, official fares, a real pronunciation provider, B1+ (ARCHITECTURE.md section 35).
- **Mumbai Marathi learning flows (done, In Development):** Marathi through A2 (21 lessons, 63 exercises, 9 grammar notes), 12 server roleplays and 42 listening activities (0032, 0033), a Marathi grading lexicon and romanisation folding (Hindi unchanged), speaking capabilities up front with a typed check, no invented Marathi scores, no Hindi voice for Marathi (transcript mode), and review metadata (0034, AI-assisted only, native review pending). Remaining: native review, B1+, longer listening (ARCHITECTURE.md section 34).
- **Completing Mumbai (done, In Development):** content review status shown and recorded (awaiting native review), gender-neutral roleplays and feminine forms, per-pack progress (`packDays`, prefixed card ids), Mumbai/Marathi tutor answers, readings, level check and achievements, Marathi AI tutor, and Marathi in the server curriculum (0031: A1/A2, 7 lessons). Remaining: native review, Marathi situations and listening (ARCHITECTURE.md section 33).
- **Mumbai in Marathi (done):** Mumbai can be learnt in Marathi too (Hindi · Marathi · English): a 7-day Mumbai Marathi First Week pack and 7 Marathi roleplays on the server's allowlist, Marathi speech (`mr-IN`), Marathi price advice and "Right now" card, and a Marathi roleplay prompt. Migration 0030 adds Marathi to the catalogue; the tutor stays in Hindi (ARCHITECTURE.md section 32).
- **Destination previews (done):** "I'm New Here" shows all 28 state capitals and 8 union-territory capitals (34 cards). Delhi is available, Mumbai is in development, the other 32 are "Coming Soon" and cannot be picked: a card opens only when its linked pack is ready in `CITIES`. Display data only, no schema change (ARCHITECTURE.md section 31).
- **City pack: Mumbai (done):** a 7-day First Week pack in Mumbai Hindi (Bambaiya and Marathi touches) with 7 Mumbai roleplays, on the server's scene allowlist, a city-aware AI prompt, Mumbai prices (by meter) and a "Right now" card. Migration 0029 marks it ready. Next: Bengaluru, Hyderabad and Chennai need Kannada, Telugu and Tamil language support first (ARCHITECTURE.md section 30).
- **15B (done):** installable PWA foundation. It adds original icons (192, 512, maskable, apple-touch, favicon) in the manifest, and a service worker at `/sw.js` that caches only an exact allowlist of 31 versioned static files and never `/api/*`, page loads, writes, recordings or other origins. There is an honest offline page (Try again, 🆘 phrases, 📞 112), an offline banner, an update offer that waits for the learner, and an install button only where the browser offers it. Chrome reports the app installable on HTTPS or localhost. There is no offline learning and nothing is queued (ARCHITECTURE.md section 29).
- **15A (done):** responsive, mobile-first layout on the existing SPA, and the app shown to signed-in accounts only. A sign-in screen lets visitors sign in or create a learner or parent account, and the 🆘 phrases and a 112 link stay available without an account. The phone bar's More menu reaches every page, the sidebar scrolls by itself (sign-in was unreachable on laptops), content is centred with fluid sizes, scrolling is smoother, and new accounts get their own progress instead of the demo's. It also adds 44px targets, visible focus, 16px fields and a web manifest (no service worker, not installable yet). It is verified in real headless Chrome; 2FA screens were deferred (ARCHITECTURE.md section 28). Next: 15B safe offline (static-only service worker, icons).
- **14F (done):** final adversarial verification of 14A to 14E. It found and fixed six defects with regression tests: concurrent attempts slipping past the challenge, sign-in, password-change and second-factor limits (one was a 500); out-of-range numbers as 500s; and unbounded event writes from free-to-repeat refusals. Its attack matrix covers authentication, sessions, 2FA, admin MFA, CSRF, headers and cookies, the legacy endpoints, IDOR, event forensics and configuration, and tests can no longer reach the network; no migration (ARCHITECTURE.md section 27).
- **14E (done):** append-only security events for sign-in, sessions, password and two-factor (closed fields, no secrets or e-mail, HMAC references), an admin Security page with events, accounts and configuration warnings, the account listing narrowed to references and paginated, and a coarse public health check; migration 0028 (ARCHITECTURE.md section 26).
- **14D (done):** TOTP 2FA (RFC 6238, stdlib), AES-GCM encrypted secrets (`TOTP_ENC_KEY`), a vendored local QR encoder with the manual key as fallback, hashed one-time recovery codes, a password-then-code sign-in challenge, database-backed second-factor throttling, and mandatory admin MFA; migration 0027 (ARCHITECTURE.md section 25).
- **14C (done):** sessions with public ids, an idle timeout and a fixed lifetime, rotation on sign-in, session list and revoke, logout-all, password change (revokes every other session), layered and bounded sign-in, registration and password-change throttles; migration 0026 (ARCHITECTURE.md section 24).
- **14B (done):** global CSRF guard (custom header + JSON content type on every write, Origin/Referer checks, one listed raw-audio route) and security headers (nosniff, DENY, referrer policy, a partial CSP, HSTS over HTTPS, `no-store` on every API response); strict script CSP deferred (ARCHITECTURE.md section 23).
- **14A (done):** legacy attack-surface lockdown: no shared demo state, validated per-user legacy state, escaped legacy rendering, a fenced and rate-limited legacy `/api/ai`, and no age-group change by DOB edit while a parent is linked (ARCHITECTURE.md section 22).

## Phase 15: Mobile / offline + polish
- **Objective:** installable, offline-capable, travel-ready.
- **Components:** PWA and offline cache (builds on the existing offline engine), travel/location packs, multilingual keyboard, mobile preview.
- **DB:** sync metadata as needed.
- **Depends on:** 4, 5.
- **Testing:** offline E2E; sync conflict handling.

## Final: Testing + DBMS documentation + viva prep
- Full test pass; ER diagram, functional dependencies and normalisation proofs (1NF to BCNF), index and query justification, transaction demos (XP/progress atomicity), sample aggregate and reporting queries, viva Q&A.

## Deferred ideas (noted, not scheduled)
Cities beyond Delhi (Mumbai, Bengaluru, Hyderabad, Chennai are placeholders today); richer placement (6 questions now); fair-price data as a table; per-city emergency numbers.
