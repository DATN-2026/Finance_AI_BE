from django.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from core.untils.api_response import error_response, success_response
from apps.users.serializers import CreateUserSerializer, UserResponseSerializer
from apps.users.services import UserServiceError, create_user

from .serializers import (
    LoginRequestSerializer,
    LoginResponseSerializer,
    LogoutRequestSerializer,
    LogoutResponseSerializer,
    RefreshRequestSerializer,
    RefreshResponseSerializer,
    ForgotPasswordRequestSerializer,
    ForgotPasswordResponseSerializer,
)
from .services import AuthServiceError, login, logout, refresh, reset_password
from .permissions import JwtAuthentication


REFRESH_COOKIE_NAME = "refreshToken"
REFRESH_COOKIE_MAX_AGE = settings.JWT_REFRESH_TOKEN_LIFETIME_DAYS * 24 * 60 * 60


def _set_refresh_cookie(response, refresh_token: str):
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        max_age=REFRESH_COOKIE_MAX_AGE,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="Lax",
    )


def _delete_refresh_cookie(response):
    response.delete_cookie(REFRESH_COOKIE_NAME)


def _get_refresh_token_from_request(request: Request, validated_data: dict) -> str:
    token = validated_data.get("refreshToken") or request.COOKIES.get(
        REFRESH_COOKIE_NAME
    )
    return token or ""


class LoginView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=LoginRequestSerializer,
        responses={200: LoginResponseSerializer},
        tags=["Authentication"],
    )
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

        response = success_response(
            result={
                "authenticated": result["authenticated"],
                "accessToken": result["accessToken"],
                "refreshToken": result["refreshToken"],
                "user": UserResponseSerializer(result["user"]).data,
            },
            code=1000,
            status_code=status.HTTP_200_OK,
        )
        _set_refresh_cookie(response, result["refreshToken"])
        return response


class RegisterView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Register a new account",
        description="Public endpoint for user registration.",
        request=CreateUserSerializer,
        responses={201: UserResponseSerializer},
        tags=["Authentication"],
    )
    def post(self, request: Request):
        serializer = CreateUserSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                code=1001,
                message="Invalid request data",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = create_user(
                email=serializer.validated_data["email"],
                password=serializer.validated_data["password"],
                name=serializer.validated_data["name"],
            )
        except UserServiceError as exc:
            return error_response(
                code=1005,
                message=str(exc),
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        response_serializer = UserResponseSerializer(user)
        return success_response(
            result=response_serializer.data,
            code=1000,
            status_code=status.HTTP_201_CREATED,
        )


class RefreshTokenView(APIView):
    permission_classes = [AllowAny]
    # authentication_classes = [JwtAuthentication]

    @extend_schema(
        request=RefreshRequestSerializer,
        responses={200: RefreshResponseSerializer},
        tags=["Authentication"],
    )
    def post(self, request: Request):
        serializer = RefreshRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                code=1001,
                message="Invalid request data",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        refresh_token = _get_refresh_token_from_request(
            request, serializer.validated_data
        )
        if not refresh_token:
            return error_response(
                code=1001,
                message="Refresh token is required",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = refresh(refresh_token)
        except AuthServiceError as exc:
            return error_response(
                code=1003, message=str(exc), status_code=status.HTTP_401_UNAUTHORIZED
            )

        response = success_response(
            result=result, code=1000, status_code=status.HTTP_200_OK
        )
        _set_refresh_cookie(response, result["refreshToken"])
        return response


class LogoutView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=LogoutRequestSerializer,
        responses={200: LogoutResponseSerializer},
        tags=["Authentication"],
    )
    def post(self, request: Request):
        serializer = LogoutRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                code=1001,
                message="Invalid request data",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        refresh_token = _get_refresh_token_from_request(
            request, serializer.validated_data
        )
        if not refresh_token:
            return error_response(
                code=1001,
                message="Refresh token is required",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        try:
            logout(refresh_token)
        except AuthServiceError as exc:
            return error_response(
                code=1004, message=str(exc), status_code=status.HTTP_401_UNAUTHORIZED
            )

        response = success_response(
            result={"loggedOut": True}, code=1000, status_code=status.HTTP_200_OK
        )
        _delete_refresh_cookie(response)
        return response


class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=ForgotPasswordRequestSerializer,
        responses={200: ForgotPasswordResponseSerializer},
        tags=["Authentication"],
    )
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
