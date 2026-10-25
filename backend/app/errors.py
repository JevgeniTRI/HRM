class NotFoundError(Exception):
    """The requested domain record does not exist."""


class ConflictError(Exception):
    """The change conflicts with existing records or their relationships."""


class ValidationError(ValueError):
    """Input violates a business rule."""


class PayloadTooLargeError(Exception):
    """The uploaded document exceeds the allowed size."""


class ForbiddenError(Exception):
    """The authenticated actor cannot perform the requested domain operation."""
