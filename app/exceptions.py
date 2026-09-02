"""Domain level exception hierarchy for AISCaMS.

Every exception carries an HTTP status so the API layer can translate a domain
failure into a meaningful response without knowing the details of the domain.
"""


class AiscamsError(Exception):
    """Base class for every error raised by the AISCaMS domain layer."""

    status_code = 400

    def __init__(self, message, details=None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def to_dict(self):
        payload = {"error": self.__class__.__name__, "message": self.message}
        if self.details:
            payload["details"] = self.details
        return payload


class ValidationError(AiscamsError):
    """Raised when user supplied input fails validation."""

    status_code = 400


class NotFoundError(AiscamsError):
    """Raised when an entity cannot be located in the repository."""

    status_code = 404


class PermissionDeniedError(AiscamsError):
    """Raised when an actor attempts an operation outside its role."""

    status_code = 403


class BookingConflictError(AiscamsError):
    """Raised when a booking overlaps an existing confirmed booking."""

    status_code = 409


class ResourceUnavailableError(AiscamsError):
    """Raised when a resource cannot be booked because of its status."""

    status_code = 409


class CapacityError(ValidationError):
    """Raised when a resource cannot host the requested number of people."""


class EquipmentError(ValidationError):
    """Raised when a resource does not provide the requested equipment."""


class InvalidTransitionError(AiscamsError):
    """Raised when a service request state transition is not allowed."""

    status_code = 409


class AuthenticationError(AiscamsError):
    """Raised when credentials are invalid or the account is inactive."""

    status_code = 401
