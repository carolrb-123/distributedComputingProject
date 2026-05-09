class WorkerCapacityError(RuntimeError):
    """Raised when a healthy worker is temporarily full."""


class AdmissionTimeoutError(RuntimeError):
    """Raised when a request waits too long for worker capacity."""
