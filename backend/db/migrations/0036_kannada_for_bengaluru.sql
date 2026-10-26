-- Kannada for Bengaluru: the language joins the catalogue (frontend/content.js LANGUAGES), Bengaluru's learning languages become Kannada,
-- English (CITIES.bengaluru.langs; frontend/content.js PACKS.bengaluru is the Kannada First Week pack, its roleplays are in SCENARIOS and on
-- the server's scene allowlist in backend/legacy/ai.py) and its pack is ready. Data only: no schema change. tests/test_schema.py keeps the
-- catalogue and the frontend in step.
INSERT INTO languages(code, name, native_name, tts_locale) VALUES ('kn', 'Kannada', 'ಕನ್ನಡ', 'kn-IN');
UPDATE city_languages SET sort_order = 2
 WHERE city_id = (SELECT id FROM cities WHERE slug = 'bengaluru') AND language_id = (SELECT id FROM languages WHERE code = 'en');
INSERT INTO city_languages(city_id, language_id, sort_order)
SELECT c.id, l.id, 1 FROM cities c, languages l WHERE c.slug = 'bengaluru' AND l.code = 'kn';
UPDATE cities SET is_ready = 1 WHERE slug = 'bengaluru';
