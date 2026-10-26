-- Tamil for Chennai: the language joins the catalogue (frontend/content.js LANGUAGES), Chennai's learning languages become Tamil, English
-- (CITIES.chennai.langs; frontend/content.js PACKS.chennai is the Tamil First Week pack, its roleplays are in SCENARIOS and on the server's
-- scene allowlist in backend/legacy/ai.py) and its pack is ready. Data only: no schema change. tests/test_schema.py keeps the catalogue and
-- the frontend in step.
INSERT INTO languages(code, name, native_name, tts_locale) VALUES ('ta', 'Tamil', 'தமிழ்', 'ta-IN');
UPDATE city_languages SET sort_order = 2
 WHERE city_id = (SELECT id FROM cities WHERE slug = 'chennai') AND language_id = (SELECT id FROM languages WHERE code = 'en');
INSERT INTO city_languages(city_id, language_id, sort_order)
SELECT c.id, l.id, 1 FROM cities c, languages l WHERE c.slug = 'chennai' AND l.code = 'ta';
UPDATE cities SET is_ready = 1 WHERE slug = 'chennai';
