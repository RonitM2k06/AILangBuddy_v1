"""SQLite access: one short-lived connection per unit of work, foreign keys always on."""
import sqlite3
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def connect(db_path):
    """Open a connection, commit on success, roll back on error, and always close."""
    conn = sqlite3.connect(Path(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")  # per-connection in SQLite, so set it every time
    try:
        yield conn
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()
