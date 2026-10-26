"""Two-factor persistence (Phase 14D). Takes an open connection. Every query is scoped by the user it acts for; the secret is only ever
ciphertext here, recovery codes and challenge tokens only ever hashes. Single-use rules are enforced by conditional UPDATEs whose row
count decides: two concurrent requests cannot both spend the same time step, recovery code or challenge."""


# ---------- credentials ----------
def get_credential(conn, user_id):
    return conn.execute("SELECT user_id, secret_ciphertext, secret_nonce, status, setup_expires_at, last_used_step FROM two_factor_credentials WHERE user_id = ?",
                        (user_id,)).fetchone()


def put_pending(conn, user_id, ciphertext, nonce, now, expires_at):
    """Replace this user's pending setup (never an enabled credential: the caller checks, and the schema refuses)."""
    conn.execute("DELETE FROM two_factor_credentials WHERE user_id = ? AND status = 'pending'", (user_id,))
    conn.execute("INSERT INTO two_factor_credentials(user_id, secret_ciphertext, secret_nonce, status, created_at, setup_expires_at) VALUES (?, ?, ?, 'pending', ?, ?)",
                 (user_id, ciphertext, nonce, now, expires_at))


def enable(conn, user_id, step, now):
    """pending -> enabled, using `step` as the first spent time step. Returns 1 if this request did it."""
    return conn.execute("""UPDATE two_factor_credentials SET status = 'enabled', enabled_at = ?, setup_expires_at = NULL, last_used_step = ?
                           WHERE user_id = ? AND status = 'pending' AND setup_expires_at > ?""", (now, step, user_id, now)).rowcount


def spend_step(conn, user_id, step):
    """Record `step` as used if it is later than the last one used. Returns 1 if this request spent it (the replay guard)."""
    return conn.execute("""UPDATE two_factor_credentials SET last_used_step = ?
                           WHERE user_id = ? AND status = 'enabled' AND (last_used_step IS NULL OR last_used_step < ?)""", (step, user_id, step)).rowcount


def remove(conn, user_id):
    conn.execute("DELETE FROM two_factor_credentials WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM recovery_codes WHERE user_id = ?", (user_id,))


def is_enabled(conn, user_id):
    return conn.execute("SELECT 1 FROM two_factor_credentials WHERE user_id = ? AND status = 'enabled'", (user_id,)).fetchone() is not None


# ---------- recovery codes ----------
def replace_recovery_codes(conn, user_id, hashes, now):
    conn.execute("DELETE FROM recovery_codes WHERE user_id = ?", (user_id,))
    conn.executemany("INSERT INTO recovery_codes(user_id, code_hash, created_at) VALUES (?, ?, ?)", [(user_id, h, now) for h in hashes])


def spend_recovery_code(conn, user_id, code_hash, now):
    """Spend one of THIS user's unused codes. Returns 1 if this request spent it."""
    return conn.execute("UPDATE recovery_codes SET used_at = ? WHERE user_id = ? AND code_hash = ? AND used_at IS NULL", (now, user_id, code_hash)).rowcount


def unused_recovery_codes(conn, user_id):
    return conn.execute("SELECT COUNT(*) FROM recovery_codes WHERE user_id = ? AND used_at IS NULL", (user_id,)).fetchone()[0]


# ---------- login challenges ----------
def create_challenge(conn, user_id, token_hash, now, expires_at):
    conn.execute("DELETE FROM login_challenges WHERE user_id = ? AND (expires_at <= ? OR completed_at IS NOT NULL)", (user_id, now))
    conn.execute("INSERT INTO login_challenges(user_id, token_hash, created_at, expires_at) VALUES (?, ?, ?, ?)", (user_id, token_hash, now, expires_at))


def live_challenge(conn, token_hash, now, max_attempts):
    """The challenge behind this token if it is unexpired, not completed and has attempts left, else None."""
    return conn.execute("""SELECT id, user_id, attempts FROM login_challenges
                           WHERE token_hash = ? AND expires_at > ? AND completed_at IS NULL AND attempts < ?""", (token_hash, now, max_attempts)).fetchone()


def take_attempt(conn, challenge_id, now, max_attempts):
    """Use one of the challenge's attempts, before the code is checked. Returns 1 if this request got one (the challenge is still live and
    has attempts left); one statement, so concurrent requests can never use more than `max_attempts` between them."""
    return conn.execute("""UPDATE login_challenges SET attempts = attempts + 1
                           WHERE id = ? AND completed_at IS NULL AND expires_at > ? AND attempts < ?""", (challenge_id, now, max_attempts)).rowcount


def complete_challenge(conn, challenge_id, now):
    """Mark the challenge used. Returns 1 if this request completed it (it can be completed once)."""
    return conn.execute("UPDATE login_challenges SET completed_at = ? WHERE id = ? AND completed_at IS NULL", (now, challenge_id)).rowcount


# ---------- failure accounting ----------
def reserve_failure(conn, user_id, kind, now, since, limit):
    """Count one second-factor attempt as a failure up front, unless this user already has `limit` failures after `since`. Returns the new
    row's id, or None at the limit. Check and insert are one statement (a write, so it holds SQLite's write lock while it counts): concurrent
    requests cannot all slip under the limit. An attempt that turns out not to be a failure is given back with release_failure."""
    conn.execute("DELETE FROM mfa_failures WHERE user_id = ? AND occurred_at <= ?", (user_id, since))
    cur = conn.execute("""INSERT INTO mfa_failures(user_id, kind, occurred_at) SELECT ?, ?, ?
                          WHERE (SELECT COUNT(*) FROM mfa_failures WHERE user_id = ? AND occurred_at > ?) < ?""", (user_id, kind, now, user_id, since, limit))
    return cur.lastrowid if cur.rowcount == 1 else None


def release_failure(conn, user_id, failure_id):
    conn.execute("DELETE FROM mfa_failures WHERE id = ? AND user_id = ?", (failure_id, user_id))


def failures_since(conn, user_id, since):
    """Times of this user's failures after `since`, oldest first. Older rows are deleted (bounded growth)."""
    conn.execute("DELETE FROM mfa_failures WHERE user_id = ? AND occurred_at <= ?", (user_id, since))
    return [r[0] for r in conn.execute("SELECT occurred_at FROM mfa_failures WHERE user_id = ? AND occurred_at > ? ORDER BY occurred_at, id", (user_id, since))]
