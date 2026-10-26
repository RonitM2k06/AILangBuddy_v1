INSERT INTO roles(name) VALUES ('learner'), ('parent'), ('admin');

-- The prototype's demo learner keeps working as a learner; it has no credentials so it cannot log in.
INSERT INTO user_roles(user_id, role_id)
SELECT u.id, r.id FROM users u, roles r WHERE u.handle = 'demo-alex' AND r.name = 'learner';
