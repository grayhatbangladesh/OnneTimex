"""
DRF exception handler — standard MeetSoc error envelope.
"""
from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework import status


def custom_exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is None:
        return None

    detail = response.data
    code = "VALIDATION_ERROR"
    if isinstance(detail, dict):
        if "detail" in detail and len(detail) == 1:
            message = str(detail["detail"])
            code = getattr(exc, "default_code", code).upper() if hasattr(exc, "default_code") else code
        else:
            message = "Validation failed."
            code = "VALIDATION_ERROR"
    else:
        message = str(detail)
        code = "ERROR"

    response.data = {
        "success": False,
        "error": {
            "code": code,
            "message": message,
            "details": detail if isinstance(detail, dict) else {"non_field_errors": [message]},
        },
    }
    return response


class APIError(Exception):
    """Raise from views for structured errors."""

    def __init__(self, message, code="ERROR", status_code=status.HTTP_400_BAD_REQUEST, details=None):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
