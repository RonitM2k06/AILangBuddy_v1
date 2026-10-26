-- Jammu & Kashmir joins the cities, learnt in Kashmiri, Dogri, Urdu and English: Kashmiri and Dogri join the catalogue (frontend/content.js
-- LANGUAGES; Urdu was added in 0050), and the city (CITIES.jk, DESTINATIONS "srinagar-jammu", In Development) has its packs:
-- PACKS.jk (Kashmiri) and LANGUAGE_PACKS.jk.doi / .ur, their roleplays in SCENARIOS and on the server's scene allowlist in
-- backend/legacy/ai.py. Data only: no schema change. tests/test_schema.py keeps the catalogue and the frontend in step.
INSERT INTO languages(code, name, native_name, tts_locale) VALUES ('ks', 'Kashmiri', 'کٲشُر', 'ks-IN');
INSERT INTO languages(code, name, native_name, tts_locale) VALUES ('doi', 'Dogri', 'डोगरी', 'doi-IN');
INSERT INTO cities(slug, name, flag, emoji, tagline, blurb, is_ready) VALUES ('jk', 'Jammu & Kashmir', '🇮🇳', '🛶', 'Kashmiri · Dogri · Urdu', 'Houseboats, kahwa & the temples of Jammu', 1);
INSERT INTO city_languages(city_id, language_id, sort_order)
SELECT c.id, l.id, v.sort_order FROM (SELECT 'ks' AS lang, 1 AS sort_order UNION ALL SELECT 'doi', 2 UNION ALL SELECT 'ur', 3 UNION ALL SELECT 'en', 4) v
JOIN cities c ON c.slug = 'jk' JOIN languages l ON l.code = v.lang;
