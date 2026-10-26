-- Jaipur and Lucknow join the cities (frontend/content.js CITIES and DESTINATIONS.jaipur, DESTINATIONS.lucknow), both learnt in Hindi and
-- English, with their First Week packs ready: PACKS.jaipur and PACKS.lucknow, their roleplays in SCENARIOS and on the server's scene
-- allowlist in backend/legacy/ai.py. Hindi was already in the catalogue (0002). Data only: no schema change. tests/test_schema.py keeps the
-- catalogue and the frontend in step.
INSERT INTO cities(slug, name, flag, emoji, tagline, blurb, is_ready) VALUES ('jaipur', 'Jaipur', '🇮🇳', '🏰', 'Hindi', 'Forts, bazaars & dal baati', 1);
INSERT INTO cities(slug, name, flag, emoji, tagline, blurb, is_ready) VALUES ('lucknow', 'Lucknow', '🇮🇳', '🕌', 'Hindi', 'Kebabs, chikankari & tehzeeb', 1);
INSERT INTO city_languages(city_id, language_id, sort_order)
SELECT c.id, l.id, v.sort_order FROM (SELECT 'jaipur' AS city, 'hi' AS lang, 1 AS sort_order UNION ALL SELECT 'jaipur', 'en', 2
                                      UNION ALL SELECT 'lucknow', 'hi', 1 UNION ALL SELECT 'lucknow', 'en', 2) v
JOIN cities c ON c.slug = v.city JOIN languages l ON l.code = v.lang;
