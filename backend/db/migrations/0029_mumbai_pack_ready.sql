-- City packs: Mumbai's First Week pack is ready (frontend/content.js PACKS.mumbai, its roleplays in SCENARIOS and on the server's scene
-- allowlist in backend/legacy/ai.py). Data only: the catalogue's flag follows the frontend's (tests/test_schema.py keeps the two in step).
UPDATE cities SET is_ready = 1 WHERE slug = 'mumbai';
