-- Kolkata joins the cities, learnt in Bengali and English: Bengali joins the catalogue (frontend/content.js LANGUAGES) and Kolkata
-- (CITIES.kolkata, DESTINATIONS.kolkata) is ready, with its Bengali First Week pack, frontend/content.js PACKS.kolkata, its roleplays in
-- SCENARIOS and on the server's scene allowlist in backend/legacy/ai.py. Data only: no schema change. tests/test_schema.py keeps the
-- catalogue and the frontend in step.
INSERT INTO languages(code, name, native_name, tts_locale) VALUES ('bn', 'Bengali', 'বাংলা', 'bn-IN');
INSERT INTO cities(slug, name, flag, emoji, tagline, blurb, is_ready) VALUES ('kolkata', 'Kolkata', '🇮🇳', '🌉', 'Bengali', 'Adda, rolls & the yellow taxi', 1);
INSERT INTO city_languages(city_id, language_id, sort_order)
SELECT c.id, l.id, v.sort_order FROM (SELECT 'bn' AS lang, 1 AS sort_order UNION ALL SELECT 'en', 2) v
JOIN cities c ON c.slug = 'kolkata' JOIN languages l ON l.code = v.lang;
