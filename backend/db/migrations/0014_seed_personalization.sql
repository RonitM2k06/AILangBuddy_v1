-- Phase 6 seed.
-- Skills: the ones the platform can already serve (vocabulary and grammar exercises, conversation steps). Speaking,
-- listening and pronunciation are added as data when those features exist.
INSERT INTO skills(code, name) VALUES ('vocabulary', 'Vocabulary'), ('grammar', 'Grammar'), ('conversation', 'Conversation');

-- Exercise difficulty is editorial metadata by answer format: recognising the answer (multiple choice) is easier than
-- completing a phrase (fill-in-the-blank), which is easier than producing one from scratch (translation).
-- No exercise text, option or answer is changed.
UPDATE exercises SET difficulty = 1 WHERE kind = 'multiple_choice';
UPDATE exercises SET difficulty = 2 WHERE kind = 'fill_blank';
UPDATE exercises SET difficulty = 3 WHERE kind = 'translation';
