-- Puducherry joins the cities (frontend/content.js CITIES and DESTINATIONS.puducherry), learnt in Tamil, French and English, with its First
-- Week packs ready: PACKS.puducherry (Tamil) and LANGUAGE_PACKS.puducherry.fr (French), their roleplays in SCENARIOS and on the server's scene
-- allowlist in backend/legacy/ai.py. French was already in the catalogue (0002). Data only: no schema change. tests/test_schema.py keeps the
-- catalogue and the frontend in step.
INSERT INTO cities(slug, name, flag, emoji, tagline, blurb, is_ready) VALUES ('puducherry', 'Puducherry', '🇮🇳', '🌅', 'Tamil · French', 'French quarter, beaches & cafés', 1);
INSERT INTO city_languages(city_id, language_id, sort_order)
SELECT c.id, l.id, v.sort_order FROM (SELECT 'ta' AS lang, 1 AS sort_order UNION ALL SELECT 'fr', 2 UNION ALL SELECT 'en', 3) v
JOIN cities c ON c.slug = 'puducherry' JOIN languages l ON l.code = v.lang;
