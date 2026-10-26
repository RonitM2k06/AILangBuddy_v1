-- Hyderabad becomes ready, learnt in Telugu, Urdu and English: Telugu and Urdu join the catalogue (frontend/content.js LANGUAGES), Hyderabad's
-- learning languages become Telugu, Urdu, English (CITIES.hyderabad.langs; frontend/content.js PACKS.hyderabad is the Telugu First Week pack and
-- LANGUAGE_PACKS.hyderabad.ur the Urdu one, their roleplays in SCENARIOS and on the server's scene allowlist in backend/legacy/ai.py). Data
-- only: no schema change. tests/test_schema.py keeps the catalogue and the frontend in step.
INSERT INTO languages(code, name, native_name, tts_locale) VALUES ('te', 'Telugu', 'తెలుగు', 'te-IN');
INSERT INTO languages(code, name, native_name, tts_locale) VALUES ('ur', 'Urdu', 'اردو', 'ur-IN');
UPDATE city_languages SET sort_order = 3
 WHERE city_id = (SELECT id FROM cities WHERE slug = 'hyderabad') AND language_id = (SELECT id FROM languages WHERE code = 'en');
INSERT INTO city_languages(city_id, language_id, sort_order)
SELECT c.id, l.id, v.sort_order FROM (SELECT 'te' AS lang, 1 AS sort_order UNION ALL SELECT 'ur', 2) v
JOIN cities c ON c.slug = 'hyderabad' JOIN languages l ON l.code = v.lang;
UPDATE cities SET is_ready = 1 WHERE slug = 'hyderabad';
