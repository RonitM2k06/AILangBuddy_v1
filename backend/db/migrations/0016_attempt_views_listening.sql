-- Phase 7A: listening attempts count as performance evidence. The two personalization views gain one UNION branch each;
-- every rule that reads them (weaknesses, performance) picks listening up with no other change. Adaptive difficulty still
-- reads only source = 'lesson', so it is unaffected. Views store nothing, so recreating them is safe.
DROP VIEW learner_attempts;
DROP VIEW learner_attempt_topics;

CREATE VIEW learner_attempts AS
SELECT 'lesson' AS source, ea.id AS attempt_id, ea.user_id, l.language_id, l.id AS unit_id, e.id AS task_id, e.kind,
       e.item_id, e.difficulty, ea.is_correct, ea.attempted_at
FROM exercise_attempts ea JOIN exercises e ON e.id = ea.exercise_id JOIN lessons l ON l.id = e.lesson_id
UNION ALL
SELECT 'situation', sa.id, sa.user_id, s.language_id, s.id, st.id, st.kind, st.item_id, NULL, sa.is_correct, sa.attempted_at
FROM situation_step_attempts sa JOIN situation_steps st ON st.id = sa.step_id JOIN situations s ON s.id = st.situation_id
WHERE st.kind <> 'learn_phrase'
UNION ALL
SELECT 'listening', la.id, la.user_id, a.language_id, a.id, a.id, 'listening', a.item_id, a.difficulty, la.is_correct, la.attempted_at
FROM listening_attempts la JOIN listening_activities a ON a.id = la.activity_id;

CREATE VIEW learner_attempt_topics AS
SELECT 'lesson' AS source, ea.id AS attempt_id, ea.user_id, l.language_id, lt.topic_id, ea.is_correct, ea.attempted_at
FROM exercise_attempts ea JOIN exercises e ON e.id = ea.exercise_id JOIN lessons l ON l.id = e.lesson_id
JOIN lesson_topics lt ON lt.lesson_id = l.id
UNION ALL
SELECT 'situation', sa.id, sa.user_id, s.language_id, s.topic_id, sa.is_correct, sa.attempted_at
FROM situation_step_attempts sa JOIN situation_steps st ON st.id = sa.step_id JOIN situations s ON s.id = st.situation_id
WHERE st.kind <> 'learn_phrase'
UNION ALL
SELECT 'listening', la.id, la.user_id, a.language_id, a.topic_id, la.is_correct, la.attempted_at
FROM listening_attempts la JOIN listening_activities a ON a.id = la.activity_id;
