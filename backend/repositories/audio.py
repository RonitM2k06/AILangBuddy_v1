"""Audio metadata persistence. No audio bytes are ever stored: only where a sound can be fetched from."""

# Preference when an item has several playable assets: a shipped file, then a generated one, then a hosted external TTS URL.
_PRIORITY = "CASE provider WHEN 'static' THEN 0 WHEN 'generated' THEN 1 ELSE 2 END"


def item_speech(conn, item_id):
    """What is needed to speak an item with a synthesiser: its text, romanised form and the language's TTS locale."""
    row = conn.execute(
        """SELECT v.id, v.language_id, v.text, v.pronunciation, l.tts_locale AS locale
           FROM vocabulary_items v JOIN languages l ON l.id = v.language_id WHERE v.id = ?""", (item_id,)).fetchone()
    return dict(row) if row else None


def active_assets(conn, item_id):
    return [dict(r) for r in conn.execute(
        f"""SELECT id, provider, locale, voice, source_url, mime_type, duration_ms FROM audio_assets
            WHERE item_id = ? AND is_active = 1 ORDER BY {_PRIORITY}, id""", (item_id,)).fetchall()]


def all_assets(conn, item_id):
    return [dict(r) for r in conn.execute(
        f"""SELECT id, provider, locale, voice, source_url, mime_type, duration_ms, is_active FROM audio_assets
            WHERE item_id = ? ORDER BY {_PRIORITY}, id""", (item_id,)).fetchall()]


def insert_asset(conn, item_id, language_id, provider, locale, voice, source_url, mime_type, duration_ms, created_at):
    cur = conn.execute(
        """INSERT INTO audio_assets(item_id, language_id, provider, locale, voice, source_url, mime_type, duration_ms, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (item_id, language_id, provider, locale, voice, source_url, mime_type, duration_ms, created_at))
    return cur.lastrowid
