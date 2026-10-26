"""Shared pieces: the learner's language/level context and the error types the router maps to HTTP."""
from .. import settings
from ..curriculum.service import NeedsProfile, NotFound  # noqa: F401  (same meaning as in lessons; re-exported)
from ..learner import service as learner_service
from ..repositories import curriculum, learner


class Forbidden(Exception):
    """The request is not available to this learner's age group."""


class InvalidInput(ValueError):
    """A semantic validation failure tied to one request field."""

    def __init__(self, field, message):
        super().__init__(message)
        self.field = field
        self.message = message


def learner_context(conn, user_id):
    ctx = curriculum.get_learner_context(conn, user_id)
    if ctx is None:
        raise NeedsProfile()
    ctx["fallback_id"] = learner.get_language_id(conn, settings.FALLBACK_CONTENT_LANGUAGE)
    return learner_service.with_age_group(conn, ctx)
