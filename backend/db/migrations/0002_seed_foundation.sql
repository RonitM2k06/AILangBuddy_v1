-- Seed data transcribed from the prototype: frontend/content.js (LANGUAGES, CITIES),
-- engine.js DEMO() (demo learner) and app.js (the A1-C2 level chips, A1/A2 labels).

INSERT INTO users(handle, display_name) VALUES ('demo-alex', 'Alex');

INSERT INTO languages(code, name, native_name, tts_locale) VALUES
  ('en',       'English',    'English',    'en-IN'),
  ('es',       'Spanish',    'Español',    'es-ES'),
  ('fr',       'French',     'Français',   'fr-FR'),
  ('de',       'German',     'Deutsch',    'de-DE'),
  ('it',       'Italian',    'Italiano',   'it-IT'),
  ('pt',       'Portuguese', 'Português',  'pt-PT'),
  ('ja',       'Japanese',   '日本語',       'ja-JP'),
  ('ko',       'Korean',     '한국어',        'ko-KR'),
  ('zh',       'Chinese',    '中文',         'zh-CN'),
  ('hi',       'Hindi',      'हिन्दी',       'hi-IN'),
  ('hinglish', 'Hinglish',   'Hinglish',   'hi-IN');

INSERT INTO cefr_levels(code, rank, label) VALUES
  ('A1', 1, 'Beginner'),
  ('A2', 2, 'Elementary'),
  ('B1', 3, 'Intermediate'),
  ('B2', 4, 'Upper Intermediate'),
  ('C1', 5, 'Advanced'),
  ('C2', 6, 'Proficient');

INSERT INTO cities(slug, name, flag, emoji, tagline, blurb, is_ready) VALUES
  ('delhi',     'Delhi',     '🇮🇳', '🕌', 'Dilli',            'Metro, autos, chaat & Sarojini', 1),
  ('mumbai',    'Mumbai',    '🇮🇳', '🌊', 'Marathi · Hindi',  'Locals, vada pav & the sea',     0),
  ('bengaluru', 'Bengaluru', '🇮🇳', '☕', 'Kannada',          'Filter coffee & tech parks',     0),
  ('hyderabad', 'Hyderabad', '🇮🇳', '🍚', 'Telugu · Urdu',    'Biryani & Charminar',            0),
  ('chennai',   'Chennai',   '🇮🇳', '🏖️', 'Tamil',            'Marina, idli & auto talk',       0);

INSERT INTO city_languages(city_id, language_id, sort_order)
SELECT c.id, l.id, v.sort_order FROM (
  SELECT 'delhi' AS city, 'hi' AS lang, 1 AS sort_order UNION ALL
  SELECT 'delhi', 'hinglish', 2 UNION ALL
  SELECT 'delhi', 'en', 3 UNION ALL
  SELECT 'mumbai', 'hi', 1 UNION ALL
  SELECT 'mumbai', 'en', 2 UNION ALL
  SELECT 'bengaluru', 'en', 1 UNION ALL
  SELECT 'hyderabad', 'en', 1 UNION ALL
  SELECT 'chennai', 'en', 1
) v JOIN cities c ON c.slug = v.city JOIN languages l ON l.code = v.lang;
