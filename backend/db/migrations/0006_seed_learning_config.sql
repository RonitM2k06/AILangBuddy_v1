-- Seed from the prototype: every shipped piece of content is A1 (content.js READINGS) and the
-- placement test (app.js) only ever assigns A1 or A2, for the three languages the Delhi pack offers.
INSERT INTO language_levels(language_id, cefr_code)
SELECT l.id, c.code FROM languages l, cefr_levels c
WHERE l.code IN ('hi', 'hinglish', 'en') AND c.code IN ('A1', 'A2');

-- 18 starts adulthood, so the teen band is 10-17.
INSERT INTO age_groups(code, label, min_age, max_age) VALUES
  ('child', 'Under 10', 0,  9),
  ('teen',  '10–17',    10, 17),
  ('adult', '18+',      18, NULL);
