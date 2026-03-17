from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema
from .serializers import ForgotPasswordRequestSerializer
from .services import reset_password

from core.untils.api_response import error_response, success_response

from .serializers import (
    LoginRequestSerializer,
    LogoutRequestSerializer,
    RefreshRequestSerializer,
)
from .services import AuthServiceError, login, logout, refresh


class LoginView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=LoginRequestSerializer)
    def post(self, request: Request):
        serializer = LoginRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                code=1001,
                message="Invalid request data",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = login(
                email=serializer.validated_data["email"],
                password=serializer.validated_data["password"],
            )
        except AuthServiceError as exc:
            return error_response(
                code=1002, message=str(exc), status_code=status.HTTP_401_UNAUTHORIZED
            )

        return success_response(
            result=result, code=1000, status_code=status.HTTP_200_OK
        )


class RefreshTokenView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=RefreshRequestSerializer)
    def post(self, request: Request):
        serializer = RefreshRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                code=1001,
                message="Invalid request data",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = refresh(serializer.validated_data["refreshToken"])
        except AuthServiceError as exc:
            return error_response(
                code=1003, message=str(exc), status_code=status.HTTP_401_UNAUTHORIZED
            )

        return success_response(
            result=result, code=1000, status_code=status.HTTP_200_OK
        )


class LogoutView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=LogoutRequestSerializer)
    def post(self, request: Request):
        serializer = LogoutRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                code=1001,
                message="Invalid request data",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        try:
            logout(serializer.validated_data["refreshToken"])
        except AuthServiceError as exc:
            return error_response(
                code=1004, message=str(exc), status_code=status.HTTP_401_UNAUTHORIZED
            )

        return success_response(
            result={"loggedOut": True}, code=1000, status_code=status.HTTP_200_OK
        )


class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=ForgotPasswordRequestSerializer)
    def post(self, request: Request):
        serializer = ForgotPasswordRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                code=1001,
                message="Invalid request data",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        try:
            reset_password(serializer.validated_data["email"])
        except AuthServiceError as exc:
            return error_response(
                code=1002, message=str(exc), status_code=status.HTTP_404_NOT_FOUND
            )

        return success_response(
            result={
                "message": "If the account exists, a new password will be emailed."
            },
            code=1000,
            status_code=status.HTTP_200_OK,
        )
