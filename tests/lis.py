"""Helpers for listening tests. Answer keys are read from the database, never from an API response."""
from backend import main
from backend.db import connect


def db():
    return connect(main.DB_PATH)


def activities(client):
    return client.get("/api/listening").json()["activities"]


def activity_id(client, slug):
    return next(a["id"] for a in activities(client) if a["slug"] == slug)


def correct_option(activity_id):
    with db() as conn:
        return conn.execute("SELECT o.id FROM listening_options o JOIN listening_activities a ON a.id = o.activity_id "
                            "WHERE a.id = ? AND o.item_id = a.item_id", (activity_id,)).fetchone()[0]


def wrong_options(activity_id):
    with db() as conn:
        return [r[0] for r in conn.execute("SELECT o.id FROM listening_options o JOIN listening_activities a ON a.id = o.activity_id "
                                           "WHERE a.id = ? AND o.item_id <> a.item_id ORDER BY o.sort_order", (activity_id,))]


def answer(client, activity_id, option_id, **extra):
    return client.post(f"/api/listening/{activity_id}/attempts", json={"option_id": option_id, **extra})


def answer_right(client, slug):
    a = activity_id(client, slug)
    return answer(client, a, correct_option(a))


def answer_wrong(client, slug, which=0):
    a = activity_id(client, slug)
    return answer(client, a, wrong_options(a)[which])
