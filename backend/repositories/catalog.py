"""Read access to the language/city catalogue. SQL lives here, not in the API layer."""
from ..db import connect


def list_languages(db_path):
    with connect(db_path) as conn:
        rows = conn.execute("SELECT code, name, native_name, tts_locale FROM languages ORDER BY id").fetchall()
    return [dict(r) for r in rows]


def list_cefr_levels(db_path):
    with connect(db_path) as conn:
        rows = conn.execute("SELECT code, rank, label FROM cefr_levels ORDER BY rank").fetchall()
    return [dict(r) for r in rows]


def list_cities(db_path):
    """Cities with their language codes in display order (single query, no N+1)."""
    with connect(db_path) as conn:
        rows = conn.execute(
            """SELECT c.id, c.slug, c.name, c.flag, c.emoji, c.tagline, c.blurb, c.is_ready, l.code AS lang
               FROM cities c
               LEFT JOIN city_languages cl ON cl.city_id = c.id
               LEFT JOIN languages l ON l.id = cl.language_id
               ORDER BY c.id, cl.sort_order"""
        ).fetchall()
    cities = {}
    for r in rows:
        city = cities.setdefault(r["id"], {
            "slug": r["slug"], "name": r["name"], "flag": r["flag"], "emoji": r["emoji"],
            "tagline": r["tagline"], "blurb": r["blurb"], "ready": bool(r["is_ready"]), "languages": [],
        })
        if r["lang"]:
            city["languages"].append(r["lang"])
    return list(cities.values())


def list_language_levels(db_path):
    """Supported (language, CEFR level) combinations, grouped by language, levels from easiest up."""
    with connect(db_path) as conn:
        rows = conn.execute(
            """SELECT l.code AS language, ll.cefr_code AS level
               FROM language_levels ll
               JOIN languages l ON l.id = ll.language_id
               JOIN cefr_levels c ON c.code = ll.cefr_code
               ORDER BY l.id, c.rank"""
        ).fetchall()
    grouped = {}
    for r in rows:
        grouped.setdefault(r["language"], []).append(r["level"])
    return [{"language": lang, "levels": levels} for lang, levels in grouped.items()]


def content_review(db_path, language_code):
    """The recorded review of a language's content (migration 0034), or None when nothing is recorded."""
    with connect(db_path) as conn:
        row = conn.execute(
            """SELECT l.code AS language, r.editorial_status, r.native_review_status, r.last_editorial_reviewed_at, r.known_limitations
               FROM content_reviews r JOIN languages l ON l.id = r.language_id WHERE l.code = ?""", (language_code,)).fetchone()
    return dict(row) if row else None


def language_code(conn, language_id):
    """The code of a language id ('hi', 'mr', ...): typed answers are compared with that language's rules (textnorm.answer_key)."""
    row = conn.execute("SELECT code FROM languages WHERE id = ?", (language_id,)).fetchone()
    return row["code"] if row else None
