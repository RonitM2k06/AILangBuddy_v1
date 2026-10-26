"""The global browser-request (CSRF) guard. No FastAPI routing in here: `rejection(...)` decides, the middleware in main.py applies it to
every request before any route runs, so no router can forget it.

Every state-changing request (POST, PUT, PATCH, DELETE), on any path, must carry:
  * X-Requested-With: XMLHttpRequest, exactly; and
  * Content-Type: application/json (parameters such as charset allowed), except on the routes listed in RAW_MEDIA, which take a raw
    media body: there the custom header alone is required (it already forces a preflight) and the route itself checks the media type
    (the recording upload answers 415 for anything but its audio allow-list). No other route may send a non-JSON write.
A browser cannot send a custom header or a JSON/audio content type cross-origin without a CORS preflight, and this app grants no CORS, so
a forged form post, <img>, fetch(mode: "no-cors") or sendBeacon is refused even when the SameSite=Lax cookie comes along. Body-less writes
get no exemption: the frontend sends the JSON content type on every write, with or without a body.

Origin: when a request names one, it must be this application's own origin (TRUSTED_ORIGINS if configured, otherwise the scheme and Host
of the request itself). "null" and any other origin are refused. When there is no Origin but there is a Referer, the Referer's origin must
match in the same way. A request with neither still has to pass the header rules above: the absence of Origin is never a bypass.
Safe methods (GET, HEAD, OPTIONS) are never refused here; they must not change anything."""
import re
from urllib.parse import urlsplit

from .. import settings

UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
HEADER, VALUE = "x-requested-with", "XMLHttpRequest"
JSON = "application/json"

# The only routes that take a raw, non-JSON body (method, exact path pattern). Their own validation decides which media types they take.
RAW_MEDIA = (
    ("POST", re.compile(r"^/api/speaking/sessions/\d+/recording$")),
)

HEADERS_MESSAGE = "CSRF check failed: send Content-Type: application/json and X-Requested-With: XMLHttpRequest"
MEDIA_MESSAGE = "CSRF check failed: send X-Requested-With: XMLHttpRequest with the recording"
ORIGIN_MESSAGE = "CSRF check failed: the request did not come from this site"


def media_type(content_type):
    return (content_type or "").split(";")[0].strip().lower()


def is_raw_media(method, path):
    return any(m == method and pattern.match(path) for m, pattern in RAW_MEDIA)


def _origin_of(url):
    try:
        parts = urlsplit(url)
    except ValueError:
        return None
    if parts.scheme not in ("http", "https") or not parts.netloc:
        return None
    return f"{parts.scheme}://{parts.netloc}".lower()


def own_origins(scheme, host):
    """The origins this application answers as. TRUSTED_ORIGINS (comma-separated, e.g. behind a proxy that rewrites Host) replaces the
    derived one; otherwise the request's own scheme and Host, plus https://Host when COOKIE_SECURE says the site is served over HTTPS
    (a TLS-terminating proxy usually forwards plain http)."""
    configured = settings.trusted_origins()
    if configured:
        return configured
    if not host:
        return frozenset()
    host = host.strip().lower()
    found = {f"{scheme}://{host}"}
    if settings.cookie_secure():
        found.add(f"https://{host}")
    return frozenset(found)


def rejection(method, path, headers, scheme):
    """None if the request may proceed, otherwise the message for a 403. `headers` is a case-insensitive mapping (Starlette Headers)."""
    if method not in UNSAFE_METHODS:
        return None
    raw = is_raw_media(method, path)
    if headers.get(HEADER) != VALUE:
        return MEDIA_MESSAGE if raw else HEADERS_MESSAGE
    if not raw and media_type(headers.get("content-type")) != JSON:
        return HEADERS_MESSAGE
    allowed = own_origins(scheme, headers.get("host"))
    origin = headers.get("origin")
    if origin is not None:
        if origin.strip().lower().rstrip("/") not in allowed:
            return ORIGIN_MESSAGE
    else:
        referer = headers.get("referer")
        if referer and _origin_of(referer) not in allowed:
            return ORIGIN_MESSAGE
    return None
