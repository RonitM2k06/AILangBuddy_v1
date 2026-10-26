-- Review metadata for a language's server content (lessons, situations, listening), the server-side twin of frontend/content.js
-- CONTENT_REVIEW. Additive: a new table and one row; nothing else changes.
--   editorial_status      who has checked the language: 'none', 'ai_assisted_review' (an AI-assisted editorial pass by the team) or
--                         'human_editorial_review' (a human editor, not necessarily a native speaker)
--   native_review_status  'pending', 'in_progress' or 'approved'. Only a real review by a fluent speaker may set 'approved'.
--   known_limitations     plain text, shown to learners with the status.
-- A language without a row has no recorded review (Hindi's content predates this table).
CREATE TABLE content_reviews (
    language_id                INTEGER PRIMARY KEY REFERENCES languages(id) ON DELETE RESTRICT,
    editorial_status           TEXT NOT NULL CHECK (editorial_status IN ('none', 'ai_assisted_review', 'human_editorial_review')),
    native_review_status       TEXT NOT NULL CHECK (native_review_status IN ('pending', 'in_progress', 'approved')),
    last_editorial_reviewed_at TEXT CHECK (last_editorial_reviewed_at IS NULL OR last_editorial_reviewed_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    known_limitations          TEXT NOT NULL DEFAULT '' CHECK (length(known_limitations) <= 2000)
);

INSERT INTO content_reviews(language_id, editorial_status, native_review_status, last_editorial_reviewed_at, known_limitations)
SELECT id, 'ai_assisted_review', 'pending', '2026-10-18',
       'Written by the LingoBuddy team with an AI-assisted editorial pass; not yet checked by a native Marathi speaker. Phrases teach the masculine '
       || 'form first and show the feminine form where they differ. Fares and practical tips change over time.'
FROM languages WHERE code = 'mr';
