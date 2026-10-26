"""The admin layer's domain errors. Services raise these; the router maps them to HTTP (no HTTP in the services)."""


class AdminError(Exception):
    pass


class NotFound(AdminError):
    """No such entity (or an id that belongs to a different parent)."""


class InvalidInput(AdminError):
    """A request value that fails service-level validation: tied to one field (422)."""

    def __init__(self, field, message):
        super().__init__(message)
        self.field, self.message = field, message


class Conflict(AdminError):
    """The request is well-formed but the content's state refuses it (409): published content, a stale revision, a slug already taken, content in use."""

    def __init__(self, code, message, **extra):
        super().__init__(message)
        self.code, self.message, self.extra = code, message, extra     # extra: e.g. current_revision, so a client can reload and retry


class ValidationFailed(AdminError):
    """Publish-time validation found errors (422 with the structured findings)."""

    def __init__(self, findings):
        super().__init__("validation failed")
        self.findings = findings
