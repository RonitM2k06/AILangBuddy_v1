-- Marathi for Mumbai: the language joins the catalogue (frontend/content.js LANGUAGES) and Mumbai's learning languages become Hindi,
-- Marathi, English (CITIES.mumbai.langs; frontend/content.js LANGUAGE_PACKS.mumbai.mr is the Marathi First Week pack). Data only: no schema
-- change, and no CEFR levels, so it is not (yet) a target for the server curriculum. tests/test_schema.py keeps both lists in step.
INSERT INTO languages(code, name, native_name, tts_locale) VALUES ('mr', 'Marathi', 'मराठी', 'mr-IN');
UPDATE city_languages SET sort_order = 3
 WHERE city_id = (SELECT id FROM cities WHERE slug = 'mumbai') AND language_id = (SELECT id FROM languages WHERE code = 'en');
INSERT INTO city_languages(city_id, language_id, sort_order)
SELECT c.id, l.id, 2 FROM cities c, languages l WHERE c.slug = 'mumbai' AND l.code = 'mr';
