"""Runtime security settings, read from the environment at call time (so tests can override them)."""
import os

DEMO_HANDLE = "demo-alex"  # the prototype's built-in learner
COOKIE_NAME = "llb_session"
SESSION_TTL_DAYS = 7                 # absolute lifetime: a session ends this long after sign-in, however active it is (never extended)
SESSION_TOUCH_SECONDS = 60           # last_seen_at is written at most this often per session (no write per request)

# ---------- authentication throttling (Phase 14C). Per process, in memory: see backend/auth/throttle.py ----------
LOGIN_ACCOUNT_MAX_FAILURES = 5       # failed sign-ins for one account (any address) per window
LOGIN_IP_MAX_FAILURES = 20           # failed sign-ins from one address (any accounts) per window
LOGIN_WINDOW_SECONDS = 900
REGISTER_IP_MAX = 30                 # registrations attempted from one address per window
REGISTER_WINDOW_SECONDS = 3600
PASSWORD_CHANGE_MAX_FAILURES = 5     # wrong current passwords per user per window
PASSWORD_CHANGE_WINDOW_SECONDS = 900
THROTTLE_MAX_KEYS = 10_000           # the most keys any one limiter remembers


# ---------- TOTP two-factor authentication (Phase 14D) ----------
TOTP_DIGITS = 6
TOTP_PERIOD_SECONDS = 30
TOTP_DRIFT_STEPS = 1                 # a code for the previous or the next 30 s step is accepted too, never further
TOTP_SECRET_BYTES = 20               # 160-bit secret, the RFC 4226 recommendation for HMAC-SHA1
TOTP_ISSUER = "LingoBuddy"
TOTP_SETUP_SECONDS = 600             # a started setup must be confirmed within this
MFA_COOKIE_NAME = "llb_mfa_challenge"
MFA_CHALLENGE_SECONDS = 300          # between a correct password and the second factor
MFA_CHALLENGE_MAX_ATTEMPTS = 5       # wrong codes per challenge; also the schema CHECK on login_challenges.attempts
MFA_MAX_FAILURES = 10                # wrong second-factor codes per user per window, across every challenge and form (in the database)
MFA_WINDOW_SECONDS = 900
RECOVERY_CODE_COUNT = 10


def totp_enc_key():
    """TOTP_ENC_KEY: 32 random bytes, base64url-encoded (padding optional). Returns the raw value or None; backend/auth/totp_crypto.py
    validates it. Never logged, stored or returned."""
    value = os.getenv("TOTP_ENC_KEY", "").strip()
    return value or None


def throttle_limit(name) -> int:
    """The limit `name` (one of the *_MAX / *_MAX_FAILURES settings above). An environment variable of the same name overrides it, e.g.
    REGISTER_IP_MAX=200 for a classroom where many learners share one public address. Invalid or non-positive values are ignored."""
    try:
        value = int(os.getenv(name, ""))
    except ValueError:
        return globals()[name]
    return value if value > 0 else globals()[name]


def session_idle_minutes() -> int:
    """SESSION_IDLE_MINUTES (default 30): a session unused for this long ends at its next request. Bounded to 1 minute .. the absolute lifetime."""
    try:
        value = int(os.getenv("SESSION_IDLE_MINUTES", "30"))
    except ValueError:
        return 30
    return min(max(value, 1), SESSION_TTL_DAYS * 24 * 60)


def demo_mode() -> bool:
    """While on (default), the prototype keeps working without login: the demo learner's state
    and the AI endpoint are reachable anonymously. Set DEMO_MODE=0 to require authentication."""
    return os.getenv("DEMO_MODE", "1").strip().lower() not in ("0", "false", "no", "off")


def cookie_secure() -> bool:
    """Set COOKIE_SECURE=1 when served over HTTPS so the session cookie is never sent in clear text."""
    return os.getenv("COOKIE_SECURE", "0").strip().lower() in ("1", "true", "yes", "on")


def trusted_origins() -> frozenset:
    """TRUSTED_ORIGINS: comma-separated origins (e.g. "https://lingo.example") that state-changing requests may come from. Unset means "this
    request's own scheme and Host" (see backend/security/csrf.py). Set it when a proxy in front of the app changes the Host header."""
    raw = os.getenv("TRUSTED_ORIGINS", "")
    return frozenset(o.strip().lower().rstrip("/") for o in raw.split(",") if o.strip())


# Meanings and explanations fall back to this language when the learner's native language has no translation yet.
FALLBACK_CONTENT_LANGUAGE = "en"


# ---------- speaking input (Phase 7B) ----------
# Recording limits. The client-reported duration is only bounded (the server does not decode audio); size is enforced exactly.
MAX_RECORDING_BYTES = 5_000_000      # ~30 s of compressed speech is a few hundred KB
MIN_RECORDING_BYTES = 16             # anything smaller than a header plus a little audio is an empty recording
MAX_RECORDING_MS = 30_000
STT_STALE_PROCESSING_SECONDS = 120   # a transcription still "processing" after this long is treated as failed


def stt_provider_name() -> str:
    """Which speech-to-text provider to use: 'none' (default: speaking sessions can be recorded but not transcribed),
    'mock' (deterministic, for development and tests) or 'groq' (Whisper via Groq, needs GROQ_API_KEY).
    Nothing is ever sent to a third party unless STT_PROVIDER names it explicitly."""
    return os.getenv("STT_PROVIDER", "none").strip().lower() or "none"


def stt_model() -> str:
    return os.getenv("STT_MODEL", "whisper-large-v3-turbo").strip()


def stt_timeout_seconds() -> float:
    try:
        return min(max(float(os.getenv("STT_TIMEOUT_SECONDS", "15")), 0.05), 120.0)
    except ValueError:
        return 15.0


def recordings_dir():
    """Where recordings are stored: outside the database and, by default, outside the repository."""
    from pathlib import Path
    return Path(os.getenv("RECORDINGS_DIR") or Path.home() / ".lingobuddy" / "recordings")


def keep_recordings() -> bool:
    """By default the recording file is deleted once its transcript is saved (voice data minimisation).
    Set SPEAKING_KEEP_AUDIO=1 to keep it."""
    return os.getenv("SPEAKING_KEEP_AUDIO", "0").strip().lower() in ("1", "true", "yes", "on")


# ---------- pronunciation assessment (Phase 7C) ----------
PRON_MAX_ATTEMPTS = 5                    # assessment attempts (including failed ones) kept per speaking session
PRON_AUDIO_GRACE_SECONDS = 600           # with a pronunciation provider configured, a transcribed recording waits this long for its assessment
FAILED_AUDIO_GRACE_SECONDS = 86_400      # a failed session keeps its recording for a retry for at most this long


def pron_provider_name() -> str:
    """Which pronunciation provider to use: 'none' (default: the word check works, pronunciation is reported as unavailable)
    or 'mock' (a deterministic test provider whose scores come from controlled test input, never from a real measurement).
    There is no real acoustic provider yet; see docs/ARCHITECTURE.md."""
    return os.getenv("PRONUNCIATION_PROVIDER", "none").strip().lower() or "none"


def pron_timeout_seconds() -> float:
    try:
        return min(max(float(os.getenv("PRONUNCIATION_TIMEOUT_SECONDS", "15")), 0.05), 120.0)
    except ValueError:
        return 15.0


# ---------- child game (Phase 8) ----------
MAX_LIVES = 5                 # also the schema CHECK on child_game_state.lives; a test ties the two together
LIFE_REGEN_SECONDS = 600      # one life comes back every 10 minutes


# ---------- parent portal (Phase 9) ----------
PARENT_CODE_TTL_SECONDS = 900     # a link code is valid for 15 minutes and works once
PARENT_CODE_LENGTH = 10
MAX_CHILDREN_PER_PARENT = 10
MAX_PARENTS_PER_CHILD = 4
PARENT_CODE_MAX_FAILURES = 5      # wrong codes tried by one parent per window (per process, like the login throttle)
PARENT_CODE_WINDOW_SECONDS = 900


# ---------- AI tutor and roleplay (Phase 11) ----------
AI_MAX_MESSAGE_CHARS = 500          # one learner message / roleplay answer
AI_MAX_REPLY_CHARS = 1200           # a model reply longer than this is cut, never stored whole
AI_HISTORY_WINDOW = 8               # messages of a conversation sent to the model, however long the stored history is
AI_MAX_PROMPT_CHARS = 6000          # hard bound on everything sent to a model in one call
AI_MAX_MESSAGES_PER_CONVERSATION = 100
AI_MAX_CONVERSATIONS_PER_LEARNER = 50
AI_MAX_FACTS = 8
ROLEPLAY_MAX_ATTEMPTS = 3          # tries per step before the model answer is shown


def ai_provider_name() -> str:
    """AI_PROVIDER: 'mock' (default, deterministic and offline: works with no API key) or 'llm' (the LLM configured in .env /
    the environment, used only for teen and adult learners). Unset or unknown means 'mock'."""
    return os.getenv("AI_PROVIDER", "mock").strip().lower()


def ai_timeout_seconds() -> float:
    try:
        return max(1.0, min(60.0, float(os.getenv("AI_TIMEOUT_SECONDS", "15"))))
    except ValueError:
        return 15.0


# ---------- adaptive AI (Phase 12) ----------
# Semantic grading of roleplay answers. confidence is 0..1. An exact (normalised) match is always accepted first.
SEMANTIC_ACCEPT_AT = 0.80           # deterministic grader: at or above this the answer is accepted as meaning the same thing
SEMANTIC_CLOSE_AT = 0.50            # at or above this (and below ACCEPT) the answer is "close": not accepted, but the hint says so
SEMANTIC_LLM_FLOOR = 0.66           # an external grader is only consulted for answers at or above this and below ACCEPT
SEMANTIC_LLM_ACCEPT_AT = 0.85       # ...and its answer is only believed at or above this confidence
AI_MAX_NEW_MICRO_LESSONS_PER_DAY = 3
AI_MICRO_LESSON_TTL_DAYS = 7
AI_MAX_RECOMMENDATIONS = 6
AI_MAX_INSIGHTS = 5
AI_TREND_WINDOW = 10                # attempts in a window when comparing recent accuracy with the window before it
AI_TREND_MIN_ATTEMPTS = 5           # each window needs at least this many attempts before a trend is claimed
AI_TREND_DELTA = 0.15               # a trend is claimed only if accuracy moved by at least this much


# ---------- admin CMS + analytics (Phase 13) ----------
REQUIRED_TRANSLATION_LANGUAGE = "en"   # every vocabulary item used by published content needs a translation in this language (not configurable)
LISTENING_OPTION_COUNT = 3             # a listening activity offers exactly this many options
SMALL_CELL = 5                         # any aggregate that involves fewer learners than this is suppressed
ANALYTICS_MAX_WINDOW_DAYS = 365
ANALYTICS_WINDOWS = {"7d": 7, "30d": 30, "90d": 90}
APP_VERSION = "0.13.0"


# ---------- legacy prototype hardening (Phase 14A) ----------
LEGACY_STATE_MAX_BYTES = 65_536        # PUT /api/state/{handle}: a larger body is refused with 413, never truncated
LEGACY_STATE_VERSION = 1               # the only state version the frontend writes (engine.js DEMO().v)
LEGACY_AI_MAX_MESSAGE_CHARS = 500      # POST /api/ai: one history message
LEGACY_AI_MAX_HISTORY = 12             # ...and at most this many messages per request
LEGACY_AI_MAX_REQUESTS = 20            # requests per caller (user, or client address when anonymous) per window
LEGACY_AI_WINDOW_SECONDS = 60
LEGACY_AI_MAX_TRACKED_CALLERS = 10_000


def demo_live_ai() -> bool:
    """DEMO_LIVE_AI=1 lets ANONYMOUS visitors' legacy /api/ai requests reach the configured LLM. Off by default: anonymous visitors get the
    offline engine. It never applies to signed-in users (a child is always offline, whatever this says)."""
    return os.getenv("DEMO_LIVE_AI", "0").strip().lower() in ("1", "true", "yes", "on")


def admin_ref_secret() -> bytes:
    """The key the admin learner references are an HMAC under. ADMIN_REF_SECRET (set it to keep references stable across restarts); otherwise a random key made
    when the process starts, so references then last until the next restart. Never logged, never returned."""
    value = os.getenv("ADMIN_REF_SECRET", "").strip()
    return value.encode() if value else _PROCESS_SECRET


import secrets as _secrets  # noqa: E402

_PROCESS_SECRET = _secrets.token_bytes(32)
