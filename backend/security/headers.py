"""Security headers for every response the application produces (pages, static files, API answers, 4xx errors and CSRF refusals).

  * X-Content-Type-Options: nosniff and X-Frame-Options: DENY everywhere; Referrer-Policy: strict-origin-when-cross-origin.
  * Content-Security-Policy, restricted to directives the current frontend cannot break: no plugins, no <base> rewriting, no framing, forms
    submit only to this site. script-src / style-src are NOT restricted yet: the prototype renders through innerHTML with ~54 inline event
    handlers (onclick=..., onsubmit=...) and inline styles, so a script-src without 'unsafe-inline' would break it. That migration is deferred.
  * Strict-Transport-Security only when the request arrived over HTTPS or COOKIE_SECURE=1 says the site is served over HTTPS, so local
    plain-HTTP development is never pinned to HTTPS.
  * Cache-Control: no-store on every /api response: they are per-user, session-dependent or security-sensitive. Pages and static files keep
    the default caching behaviour."""
from .. import settings

CSP = "object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'"
HSTS = "max-age=31536000; includeSubDomains"
ALWAYS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Content-Security-Policy": CSP,
}


def is_api(path):
    return path == "/api" or path.startswith("/api/")


def apply(response_headers, path, scheme):
    for name, value in ALWAYS.items():
        response_headers[name] = value
    if scheme == "https" or settings.cookie_secure():
        response_headers["Strict-Transport-Security"] = HSTS
    if is_api(path):
        response_headers["Cache-Control"] = "no-store"
