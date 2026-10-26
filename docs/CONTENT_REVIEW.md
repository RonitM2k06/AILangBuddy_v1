# Content review: Mumbai (Hindi and Marathi), Bengaluru (Kannada), Chennai (Tamil) and Puducherry (Tamil and French)

Bengaluru, Chennai and Puducherry have their own sections at the end of this file; everything until then is about Mumbai.

**Status: AI-assisted editorial review done; native-speaker review pending.** Nobody fluent in Mumbai Hindi or Marathi has checked this
content. It was written by the LingoBuddy team and has had the editorial pass described below, done with the help of AI tools. That pass
catches mechanical and obvious problems; it is **not** a substitute for a fluent local speaker, and several AI passes do not add up to one.

The status is recorded in the same fields in three places, and the app shows it wherever the content appears:

| Where | Fields |
|---|---|
| First Week packs (`frontend/content.js` `CONTENT_REVIEW`) | `editorial_status: "ai_assisted_review"`, `native_review_status: "pending"`, `last_editorial_reviewed_at: "2026-10-18"`, `known_limitations` |
| Server content (`content_reviews` table, migration 0034; `GET /api/content-review`) | the same four fields, for Marathi |
| This file | this section |

Only a real review by a fluent speaker may set `native_review_status` to `approved` (the database accepts nothing else that claims more).
Delhi's content predates this process and has no recorded review (see the seed notes in `backend/db/migrations/0009_seed_curriculum.sql`).

## Availability decision (2026-10-18)

Mumbai was changed from **In Development** to **Available** on 2026-10-18 at the product owner's request, after the technical work was
complete (docs/ARCHITECTURE.md sections 30–35). This is a product decision, **not** a review result: the native-speaker review is still
pending, the review fields above are unchanged, and the app keeps saying so. Mumbai's destination card shows "Native-speaker review pending",
and the packs, lessons, situations, listening and voice pages keep their review notes. When a fluent speaker has reviewed the content, record
it below and set `native_review_status` to `approved`; the notes then disappear by themselves.

## What is covered

| Content | Where | Size |
|---|---|---|
| Mumbai Hindi First Week pack | `content.js` `PACKS.mumbai` | 7 days, 35 phrases |
| Mumbai Hindi roleplays | `content.js` `SCENARIOS.mum_*` | 7 scenes |
| Mumbai Marathi First Week pack | `content.js` `LANGUAGE_PACKS.mumbai.mr` | 7 days, 35 phrases |
| Mumbai Marathi roleplays (prototype) | `content.js` `SCENARIOS.mum_mr_*` | 7 scenes |
| Mumbai tutor answers and glossary (Hindi, Marathi) | `content.js` `LOCAL_CONTENT.mumbai.*.tutor` | 12 ready-made answers each, Marathi glossary |
| Mumbai readings, level check, achievement names | `content.js` `LOCAL_CONTENT.mumbai.*` | 2 readings and 5 questions per language |
| Marathi curriculum A1 and A2 | migrations 0031 and 0032 (source: `tools/marathi_curriculum_data.py`) | 21 lessons (A1 11, A2 10), 155 items, 9 grammar notes, 63 exercises |
| Marathi server roleplays and listening | migration 0033 | 12 situations (A1 8, A2 4), 42 listening activities (A1 22, A2 20) |
| Marathi B1 | migration 0035 (source: `tools/marathi_curriculum_data.py`) | 6 lessons, 44 items, 5 grammar notes, 18 exercises, 2 situations, 12 listening activities |
| Fair-price ranges | `frontend/app.js` `MUMBAI_PRICES` | 7 items |

## Editorial pass (AI-assisted, not a native review)

**Deterministic checks**, run as tests on every change (`tests/test_mumbai_content_lint.py`, `tests/test_marathi_learning.py`):

- every phrase is in both Devanagari and Roman letters;
- the Marathi has no Hindi words or Hindi punctuation (the danda "।"), in the packs, roleplays, tutor, readings and server content;
- no phrase is taught twice in a pack, and every server item is unique (the database enforces it);
- each romanised Marathi word is spelled one way across all the content (exceptions are listed, with a reason, in the test);
- every gendered learner phrase has its feminine form, in the packs and the server lessons;
- the review status is the same on the client, the server and here;
- the fare ranges contain the sourced fares below.

**Editorial changes** made in the passes so far:

- **Gender.** Characters no longer assume the learner is male ("bhai", "bhaiya", "saheb", "naye aaye ho", "dhoondh rahe ho", "shodhtoys"
  were replaced). Suggested replies are gender-neutral where a natural neutral form exists ("flat barah mein shift kiya hai",
  "do lein toh kitna?", "ho, kalla", "chaarshela dya"). A learner phrase that changes with the speaker's gender shows the feminine form too.
  The A2 lessons use the "kela" construction where it is natural, because it is the same for everyone.
- **Marathi without Hindi fillers.** "Achha" became "bara", "yaar" became "re", and "saheb" was dropped in the Marathi roleplays. The
  built-in roleplay character no longer praises a Marathi learner in Hindi ("Achha!", "Shabaash!"): it says "Chhan!", "Ekdum barobar!", "Shabbas!".
- **Places.** The kurta price is labelled for Colaba Causeway and Dadar, because the Marathi pack shops at Dadar's Ranade Road market.
- **Marathi place names in the tutor.** Places take "-la" ("Dadarla"), and a few change their ending first ("Bandryala", "Kulabyala"). An
  unknown destination gets a plain "-la", which may be wrong for names ending in a vowel.

**What the checks cannot catch** (and the pass did not claim to): whether a phrase is what a Mumbaikar would actually say, whether a
register sounds rude or stiff, whether a roleplay reply is plausible, and whether a grammar note is the best way to explain the point.

## Facts checked against sources (2026-10-18)

| Claim in the app | Source | Result |
|---|---|---|
| Auto, ~5 km by meter: ₹70–110 | The MMRTA revision in force from 1 September 2026, as reported independently by Outlook Business, ETV Bharat, Time Out Mumbai, Deccan Chronicle and NewsBytes: ₹27 for the first 1.5 km, then ₹18.22/km. The order itself is not published online; the Transport Department's online tariff card (transport.maharashtra.gov.in) is still the February 2025 one. | ≈ ₹91: inside the range |
| Kaali-peeli taxi, ~5 km: ₹90–150 | The same reports: ₹33 for the first 1.5 km, then ₹21.90/km | ≈ ₹110: inside the range |
| Local train, second class: ₹5–20 | Western Railway and travel guides: ₹5 for the shortest journeys, about ₹15 for longer ones | inside the range |
| Night surcharge after midnight | 25% between midnight and 5 am (Time Out Mumbai on the September 2026 revision; fare calculators citing the Transport Department) | correct; the app says "a night surcharge after midnight" |
| Bus to Pune from Dadar (A2 roleplay) | MSRTC Shivneri (AC) buses run from Dadar to Pune many times a day (MSRTC timetables) | correct; the app gives no fare, only "check when you book" |
| India's emergency number is 112 | National emergency number | correct |

Meters were given until the end of November 2026 to be recalibrated; until then a driver may show an RTO fare card to convert the meter
reading. The fares change: re-check them against the official tariff card when it is published, and before any later release.

## What the native reviewer should check

1. **Naturalness.** Is each phrase what a Mumbaikar would actually say, at that place, to that person? Flag anything textbook-like.
2. **Register.** Hindi: "aap" with strangers and elders, "tum" with colleagues, "tu" with friends. Marathi: "tumhi" with elders and
   strangers, "tu" with friends and colleagues.
3. **Gender.** The learner's own gendered forms (masculine taught first, feminine shown under it), and the characters' lines.
4. **Mixing.** Mumbai Hindi deliberately borrows Marathi and English ("Kasa kay?", "local", "meter"); Mumbai Marathi borrows English
   ("local", "meter", "weekend", "plumber"). Check the mix is realistic and not accidental.
5. **Romanisation.** No diacritics, nasal sounds dropped (कसं → "kasa", येतं → "yeta"), English loanwords joined to Marathi endings
   ("Churchgatela", "Societyt"). The answer checker accepts the documented variants (docs/ARCHITECTURE.md section 34). Decide whether this is
   readable for beginners.
6. **Devanagari.** Spelling and punctuation (the Marathi uses ".", not "।").
7. **Translations.** The literal and natural English of every phrase.
8. **Roleplays.** The prototype's 14 roleplays and the 12 server situations: opening lines, replies, options and accepted answers.
9. **Lessons and exercises.** All 27 Marathi lessons (A1, A2, B1), the 14 grammar notes (especially the past tense, the future, "aavadta",
   "jar … tar" and "shak-") and the accepted answers of every exercise.
10. **Listening.** The 54 activities' phrases and options, and the 14 server situations.

## After a review

Record the reviewer (name or role), the date and the scope in this file. Make their corrections in the content files and
`tools/marathi_curriculum_data.py`, and ship them to existing installations in a new migration (existing migrations are never edited).
Then set `native_review_status` for the reviewed languages only, in `CONTENT_REVIEW` and in `content_reviews`.

## Bengaluru (Kannada)

**Status: AI-assisted editorial review done; native-speaker review pending.** Nobody fluent in Kannada has checked this content. It was
written by the LingoBuddy team and had the editorial pass described below, done with the help of AI tools. The status is recorded in the same
fields as Mumbai's, in `frontend/content.js` `CONTENT_REVIEW.bengaluru.kn` and in the `content_reviews` row for Kannada (migration 0037).

### What is covered

| Content | Where | Size |
|---|---|---|
| Bengaluru Kannada First Week pack | `content.js` `PACKS.bengaluru` (the English view shows the same pack) | 7 days, 36 phrases (and 1 feminine form) |
| Bengaluru roleplays (prototype) | `content.js` `SCENARIOS.blr_*` | 7 scenes |
| Tutor answers, glossary, readings, level check, "Right now" card, price phrases | `content.js` `LOCAL_CONTENT.bengaluru.kn` | 12 ready-made answers, 17 glossary words, 2 readings, 5 questions |
| Kannada curriculum A1 | migration 0037 (source: `tools/kannada_curriculum_data.py`, `tools/gen_kannada_curriculum.py`) | 9 lessons, 66 items, 3 grammar notes, 27 exercises |
| Kannada server roleplays and listening, A1 | migration 0037 | 8 situations, 18 listening activities |
| Kannada A2 and B1 | migration 0038 (same sources) | 16 lessons (A2 10, B1 6), 112 items, 9 grammar notes, 48 exercises, 6 situations, 32 listening activities |
| Fair-price ranges | `frontend/app.js` `BENGALURU_PRICES` | 6 items |

The curriculum runs from A1 to B1, like Mumbai's Marathi. Hindi is not offered for Bengaluru (no Bengaluru Hindi content was written); English is offered as a view of the Kannada pack.

### Editorial pass (AI-assisted, not a native review)

Deterministic checks, run as tests on every change (`tests/test_bengaluru_content.py`, `tests/test_kannada_learning.py`):

- every phrase is in Kannada script and Roman letters, and nothing in the Bengaluru content is in Devanagari;
- no Hindi words in the pack, roleplays, tutor, readings or server content;
- every suggested roleplay reply is answered by a rule, and every "say it like a local" hint is answered by its own rule;
- characters never address the learner with a gendered word, and the one gendered learner phrase ("hosaba") shows its feminine form ("hosabalu");
  Kannada's first-person verbs are not gendered, so no other phrase needed one;
- a few romanised words that are easy to spell two ways are spelled one way throughout;
- the review status is the same on the client, the server and here;
- the fare ranges contain the sourced fares below.

What the checks cannot catch: whether a phrase is what a Bengalurean would say, the register (the content uses the polite "neevu" forms with
strangers and the casual "maga" only between friends), whether a roleplay reply is plausible, and the grammar notes' explanations.

### Facts checked against sources (2026-10-18)

| Claim in the app | Source | Result |
|---|---|---|
| Auto: ₹36 for the first 2 km, then ₹18 a km; ~5 km by meter ₹80–120 | The Bengaluru Urban fare revision in force from 1 August 2025 (notification of 14 July 2025), reported by The South First, Deccan Herald, Oneindia and others | ≈ ₹90: inside the range |
| Night fares up to one and a half times the meter, 10 pm to 5 am | The same revision | correct |
| Namma Metro ₹10–90 | BMRCL fare table from 9 February 2025, reported by Deccan Herald | correct. An annual revision of up to 5% is allowed from February 2026; whether it was applied was not confirmed, so the range allows ₹95 and the app says so |
| Women who live in Karnataka travel free on BMTC's ordinary buses | The Shakti scheme | correct; the tip names the residence condition |
| India's emergency number is 112 | National emergency number | correct |

Re-check the metro table before a later release.

### Availability decision (2026-10-18): Available

Bengaluru was changed from **In Development** to **Available** on 2026-10-18 at the product owner's request, once its content matched Mumbai's
(a First Week pack, roleplays, and a server curriculum from A1 to B1). As with Mumbai, this is a product decision and **not** a review result.

- **Still pending:** the native-speaker review. The review fields are unchanged, and Bengaluru's card shows "Native-speaker review pending".
  The pack, lessons, situations, listening and voice pages keep their review notes.
- **Not verified:** Kannada speech recognition in the browser and a Kannada voice depend on the learner's device and have not been tried on a
  real one. When either is missing, the app says so and offers the typed check and transcripts.
- **Not available:** pronunciation scoring for Kannada (no provider).

When a fluent speaker has reviewed the content, record it here and set `native_review_status` to `approved` for Kannada only; the notes then
disappear by themselves.

## Chennai (Tamil)

**Status: AI-assisted editorial review done; native-speaker review pending.** Nobody fluent in Tamil has checked this content. It was written by
the LingoBuddy team and had the editorial pass described below, done with the help of AI tools. The status is recorded in
`frontend/content.js` `CONTENT_REVIEW.chennai.ta` and in the `content_reviews` row for Tamil (migration 0040).

The content teaches **spoken Chennai Tamil** with polite "-nga" forms ("kudunga", "irukeenga"), not written Tamil. Tamil's first-person and
"neenga" verbs are not gendered, so no phrase needed a feminine form.

### What is covered

| Content | Where | Size |
|---|---|---|
| Chennai Tamil First Week pack | `content.js` `PACKS.chennai` (the English view shows the same pack) | 7 days, 36 phrases |
| Chennai roleplays (prototype) | `content.js` `SCENARIOS.chn_*` | 7 scenes |
| Tutor answers, glossary, readings, level check, "Right now" card, price phrases | `content.js` `LOCAL_CONTENT.chennai.ta` | 12 ready-made answers, 17 glossary words, 2 readings, 5 questions |
| Tamil curriculum A1 | migration 0040 (source: `tools/tamil_curriculum_data.py`, `tools/gen_tamil_curriculum.py`) | 9 lessons, 65 items, 3 grammar notes, 27 exercises, 8 situations, 18 listening activities |
| Tamil A2 and B1 | migration 0041 (same sources) | 16 lessons (A2 10, B1 6), 112 items, 9 grammar notes, 48 exercises, 6 situations, 32 listening activities |
| More Tamil practice | migration 0042 (same sources) | 2 A1 lessons (Time and Days, About Me), 14 items, 6 exercises, 4 situations, 4 listening activities |
| Fair-price ranges | `frontend/app.js` `CHENNAI_PRICES` | 6 items |

Hindi is not offered for Chennai (no Chennai Hindi content was written); English is offered as a view of the Tamil pack.

### Editorial pass (AI-assisted, not a native review)

Deterministic checks (`tests/test_chennai_content.py`, `tests/test_tamil_learning.py`):

- **Script:** every phrase is in Tamil script and Roman letters, and nothing in the Chennai content is in Devanagari or Kannada script.
- **No Hindi:** no Hindi words anywhere in the Chennai content.
- **Roleplays:** every suggested reply is answered by a rule, and every hint by its own rule.
- **Gender:** characters never address the learner with a gendered word.
- **Spelling:** easily confused romanised words are spelled one way throughout.
- **Records agree:** the review status and the fare ranges match their sources.

What the checks cannot catch:

- whether a phrase is what a Chennai local would say;
- whether the mix of spoken and English words is natural;
- the register;
- the grammar notes' explanations.

### Facts checked against sources (2026-10-18)

| Claim in the app | Source | Result |
|---|---|---|
| Official auto meter fare ₹25 for the first 1.8 km, then ₹12 a km, unchanged since 2013; a revision is pending | Reports of the Tamil Nadu Transport Department's consultation on a revision (Telangana Today, DT Next, The Hans India; checked 2026-10-18) | correct. Drivers quote their own fares, so the app's auto item (₹80–150 for ~5 km) is labelled an agreed fare, not a meter fare. The range is an estimate, not a sourced figure |
| Chennai Metro tokens ₹10–50 | CMRL's fare table (₹10 up to 2 km … ₹50 above 12 km), reported by fare guides; Phase II keeps the same structure | correct |
| Women travel free on MTC's ordinary buses | The Tamil Nadu scheme for free travel on ordinary town buses | correct |
| India's emergency number is 112 | National emergency number | correct |

Re-check the auto fare when the revision is announced, and update the auto item then.

### Availability decision (2026-10-18): Available

Chennai was made **Available** on 2026-10-18 at the product owner's request, with the same content as Bengaluru: a First Week pack, roleplays,
and a server curriculum from A1 to B1. Since migration 0042, Tamil matches Mumbai's Marathi in lessons (27) and listening activities (54),
and has more server roleplays (18 against 14). This is a product decision and **not** a review result.

- **Still pending:** the native-speaker review. Chennai's card shows "Native-speaker review pending", and every page keeps its review note.
- **Not verified:** Tamil speech recognition and a Tamil voice depend on the learner's device and have not been tried on a real one. When either
  is missing, the app says so and offers the typed check and transcripts.
- **Not available:** pronunciation scoring for Tamil (no provider).

## Puducherry (Tamil and French)

**Status: AI-assisted editorial review done; native-speaker review pending, for both languages.** Nobody fluent in Tamil or French has checked
this content. The status is recorded in `frontend/content.js` `CONTENT_REVIEW.puducherry.ta` and `.fr`, and in the `content_reviews` rows
for Tamil (migration 0040) and French (migration 0044).

Puducherry is learnt in **Tamil** (the language of the town, its markets and its autos), **French** (the language of White Town's heritage homes,
the Lycée français, the Alliance française and the consulate) and English. Hindi is not offered.

### What is covered

| Content | Where | Size |
|---|---|---|
| Tamil First Week pack | `content.js` `PACKS.puducherry` | 7 days, 35 phrases |
| French First Week pack | `content.js` `LANGUAGE_PACKS.puducherry.fr` | 7 days, 35 phrases (and 2 feminine forms), with accents, an unaccented form and a pronunciation guide |
| Roleplays (prototype) | `content.js` `SCENARIOS.pdy_*` (Tamil) and `SCENARIOS.pdy_fr_*` (French) | 7 + 7 scenes |
| Tutor, glossary, readings, level check, "Right now" card, price phrases | `content.js` `LOCAL_CONTENT.puducherry.ta` and `.fr` | 12 ready-made answers each, 2 readings and 5 questions each |
| Tamil for Puducherry (server) | migration 0045 (source: `tools/tamil_curriculum_data.py`) | 1 A2 lesson (A Weekend in Puducherry), 7 items, 3 exercises, 3 situations, 2 listening activities; Tamil's other 27 lessons are shared with Chennai |
| French curriculum A1 (server) | migration 0044 (source: `tools/french_curriculum_data.py`, `tools/gen_french_curriculum.py`) | 9 lessons, 66 items, 3 grammar notes, 27 exercises, 8 situations, 18 listening activities |
| Fair-price ranges | `frontend/app.js` `PUDUCHERRY_PRICES` | 6 items |

### Editorial pass (AI-assisted, not a native review)

Deterministic checks (`tests/test_puducherry_content.py`, `tests/test_french_learning.py`, `tests/test_tamil_learning.py`):

- **Tamil:** every phrase is in Tamil script and Roman letters, with no Hindi and no Chennai place names in Puducherry's pack.
- **French:** every phrase has its accents.
  - **Unaccented form:** it equals the phrase with the accents removed.
  - **Pronunciation guide:** each phrase has one for English speakers.
  - **Gender:** the two gendered phrases ("nouveau", "végétarien") show their feminine forms.
  - **Roleplays:** they never make the learner use a masculine form.
  - **Register:** strangers are addressed with "vous", classmates and friends with "tu".
- **Roleplays:** every suggestion is answered, every hint by its own rule, with or without accents.
- **Records agree:** the review records and the price ranges match their sources.

What the checks cannot catch: whether the phrases are what Puducherry's Tamil and French speakers would say; local Franco-Pondicherrian
expressions (not covered yet); and whether the pronunciation guides are helpful.

### Facts checked against sources (2026-10-18)

| Claim in the app | Source | Result |
|---|---|---|
| Scooter rental about ₹300–700 a day | Published rates of several Puducherry rental shops (bikerentalpondicherry.com, travelonrent.com, universaladventures.in, gowheelo.com) | correct |
| Autos don't use meters; agree the fare first | Common local practice; no official meter tariff found | the auto item (₹100–200 for ~3 km) is labelled an agreed fare and is an estimate |
| Bicycle rental, handloom bag, fish curry meal, filter coffee | — | estimates, not sourced figures |
| Real places: White Town, the Promenade (Beach Road), Rue Suffren, Rue Romain Rolland, Rue Dumas, Mission Street, Goubert Market, Auroville and the Matrimandir, the French Consulate, the Lycée français, the Alliance française, the French Institute of Pondicherry, Pondicherry University | General knowledge | correct to the team's knowledge; a local should confirm the details (e.g. where each one is) |
| India's emergency number is 112 | National emergency number | correct |

### Availability decision (2026-10-18): Available

Puducherry was made **Available** on 2026-10-18 at the product owner's request. Its Tamil content is as deep as Chennai's (28 lessons), and its
French is at A1. This is a product decision and **not** a review result.

- **Still pending:** the native-speaker review, for both languages. The card shows "Native-speaker review pending".
- **Not verified:** voices and speech recognition on real devices.
- **Not available:** pronunciation scoring.
- **Scope of the French:** A1 only.

## Jaipur and Lucknow (Hindi)

**Status: AI-assisted editorial review done; native-speaker review pending, for both cities.** Nobody from Jaipur or Lucknow has checked this
content. The status is recorded in `frontend/content.js` `CONTENT_REVIEW.jaipur.hi` and `CONTENT_REVIEW.lucknow.hi`.

Both cities are learnt in **Hindi** and English. Jaipur's Hindi has Rajasthani touches ("Khamma ghani", "padharo", "ghani"). Lucknow's has its
Urdu-flavoured courtesy ("Aadaab", "shukriya", "pehle aap", "tashreef laaiye"). The touches are taught as everyday Hindi words: this is not a course
in Rajasthani or Urdu, and Urdu script is not covered.

### What is covered

| Content | Where | Size |
|---|---|---|
| Jaipur First Week pack | `content.js` `PACKS.jaipur` | 7 days, 35 phrases (and 1 feminine form) |
| Lucknow First Week pack | `content.js` `PACKS.lucknow` | 7 days, 35 phrases (and 2 feminine forms) |
| Roleplays (prototype) | `content.js` `SCENARIOS.jpr_*` and `SCENARIOS.lko_*` | 7 + 7 scenes |
| Tutor, readings, level check, "Right now" card, price phrases | `content.js` `LOCAL_CONTENT.jaipur.hi` and `.lucknow.hi` | 12 ready-made answers each, 2 readings and 5 questions each |
| Hindi on the server | the existing Hindi curriculum (shared with Delhi and Mumbai) | unchanged: no new server lessons for these cities yet |
| Fair-price ranges | `frontend/app.js` `JAIPUR_PRICES`, `LUCKNOW_PRICES` | 6 items each |

### Editorial pass (AI-assisted, not a native review)

Deterministic checks (`tests/test_jaipur_lucknow_content.py`, `tests/test_jaipur_lucknow_browser.py`, `tests/test_legacy_frontend.py`):

- **Hindi:** every phrase is in Devanagari and Roman letters; no other city's place names appear in either pack.
- **Each city's own:** each pack names its own places and uses its own local words, and the two packs share at most two phrases.
- **Gender:** the gendered phrases show their feminine forms. Characters never assume the learner is male, and no suggestion makes the
  learner use a masculine form.
- **Roleplays:** every suggestion is answered, every hint by its own rule.
- **Records agree:** the review records and the price ranges match their sources.

What the checks cannot catch: whether the phrases are what people in Jaipur and Lucknow would say, and whether the Rajasthani and Urdu touches
are used naturally.

### Facts checked against sources (2026-10-19)

| Claim in the app | Source | Result |
|---|---|---|
| Jaipur Metro (Pink Line, Mansarovar ↔ Badi Chaupar) ₹10–30 | Jaipur Metro Rail Corporation fare revision in force from 31 January 2025 | correct as of that revision |
| Lucknow Metro (Red Line, CCS Airport ↔ Munshi Pulia, via Charbagh and Hazratganj) ₹10–60 | UP Metro Rail Corporation fare table | correct |
| Lucknow shared autos and tempos charge per seat on fixed routes | The Lucknow transport department's revised per-km rates for shared autos and tempos | the ₹10–30 seat range for ~3 km is an estimate from those rates |
| Autos in both cities rarely use the meter; agree the fare first | Common local practice | the auto items (₹80–150 for ~5 km) are labelled agreed fares and are estimates |
| Mojaris, block-print kurtas, chikankari, kachori, lassi, kebabs, chai | — | estimates, not sourced figures |
| Real places: Hawa Mahal, Amer Fort, Nahargarh Fort, Jal Mahal, Johari and Bapu Bazaars, Badi and Choti Chaupar, Sindhi Camp, Malviya Nagar; Hazratganj, Aminabad, Chowk, Charbagh, Gomti Nagar, the Bara Imambara, the Rumi Darwaza, the Ghanta Ghar, Lucknow University and its Tagore Library | General knowledge | correct to the team's knowledge; a local should confirm the details |
| India's emergency number is 112 | National emergency number | correct |

### Availability decision (2026-10-19): Available

Jaipur and Lucknow were made **Available** on 2026-10-19 at the product owner's request. This is a product decision and **not** a review result.

- **Still pending:** the native-speaker review, for both cities. The cards show "Native-speaker review pending".
- **Not verified:** voices and speech recognition on real devices. Voices are chosen exactly as for Delhi.
- **Not available:** pronunciation scoring.
- **Server lessons:** both cities use the existing Hindi curriculum. City-specific server lessons, roleplays and listening, and deeper Hindi
  (A2 and B1), are a follow-up.

## Kolkata (Bengali)

**Status: AI-assisted editorial review done; native-speaker review pending.** Nobody fluent in Bengali has checked this content. The status
is recorded in `frontend/content.js` `CONTENT_REVIEW.kolkata.bn` and in the `content_reviews` row for Bengali (migration 0048).

Kolkata is learnt in **Bengali** (spoken Kolkata Bengali, the language of its markets, taxis, tea stalls and adda) and English. Hindi is not
offered. Bengali verbs do not change for the speaker's gender, so no phrase needs a feminine form.

### What is covered

| Content | Where | Size |
|---|---|---|
| Bengali First Week pack | `content.js` `PACKS.kolkata` | 7 days, 35 phrases, in Bengali script with a romanised line |
| Roleplays (prototype) | `content.js` `SCENARIOS.kol_*` | 7 scenes |
| Tutor, glossary, readings, level check, "Right now" card, price phrases | `content.js` `LOCAL_CONTENT.kolkata.bn` | 12 ready-made answers, 2 readings, 5 questions |
| Bengali curriculum A1 (server) | migration 0048 (source: `tools/bengali_curriculum_data.py`, `tools/gen_bengali_curriculum.py`) | 9 lessons, 64 items, 3 grammar notes, 27 exercises, 8 situations, 18 listening activities |
| Bengali curriculum A2 and B1 (server) | migration 0049 (same sources) | 10 A2 and 6 B1 lessons, 112 items, 9 grammar notes, 48 exercises, 6 situations, 32 listening activities |
| Fair-price ranges | `frontend/app.js` `KOLKATA_PRICES` | 6 items |

### Editorial pass (AI-assisted, not a native review)

Deterministic checks (`tests/test_kolkata_content.py`, `tests/test_bengali_learning.py`, `tests/test_kolkata_browser.py`):

- **Bengali:** every phrase is in Bengali script and Roman letters, with no Devanagari letter, no Hindi words and no other city's places.
- **Kolkata's own:** the pack names Kolkata's places and uses its own words (adda, bhaar, taant, phuchka).
- **Roleplays:** every suggestion is answered, every hint by its own rule. The taxi scene checks the longer rule first where one keyword
  contains another ("kotokkhon", how long, contains "koto", how much).
- **Grading:** answers are accepted in Roman letters or Bengali script, with common romanisation variants folded ("achhe" / "ache",
  "shoja" / "soja"). "Na" (not) is never ignored, so "debo na" (won't give) does not match "debo" (will give).
- **Records agree:** the review records and the price ranges match their sources.

What the checks cannot catch: whether the phrases are what Kolkata speakers would say, and whether the romanisation reads naturally to them.

### Facts checked against sources (2026-10-19)

| Claim in the app | Source | Result |
|---|---|---|
| Metro Blue Line fares ₹5–25 (0–2 km ₹5 … over 20 km ₹25) | Metro Railway Kolkata fare slabs, as published on kolkatametro.org | correct |
| The Green Line runs under the Hooghly from Howrah Maidan through Esplanade and Sealdah to Salt Lake Sector V | The Esplanade–Sealdah section opened on 22 August 2025 (Wikipedia, Green Line (Kolkata Metro)) | correct |
| The Blue Line runs from Dakshineswar to Kavi Subhash via Esplanade, Park Street and Maidan | Wikipedia, Blue Line (Kolkata Metro) | correct |
| Yellow taxis go by the meter; ~5 km ≈ ₹100–160 | Published tariffs disagree (fare-card sites give different base and per-km rates) | the meter rule is correct; the range is labelled an estimate |
| Taant saree, kurta, egg roll, tea in a clay cup | — | estimates, not sourced figures |
| Real places: Howrah Station, Bolpur (for Shantiniketan), Dakshineswar, the EM Bypass, Salt Lake Sector V, Park Street, Esplanade, Maidan, the Victoria Memorial, Gariahat Market, New Market, College Street and the Indian Coffee House, Salt Lake, Sealdah, Jadavpur University (and Milan da's canteen), Prinsep Ghat, Shantipur taant | General knowledge | correct to the team's knowledge; a local should confirm the details |
| Trains to Bolpur (Shantiniketan) leave from Howrah | Eastern Railway services such as the Shantiniketan Express | correct to the team's knowledge |
| India's emergency number is 112 | National emergency number | correct |

### Availability decision (2026-10-19): Available

Kolkata was made **Available** on 2026-10-19 at the product owner's request. This is a product decision and **not** a review result.

- **Still pending:** the native-speaker review. The card shows "Native-speaker review pending".
- **Not verified:** voices and speech recognition on real devices.
- **Not available:** pronunciation scoring.
- **Scope of the Bengali:** A1 to B1 on the server (25 lessons), as for Kannada and Tamil.

## Hyderabad (Telugu and Urdu)

**Status: AI-assisted editorial review done; native-speaker review pending, for both languages.** Nobody fluent in Telugu or Urdu has checked
this content. The status is recorded in `frontend/content.js` `CONTENT_REVIEW.hyderabad.te` and `.ur`, and in the `content_reviews` rows for
Telugu (migration 0051) and Urdu (migration 0052).

Hyderabad is learnt in **Telugu** (the language of the new city's offices, autos and markets), **Urdu** (Hyderabadi Urdu, the language of the
old city around the Charminar, with its Dakhini words "hau", "nakko" and "kya re") and English. Telugu verbs for "I" and "you" do not change
for gender; Urdu's do, so the Urdu pack shows feminine forms.

### What is covered

| Content | Where | Size |
|---|---|---|
| Telugu First Week pack | `content.js` `PACKS.hyderabad` | 7 days, 35 phrases, in Telugu script with a romanised line |
| Urdu First Week pack | `content.js` `LANGUAGE_PACKS.hyderabad.ur` | 7 days, 35 phrases (and 1 feminine form), in Urdu script (right to left) with a romanised line |
| Roleplays (prototype) | `content.js` `SCENARIOS.hyd_*` (Telugu) and `SCENARIOS.hyd_ur_*` (Urdu) | 7 + 7 scenes |
| Tutor, glossary, readings, level check, "Right now" card, price phrases | `content.js` `LOCAL_CONTENT.hyderabad.te` and `.ur` | 12 ready-made answers each, 2 readings and 5 questions each |
| Telugu curriculum A1 (server) | migration 0051 (source: `tools/telugu_curriculum_data.py`, `tools/gen_telugu_curriculum.py`) | 9 lessons, 64 items, 3 grammar notes, 27 exercises, 8 situations, 18 listening activities |
| Urdu curriculum A1 (server) | migration 0052 (source: `tools/urdu_curriculum_data.py`, `tools/gen_urdu_curriculum.py`) | 9 lessons, 65 items, 3 grammar notes, 27 exercises, 8 situations, 18 listening activities |
| Fair-price ranges | `frontend/app.js` `HYDERABAD_PRICES` | 6 items |

### Editorial pass (AI-assisted, not a native review)

Deterministic checks (`tests/test_hyderabad_content.py`, `tests/test_telugu_urdu_learning.py`, `tests/test_hyderabad_browser.py`):

- **Telugu:** every phrase is in Telugu script and Roman letters, with no Hindi and no other city's places.
- **Urdu:** every phrase is in Urdu script, ends with Urdu's own full stop (۔) rather than the Hindi danda, and has a romanised line. The
  Hyderabadi words are there ("hau", "kya re", "idhar").
- **Right to left:** Urdu phrases are drawn right to left (checked in a real browser: the first letter is to the right of the last), and the
  romanised line stays left to right.
- **Gender:** the gendered Urdu phrase shows its feminine form; no Urdu character assumes the learner is male, and no suggestion or hint makes
  the learner use a masculine form.
- **Roleplays:** every suggestion is answered, every hint by its own rule. Two keyword clashes were caught: "entha sepu" (how long) contains
  "entha" (how much), and "kidhar" (where) contains "idhar" (here).
- **Grading:** typed answers are accepted in Roman letters or each language's own script; Urdu typed on an Arabic keyboard (ي, ك, ه) folds into
  its Urdu letters.
- **Records agree:** the review records and the price ranges match their sources.

What the checks cannot catch: whether the phrases are what Hyderabadis would say, whether the Dakhini words are used naturally, and how the
Urdu Nastaliq font looks on every device.

### Facts checked against sources (2026-10-19)

| Claim in the app | Source | Result |
|---|---|---|
| Hyderabad Metro fares ₹11–69 | The revised fare chart in force from 24 May 2025 (₹12–75, less a 10% discount), as reported by indiarailinfo.com and newsmeter.in | correct as of that revision |
| Metro lines: Red (Miyapur–LB Nagar), Blue (Nagole–Raidurg), Green (JBS Parade Ground–MGBS) | Hyderabad Metro Rail network | correct to the team's knowledge |
| Autos should use the meter, but many drivers quote a fare | Common local practice | the auto item (₹80–150 for ~5 km) is labelled an agreed fare and is an estimate |
| Lac bangles, pearls, biryani, Irani chai | — | estimates, not sourced figures |
| Real places: Secunderabad, Nampally, Banjara Hills, Jubilee Hills, HITEC City, Madhapur, Gachibowli, Ameerpet, Tolichowki, Mehdipatnam, Koti, Abids, the Charminar, Laad Bazaar, Pathargatti, Chowmahalla Palace, the Mecca Masjid, Tank Bund and Hussain Sagar, Golconda Fort (and its light show), the Maulana Azad National Urdu University | General knowledge | correct to the team's knowledge; a local should confirm the details |
| India's emergency number is 112 | National emergency number | correct |

### Availability decision (2026-10-19): Available

Hyderabad was made **Available** on 2026-10-19 at the product owner's request, in Telugu, Urdu and English (the product owner chose Urdu in
Urdu script). This is a product decision and **not** a review result.

- **Still pending:** the native-speaker review, for both languages. The card shows "Native-speaker review pending".
- **Not verified:** voices and speech recognition on real devices; Urdu voices are rare on Indian devices, and without one Urdu is not read
  aloud.
- **Not available:** pronunciation scoring.
- **Scope:** A1 on the server for both languages.

## Bhopal (Hindi)

**Status: AI-assisted editorial review done; native-speaker review pending.** Nobody from Bhopal has checked this content. The status is
recorded in `frontend/content.js` `CONTENT_REVIEW.bhopal.hi`.

Bhopal is learnt in **Hindi** and English, with Bhopali touches: "khan" and "miyan" as a friendly address, the old city's "patiya" chats,
poha-jalebi, sulemani chai and zari batuas. They are touches in Hindi, not a course in Bhopali.

### What is covered

| Content | Where | Size |
|---|---|---|
| First Week pack | `content.js` `PACKS.bhopal` | 7 days, 35 phrases (and 1 feminine form) |
| Roleplays (prototype) | `content.js` `SCENARIOS.bpl_*` | 7 scenes |
| Tutor, readings, level check, "Right now" card, price phrases | `content.js` `LOCAL_CONTENT.bhopal.hi` | 12 ready-made answers, 2 readings, 5 questions |
| Hindi on the server | the existing Hindi curriculum (shared with Delhi, Mumbai, Jaipur and Lucknow) | unchanged |
| Fair-price ranges | `frontend/app.js` `BHOPAL_PRICES` | 6 items |

### Editorial pass (AI-assisted, not a native review)

Deterministic checks (`tests/test_bhopal_content.py`, `tests/test_jaipur_lucknow_browser.py`, `tests/test_legacy_frontend.py`): every phrase is
in Devanagari and Roman letters; the pack names Bhopal's places and uses its own words; the gendered phrase shows its feminine form; no
character assumes the learner is male and no suggestion or hint makes the learner use a masculine form (two openings and one suggestion were
rewritten for this); every suggestion is answered and every hint by its own rule.

What the checks cannot catch: whether the phrases are what Bhopalis would say, and whether the Bhopali touches are used naturally.

### Facts checked against sources (2026-10-19)

| Claim in the app | Source | Result |
|---|---|---|
| Bhopal Metro's Orange Line runs Subhash Nagar – AIIMS (8 stations, via MP Nagar and Rani Kamlapati), open since December 2025 | Wikipedia, Orange Line (Bhoj Metro) | correct |
| Metro fares ₹20–40 (1–2 stations ₹20, 3–5 ₹30, 6–8 ₹40) | Reported fare slabs (palpalnewshub.com, trackmymetro.com) | correct as reported; to be confirmed against MPMRCL's own table |
| Autos rarely use the meter; shared "magic" vans run fixed routes | Common local practice | the auto (₹70–130 for ~5 km) and van-seat ranges are estimates |
| Batua, poha-jalebi, chai | — | estimates, not sourced figures |
| Real places: Rani Kamlapati station (formerly Habibganj), Bhopal Junction, New Market, MP Nagar, Arera Colony, DB Mall, Van Vihar, the Upper Lake (Bada Talab) and its Boat Club, Peer Gate, Chowk Bazaar, the Taj-ul-Masajid, Sanchi, Bhimbetka, Bhojpur, MANIT, Barkatullah University | General knowledge | correct to the team's knowledge; a local should confirm the details |
| India's emergency number is 112 | National emergency number | correct |

### Availability decision (2026-10-19): Available

Bhopal was made **Available** on 2026-10-19 at the product owner's request. This is a product decision and **not** a review result.

- **Still pending:** the native-speaker review. The card shows "Native-speaker review pending".
- **Not verified:** voices and speech recognition on real devices. Voices are chosen exactly as for Delhi.
- **Not available:** pronunciation scoring.
- **Server lessons:** Bhopal uses the existing Hindi curriculum; city lessons and Hindi A2/B1 are a follow-up shared with Jaipur and Lucknow.

## Jammu & Kashmir (Kashmiri, Dogri and Urdu)

**Status: a DRAFT for Kashmiri and Dogri; AI-assisted editorial review done for Urdu; native-speaker review pending for all three.** Nobody
fluent in any of the three has checked this content. The Kashmiri and Dogri were written with **lower confidence** than every other language in
the app: the phrases are simple and plausible, but some may not be what people say, and the Kashmiri Perso-Arabic spelling in particular is
likely to contain errors. The status is recorded in `frontend/content.js` `CONTENT_REVIEW.jk.ks`, `.doi` and `.ur`, and in the
`content_reviews` rows for Kashmiri (migration 0055) and Dogri (migration 0056).

The destination "Srinagar & Jammu" is learnt in **Kashmiri** (the Valley's language, set in Srinagar), **Dogri** (Jammu's language, set in Jammu)
and **Urdu** (J&K's official language, set in both), and English. The city's id is `jk`. All three change verbs with the speaker's gender, so
each pack shows a feminine form.

### What is covered

| Content | Where | Size |
|---|---|---|
| Kashmiri First Week pack (draft) | `content.js` `PACKS.jk` | 7 days, 35 phrases (and 1 feminine form), Perso-Arabic script, right to left |
| Dogri First Week pack (draft) | `content.js` `LANGUAGE_PACKS.jk.doi` | 7 days, 35 phrases (and 1 feminine form), Devanagari |
| Urdu First Week pack | `content.js` `LANGUAGE_PACKS.jk.ur` | 7 days, 35 phrases (and 1 feminine form), Urdu script, right to left |
| Roleplays (prototype) | `content.js` `SCENARIOS.jk_*`, `jk_doi_*`, `jk_ur_*` | 7 + 7 + 7 scenes |
| Tutor, readings, level check, "Right now" card, price phrases | `content.js` `LOCAL_CONTENT.jk.ks`, `.doi`, `.ur` | 12 ready-made answers each, 2 readings and 5 questions each |
| Kashmiri curriculum A1 (server, draft) | migration 0055 (source: `tools/kashmiri_curriculum_data.py`, `tools/gen_kashmiri_curriculum.py`) | 9 lessons, 65 items, 3 grammar notes, 27 exercises, 8 situations, 18 listening activities |
| Dogri curriculum A1 (server, draft) | migration 0056 (source: `tools/dogri_curriculum_data.py`, `tools/gen_dogri_curriculum.py`) | 9 lessons, 65 items, 3 grammar notes, 27 exercises, 8 situations, 18 listening activities |
| Urdu on the server | the existing Urdu curriculum (0052, set in Hyderabad) | unchanged; J&K settings on the server are a follow-up |
| Fair-price ranges | `frontend/app.js` `JK_PRICES` | 6 items |

### Editorial pass (AI-assisted, not a native review)

Deterministic checks (`tests/test_jammu_kashmir_content.py`, `tests/test_kashmiri_dogri_learning.py`, `tests/test_jammu_kashmir_browser.py`):

- **Scripts:** Kashmiri phrases use Kashmiri's own letters and vowel signs (not just Urdu spelling); Urdu phrases use none of them; Dogri is
  Devanagari only. Kashmiri and Urdu are drawn right to left.
- **Places:** the Kashmiri pack is set in Srinagar, the Dogri pack in Jammu, the Urdu pack in both; no Hyderabadi Urdu in J&K.
- **Gender:** each gendered phrase shows its feminine form; no suggestion or hint makes the learner use a masculine form (three were rewritten
  for this).
- **Roleplays:** every suggestion is answered, every hint by its own rule (one clash fixed: "yeti", here, was also in "I'm new here").
- **Voices:** browsers have no Kashmiri or Dogri voice, so those phrases are never read aloud, and an Urdu or Hindi voice is never used instead.
- **Records agree:** the review records say "draft" for Kashmiri and Dogri, and the price ranges match their sources.

What the checks cannot catch: **whether the Kashmiri and Dogri are right.** This needs a native speaker of each before learners rely on them.

### Facts checked against sources (2026-10-19)

| Claim in the app | Source | Result |
|---|---|---|
| The official Dal Lake shikara rate is about ₹770 for the first hour per boat; boatmen at Dal Gate often ask more | J&K tourism department rates as reported by Greater Kashmir and Rising Kashmir | correct as reported |
| Autos in Srinagar and Jammu don't use meters | Common local practice | the auto range (₹100–200 for ~5 km) is an estimate |
| Jammu's matadors run fixed routes for a few rupees a seat | The fare charts found are old; overcharging is reported | the seat range (₹10–20) is an estimate |
| Pashmina, kahwa, kalari kulcha | — | estimates, not sourced figures |
| Real places: the Dal Lake, Dal Gate, the Boulevard, Lal Chowk and its clock tower, Polo View, Residency Road, Rajbagh, the Nishat and Shalimar Baghs, the Hazratbal, the University of Kashmir, Gulmarg; Jammu Tawi station, Gandhi Nagar, Raghunath Bazaar and Temple, the Bahu Fort and Bagh-e-Bahu, the University of Jammu, Katra and Vaishno Devi | General knowledge | correct to the team's knowledge; a local should confirm the details |
| India's emergency number is 112 | National emergency number | correct |

### Status decision (2026-10-19): In Development

The destination is **In Development**, not Available, because the Kashmiri and Dogri are a lower-confidence draft. The card says "In
Development" and "Early version", and the introduction and the language cards say "draft".

- **Still pending:** the native-speaker review of all three languages; for Kashmiri and Dogri, every phrase.
- **Not verified:** speech recognition on real devices. There are no Kashmiri or Dogri voices.
- **Not available:** pronunciation scoring.
- **To make it Available:** after a native review, change `status` to `"available"` in `content.js` `DESTINATIONS` and record the review here.
