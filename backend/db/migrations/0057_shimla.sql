-- Shimla joins the cities (frontend/content.js CITIES and DESTINATIONS.shimla), learnt in Hindi and English, with its First Week pack ready:
-- PACKS.shimla, its roleplays in SCENARIOS and on the server's scene allowlist in backend/legacy/ai.py. Hindi was already in the catalogue
-- (0002). Data only: no schema change. tests/test_schema.py keeps the catalogue and the frontend in step.
INSERT INTO cities(slug, name, flag, emoji, tagline, blurb, is_ready) VALUES ('shimla', 'Shimla', '🇮🇳', '🏔️', 'Hindi', 'The Mall, the Ridge & the toy train', 1);
INSERT INTO city_languages(city_id, language_id, sort_order)
SELECT c.id, l.id, v.sort_order FROM (SELECT 'hi' AS lang, 1 AS sort_order UNION ALL SELECT 'en', 2) v
JOIN cities c ON c.slug = 'shimla' JOIN languages l ON l.code = v.lang;
