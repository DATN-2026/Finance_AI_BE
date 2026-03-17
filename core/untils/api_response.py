from typing import Any

from rest_framework.response import Response


def success_response(result: Any, code: int = 1000, status_code: int = 200) -> Response:
    return Response({"code": code, "result": result}, status=status_code)


def error_response(code: int, message: str, status_code: int = 400) -> Response:
    return Response({"code": code, "message": message}, status=status_code)
