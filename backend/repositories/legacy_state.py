"""Legacy prototype state: one JSON blob per learner. Behaviour is unchanged from the original endpoints."""
import json

from ..db import connect


def get_state(db_path, user_id):
    with connect(db_path) as conn:
        row = conn.execute("SELECT data FROM state WHERE user_id = ?", (user_id,)).fetchone()
    return json.loads(row["data"]) if row else None


def put_state(db_path, user_id, data):
    with connect(db_path) as conn:
        conn.execute(
            "INSERT INTO state(user_id, data) VALUES(?, ?) ON CONFLICT(user_id) DO UPDATE SET data=excluded.data, updated=CURRENT_TIMESTAMP",
            (user_id, json.dumps(data)),
        )
