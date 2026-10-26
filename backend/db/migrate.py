"""Minimal ordered SQL migration runner.

Migrations are files named NNNN_description.sql in backend/db/migrations, applied in
filename order. Each one runs in a single transaction together with its
schema_migrations row, so a failed migration leaves no trace. Applied migrations are
skipped, which makes running this on every startup safe. A checksum guards against
editing a migration after it has been applied.
"""
import hashlib
import sqlite3
from pathlib import Path

from . import connect

MIGRATIONS_DIR = Path(__file__).parent / "migrations"

BOOTSTRAP = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version    TEXT PRIMARY KEY,
    name       TEXT NOT NULL,
    checksum   TEXT NOT NULL,
    applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
)
"""


class MigrationError(RuntimeError):
    pass


def discover(directory=MIGRATIONS_DIR):
    """Return [(version, name, sql, checksum)] sorted by version."""
    found = []
    for path in sorted(Path(directory).glob("*.sql")):
        version, _, name = path.stem.partition("_")
        if not version.isdigit():
            raise MigrationError(f"Bad migration filename: {path.name}")
        sql = path.read_text(encoding="utf-8")
        found.append((version, name, sql, hashlib.sha256(sql.encode("utf-8")).hexdigest()))
    versions = [f[0] for f in found]
    if len(set(versions)) != len(versions):
        raise MigrationError("Duplicate migration version numbers")
    return found


def migrate(db_path, directory=MIGRATIONS_DIR):
    """Apply all pending migrations. Returns the list of versions applied this call."""
    applied_now = []
    with connect(db_path) as conn:
        conn.execute(BOOTSTRAP)
    for version, name, sql, checksum in discover(directory):
        with connect(db_path) as conn:
            row = conn.execute("SELECT checksum FROM schema_migrations WHERE version = ?", (version,)).fetchone()
            if row:
                if row["checksum"] != checksum:
                    raise MigrationError(f"Migration {version}_{name} was modified after being applied")
                continue
            # executescript() would COMMIT first, so drive the transaction by hand.
            conn.isolation_level = None
            try:
                conn.execute("BEGIN")
                for stmt in _statements(sql):
                    conn.execute(stmt)
                conn.execute("INSERT INTO schema_migrations(version, name, checksum) VALUES (?, ?, ?)", (version, name, checksum))
                conn.execute("COMMIT")
            except Exception as exc:
                if conn.in_transaction:
                    conn.execute("ROLLBACK")
                raise MigrationError(f"Migration {version}_{name} failed: {exc}") from exc
            applied_now.append(version)
    return applied_now


def _statements(sql):
    """Split a script into complete statements (sqlite3.complete_statement handles quotes/semicolons)."""
    buf = ""
    for line in sql.splitlines(keepends=True):
        buf += line
        if sqlite3.complete_statement(buf):
            if buf.strip():
                yield buf.strip()
            buf = ""
    if buf.strip():
        raise MigrationError(f"Incomplete SQL statement: {buf.strip()[:60]}")
