-- Phase 9: the parent portal. Additive only; no existing table or column changes.
--
-- Design notes
--  * A parent is an ordinary user holding the existing 'parent' role; a child is an ordinary user holding the 'learner' role.
--    Nothing about either is copied: parent_links only relates the two.
--  * A link can only be created by redeeming a one-time code that the LEARNER's own session generated, so no parent can
--    discover or claim an arbitrary learner (there is no search, and no endpoint takes a learner id on creation).
--  * The composite foreign keys into user_roles make the database itself refuse a link whose parent does not hold the parent
--    role or whose child does not hold the learner role. role ids 2 and 1 are the ones seeded by 0004 (a test ties them to
--    the role names).
--  * Parental controls are RESTRICTIONS only: a control row can switch a feature off, never switch on anything the product
--    itself keeps off (child voice stays blocked by age group whatever a control says). No row means no restriction beyond
--    the product defaults.

CREATE TABLE parent_links (
    id              INTEGER PRIMARY KEY,
    parent_id       INTEGER NOT NULL,
    learner_id      INTEGER NOT NULL,
    parent_role_id  INTEGER NOT NULL DEFAULT 2 CHECK (parent_role_id = 2),
    learner_role_id INTEGER NOT NULL DEFAULT 1 CHECK (learner_role_id = 1),
    created_at      TEXT    NOT NULL,
    UNIQUE (parent_id, learner_id),                     -- one relationship per pair, never duplicated
    CHECK (parent_id <> learner_id),
    FOREIGN KEY (parent_id,  parent_role_id)  REFERENCES user_roles(user_id, role_id) ON DELETE CASCADE,
    FOREIGN KEY (learner_id, learner_role_id) REFERENCES user_roles(user_id, role_id) ON DELETE CASCADE
);
CREATE INDEX idx_parent_links_learner ON parent_links(learner_id);      -- "who may see this learner" (the parent side is the UNIQUE)

-- One-time codes. Only a SHA-256 of the code is stored. A code is single use, short lived and tied to the learner who made it.
CREATE TABLE parent_link_codes (
    id              INTEGER PRIMARY KEY,
    learner_id      INTEGER NOT NULL,
    learner_role_id INTEGER NOT NULL DEFAULT 1 CHECK (learner_role_id = 1),
    code_hash       TEXT    NOT NULL UNIQUE,
    created_at      TEXT    NOT NULL,
    expires_at      TEXT    NOT NULL,
    used_at         TEXT,
    used_by         INTEGER REFERENCES users(id) ON DELETE CASCADE,
    CHECK (expires_at > created_at),
    CHECK ((used_at IS NULL) = (used_by IS NULL)),
    FOREIGN KEY (learner_id, learner_role_id) REFERENCES user_roles(user_id, role_id) ON DELETE CASCADE
);
CREATE INDEX idx_parent_link_codes_learner ON parent_link_codes(learner_id);

-- Per-relationship restrictions. voice_disabled = 1 stops the child's speaking features. If several parents are linked,
-- the strictest wins (any parent's restriction applies).
CREATE TABLE parent_controls (
    link_id        INTEGER PRIMARY KEY REFERENCES parent_links(id) ON DELETE CASCADE,
    voice_disabled INTEGER NOT NULL DEFAULT 0 CHECK (voice_disabled IN (0, 1)),
    updated_at     TEXT    NOT NULL
);
