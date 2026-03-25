"""
Triage exceptions
=================
Custom exceptions for the triage pipeline.
"""


class InvalidTransitionError(Exception):
    """
    Raised when a status transition is not permitted.

    Example:
        raise InvalidTransitionError(
            "Cannot transition from 'resolved' to 'acknowledged'."
        )
    """
