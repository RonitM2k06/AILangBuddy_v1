-- Bhopal joins the cities (frontend/content.js CITIES and DESTINATIONS.bhopal), learnt in Hindi and English, with its First Week pack ready:
-- PACKS.bhopal, its roleplays in SCENARIOS and on the server's scene allowlist in backend/legacy/ai.py. Hindi was already in the catalogue
-- (0002). Data only: no schema change. tests/test_schema.py keeps the catalogue and the frontend in step.
INSERT INTO cities(slug, name, flag, emoji, tagline, blurb, is_ready) VALUES ('bhopal', 'Bhopal', '🇮🇳', '🏞️', 'Hindi', 'Lakes, poha & the old city', 1);
INSERT INTO city_languages(city_id, language_id, sort_order)
SELECT c.id, l.id, v.sort_order FROM (SELECT 'hi' AS lang, 1 AS sort_order UNION ALL SELECT 'en', 2) v
JOIN cities c ON c.slug = 'bhopal' JOIN languages l ON l.code = v.lang;
