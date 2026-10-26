import ipaddress
import os
import socket

# Phase 14F: no test may open a network connection to anything but this machine, whatever the code under test does. In this process every
# TCP/UDP connect and every host-name lookup for a non-loopback host is refused (and remembered: code that swallows the error still fails
# the test, see _network_isolation below). Child processes (the frontend tests' uvicorn servers) cannot be patched, so they inherit a proxy
# that does not exist: httpx, the only HTTP client the backend uses, sends every request for a non-local host to it and fails.
_LOCAL_NAMES = frozenset({"localhost", "testserver"})
BLOCKED_CONNECTIONS = []


class ExternalNetworkBlocked(AssertionError):
    pass


def _is_local(host):
    if isinstance(host, bytes):
        host = host.decode()
    if host is None or host in _LOCAL_NAMES:
        return True
    try:
        return ipaddress.ip_address(str(host).split("%")[0]).is_loopback
    except ValueError:
        return False


def _refuse(host):
    if isinstance(host, bytes):
        host = host.decode()
    BLOCKED_CONNECTIONS.append(str(host))
    raise ExternalNetworkBlocked(f"a test tried to reach {host!r}: tests may only talk to this machine")


def _guard_connect(real):
    def connect(self, address, *args):
        if self.family in (socket.AF_INET, socket.AF_INET6) and not _is_local(address[0]):
            _refuse(address[0])
        return real(self, address, *args)
    return connect


def _guard_getaddrinfo(real):
    def getaddrinfo(host, *args, **kwargs):
        if not _is_local(host):
            _refuse(host)
        return real(host, *args, **kwargs)
    return getaddrinfo


socket.socket.connect = _guard_connect(socket.socket.connect)
socket.socket.connect_ex = _guard_connect(socket.socket.connect_ex)
socket.getaddrinfo = _guard_getaddrinfo(socket.getaddrinfo)
DEAD_PROXY = "http://127.0.0.1:9"                 # the discard port on loopback: nothing listens there
for _var in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
    os.environ[_var] = DEAD_PROXY
os.environ["NO_PROXY"] = os.environ["no_proxy"] = "127.0.0.1,localhost,::1"

# No test may reach a real model provider. backend.main copies .env into the environment with setdefault() when it is imported, so the
# provider settings are blanked BEFORE that import: then the developer's real keys are never loaded, in this process or in the test servers
# the frontend tests start (they inherit this environment). A test that needs a "configured" provider sets a fake value or patches
# main.provider, and stubs main.call_llm (the autouse fixture below makes an un-stubbed call fail instead of going out).
PROVIDER_ENV = ("GROQ_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OPENAI_BASE_URL", "OLLAMA_URL", "LLM_MODEL")
for _var in PROVIDER_ENV:
    os.environ[_var] = ""
os.environ.pop("DEMO_LIVE_AI", None)
# A fixed, test-only TOTP encryption key (Phase 14D): 32 bytes, base64url. Set here so in-process tests and the test servers share it;
# tests about a missing or malformed key remove or replace it themselves. It protects nothing real: test databases are temp files.
TEST_TOTP_ENC_KEY = "dGVzdC1vbmx5LXRvdHAta2V5LWxpbmdvYnVkZHkhISE"
os.environ["TOTP_ENC_KEY"] = TEST_TOTP_ENC_KEY

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from backend import main  # noqa: E402
from backend.auth import service  # noqa: E402
from backend.db.migrate import migrate  # noqa: E402
from backend.legacy import ai as legacy_ai  # noqa: E402


class RealProviderCalled(AssertionError):
    pass


async def _no_real_provider(*_args, **_kwargs):
    raise RealProviderCalled("a test reached main.call_llm without stubbing it: that would have called a real model provider")


REAL_CALL_LLM = main.call_llm                    # the unpatched provider call, for the tests that prove it cannot leave the machine


@pytest.fixture(autouse=True)
def _network_isolation():
    """Safety net for every test: fails it if anything tried to reach another host during it, even if the code swallowed the refusal."""
    before = len(BLOCKED_CONNECTIONS)
    yield
    assert len(BLOCKED_CONNECTIONS) == before, f"external connections attempted: {BLOCKED_CONNECTIONS[before:]}"


@pytest.fixture(autouse=True)
def _real_database_isolation(tmp_path, monkeypatch):
    """Safety net for every test: main.DB_PATH starts as a temp file, so a test that forgets the client fixture can never open the real
    buddy.db. (The client fixture then points it at its own fresh database.)"""
    monkeypatch.setattr(main, "DB_PATH", tmp_path / "isolated.db")


@pytest.fixture(autouse=True)
def _provider_isolation(monkeypatch):
    """Safety net for every test: the real LLM call is replaced (tests that want a model patch main.call_llm themselves), and the key
    variables stay blank even if something reloaded .env."""
    assert not main.GROQ_KEY and not main.ANTHROPIC_KEY and not main.OPENAI_KEY and not main.OLLAMA_URL, "a provider key was loaded in tests"
    monkeypatch.setattr(main, "call_llm", _no_real_provider)
    monkeypatch.delenv("DEMO_LIVE_AI", raising=False)
    legacy_ai.reset_throttle()


@pytest.fixture(autouse=True)
def _voice_isolation(tmp_path, monkeypatch):
    """Safety net for every test: recordings can only go to a temp dir (never the home directory or the repo) and no speech
    provider is configured unless a test asks for one."""
    monkeypatch.setenv("RECORDINGS_DIR", str(tmp_path / "recordings"))
    for var in ("STT_PROVIDER", "STT_TIMEOUT_SECONDS", "SPEAKING_KEEP_AUDIO", "STT_MODEL"):
        monkeypatch.delenv(var, raising=False)


@pytest.fixture
def db_path(tmp_path):
    """A fresh, fully migrated database in a temp dir. Never the real buddy.db."""
    path = tmp_path / "test.db"
    migrate(path)
    return path


# What the real frontend sends on every request (frontend/profile.js api(), admin.js, engine.js): the browser-request signal the global
# CSRF guard requires on writes (backend/security/csrf.py). Test "browsers" behave like the frontend unless a test is about the guard
# itself; those use a bare TestClient(main.app), which sends neither header.
FRONTEND_HEADERS = {"X-Requested-With": "XMLHttpRequest", "Content-Type": "application/json"}
WRITE_SIGNAL = {"X-Requested-With": "XMLHttpRequest"}


# A frontend test server stands in for many different people who all reach it from 127.0.0.1, like a classroom behind one public address:
# its per-ADDRESS limits are raised through the documented environment override (settings.throttle_limit). Per-account and password-change
# limits are unchanged there; the throttles themselves are tested in-process (test_session_security.py).
SHARED_ADDRESS_LIMITS = {"REGISTER_IP_MAX": "100000", "LOGIN_IP_MAX_FAILURES": "100000"}


def browser():
    """A browser running the real frontend: its own cookie jar, the frontend's headers."""
    return TestClient(main.app, headers=dict(FRONTEND_HEADERS))


@pytest.fixture
def client(tmp_path, monkeypatch):
    path = tmp_path / "api.db"
    monkeypatch.setattr(main, "DB_PATH", path)
    monkeypatch.delenv("DEMO_MODE", raising=False)  # default: demo mode on
    service.reset_throttle()
    with TestClient(main.app, headers=dict(FRONTEND_HEADERS)) as c:  # entering the context runs the lifespan (migrations)
        yield c


@pytest.fixture
def client2(client):
    """A second browser: same app and database, separate cookie jar."""
    return browser()


@pytest.fixture
def lockdown(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "0")


PASSWORD = "correct horse battery"


def register(c, email, role="learner", password=PASSWORD, name="Test User"):
    r = c.post("/api/auth/register", json={"email": email, "password": password, "display_name": name, "role": role}, headers=WRITE_SIGNAL)
    assert r.status_code == 201, r.text
    return r.json()["user"]


def plant_mfa_session(c, email):
    """Give browser `c` a session for `email` that has passed a second factor (mfa_level 1), as /api/auth/2fa/verify would create, without
    the TOTP round trip (that flow is tested in test_two_factor.py). Since Phase 14D the admin API needs such a session."""
    from backend.auth import service as auth_service
    from backend.db import connect
    with connect(main.DB_PATH) as conn:
        uid = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()[0]
        token, _ = auth_service._start_session(conn, uid, auth_service.utcnow(), mfa_level=1, auth_method="password+totp")
    c.cookies.set("llb_session", token)
    return c


@pytest.fixture
def make_admin(client):
    def _make(email="admin@example.com"):
        from backend.manage import create_admin
        return create_admin(main.DB_PATH, email, PASSWORD, "Admin")
    return _make
