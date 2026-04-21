from rest_framework import status
from rest_framework.exceptions import (
    APIException,
    AuthenticationFailed,
    NotAuthenticated,
    PermissionDenied,
    ValidationError,
)
from rest_framework.views import exception_handler

from core.untils.api_response import error_response


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if isinstance(exc, (AuthenticationFailed, NotAuthenticated)):
        return error_response(
            code=2007,
            message=str(exc),
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    if isinstance(exc, PermissionDenied):
        return error_response(
            code=2008,
            message=str(exc),
            status_code=status.HTTP_403_FORBIDDEN,
        )

    if isinstance(exc, ValidationError):
        return error_response(
            code=2001,
            message="Invalid request data",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    if isinstance(exc, APIException):
        message = "Unexpected API error"
        if response is not None and isinstance(response.data, dict):
            detail = response.data.get("detail")
            if detail:
                message = str(detail)
        return error_response(
            code=2999,
            message=message,
            status_code=(
                response.status_code
                if response is not None
                else status.HTTP_400_BAD_REQUEST
            ),
        )

    if response is None:
        return error_response(
            code=5000,
            message="Internal server error",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return response
