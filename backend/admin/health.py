"""System health for the admin: safe facts only. Provider configuration is a yes/no, never a key, URL or path; no filesystem location, hostname or secret is
ever returned; the database check reports ok / not ok, not SQLite's own message."""
import os

from .. import settings
from ..db import connect
from ..auth import totp_crypto
from ..repositories import admin_content as content_repo
from ..repositories import security_events as security_repo

_LLM_KEYS = ("GROQ_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OLLAMA_URL")


def _set(name):
    return bool(os.getenv(name, "").strip())


def health(db_path):
    with connect(db_path) as conn:
        last = conn.execute("SELECT version, name, applied_at FROM schema_migrations ORDER BY version DESC LIMIT 1").fetchone()
        integrity = "ok" if content_repo.integrity_check(conn) == ["ok"] else "failed"
        foreign_keys = "ok" if not content_repo.foreign_key_violations(conn) else "violations"
        counts = {}
        for kind, table in content_repo.LIFECYCLE_TABLES.items():
            by_status = dict(conn.execute(f"SELECT status, COUNT(*) FROM {table} GROUP BY status").fetchall())
            counts[table] = {s: by_status.get(s, 0) for s in ("draft", "published", "archived")}
        admins, admins_mfa = security_repo.admin_mfa_counts(conn)
    return {
        "app_version": settings.APP_VERSION,
        "last_migration": {"version": last["version"], "name": last["name"], "applied_at": last["applied_at"]},
        "database": {"integrity": integrity, "foreign_keys": foreign_keys},
        "content": counts,
        "demo_mode": settings.demo_mode(),
        "security": _security(admins, admins_mfa),
        "providers": {"llm_configured": any(_set(k) for k in _LLM_KEYS), "speech_to_text_configured": settings.stt_provider_name() != "none",
                      "pronunciation_configured": settings.pron_provider_name() != "none", "tutor_uses_llm": settings.ai_provider_name() == "llm"},
    }


def _security(admins, admins_mfa):
    """Security configuration, as statuses only (Phase 14E): never a key, value, address or path. Warnings are what an operator should fix
    before serving real users. "Production" is not guessed from host names: the settings themselves are reported."""
    cookie_secure, key, demo, live_ai = settings.cookie_secure(), totp_crypto.key_status(), settings.demo_mode(), settings.demo_live_ai()
    warnings = []
    if not cookie_secure:
        warnings.append({"code": "cookie_not_secure", "severity": "warning",
                         "message": "COOKIE_SECURE is off: session cookies are also sent over plain HTTP. Turn it on wherever the site is served over HTTPS."})
    if key != "valid":
        warnings.append({"code": f"totp_key_{key}", "severity": "critical" if admins else "warning",
                         "message": f"TOTP_ENC_KEY is {key}: two-factor authentication cannot be set up or checked"
                                    + (", and administrators need it to use the admin console." if admins else ".")})
    if admins_mfa < admins:
        warnings.append({"code": "admins_without_two_factor", "severity": "warning",
                         "message": f"{admins - admins_mfa} of {admins} administrator account(s) have not turned on two-factor authentication and cannot use the admin console."})
    if demo:
        warnings.append({"code": "demo_mode_on", "severity": "warning",
                         "message": "DEMO_MODE is on: the legacy AI endpoint answers visitors who are not signed in (offline unless DEMO_LIVE_AI)."})
    if live_ai:
        warnings.append({"code": "demo_live_ai_on", "severity": "warning",
                         "message": "DEMO_LIVE_AI is on: visitors who are not signed in can reach the configured language model."})
    return {"cookie_secure": cookie_secure, "totp_key": key, "demo_mode": demo, "demo_live_ai": live_ai, "admins": admins,
            "admins_with_two_factor": admins_mfa, "warnings": warnings}
