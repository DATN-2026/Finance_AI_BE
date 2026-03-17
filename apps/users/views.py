from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from core.untils.api_response import error_response, success_response
from core.authentication.permissions import (
    IsAuthenticated,
    IsAdmin,
    IsAdminOrOwner,
    JwtAuthentication,
)

from .serializers import (
    CreateUserSerializer,
    UpdateUserSerializer,
    UserResponseSerializer,
)
from .services import (
    UserServiceError,
    create_user,
    delete_user,
    get_user,
    list_users,
    update_user,
)


class CreateUserView(APIView):
    """
    Public endpoint to create a new user.
    role and status are set by the system (defaults from model).
    """

    permission_classes = [AllowAny]

    @extend_schema(
        request=CreateUserSerializer,
        responses={201: UserResponseSerializer},
        tags=["Users"],
    )
    def post(self, request: Request):
        serializer = CreateUserSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                code=2001,
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
                code=2002, message=str(exc), status_code=status.HTTP_400_BAD_REQUEST
            )

        response_serializer = UserResponseSerializer(user)
        return success_response(
            result=response_serializer.data,
            code=1000,
            status_code=status.HTTP_201_CREATED,
        )


class GetUserView(APIView):
    """
    Protected endpoint to get a user by ID.
    Requires JWT authentication.
    Admin can view any user, regular users can only view their own profile.
    """

    authentication_classes = [JwtAuthentication]
    permission_classes = [IsAdminOrOwner]

    @extend_schema(
        responses={200: UserResponseSerializer},
        tags=["Users"],
    )
    def get(self, request: Request, user_id: str):
        try:
            user = get_user(user_id)
        except UserServiceError as exc:
            return error_response(
                code=2003, message=str(exc), status_code=status.HTTP_404_NOT_FOUND
            )

        response_serializer = UserResponseSerializer(user)
        return success_response(
            result=response_serializer.data, code=1000, status_code=status.HTTP_200_OK
        )


class GetCurrentUserView(APIView):
    """
    Protected endpoint to get the current authenticated user's profile.
    Requires JWT authentication.
    """

    authentication_classes = [JwtAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: UserResponseSerializer},
        tags=["Users"],
    )
    def get(self, request: Request):
        response_serializer = UserResponseSerializer(request.user)
        return success_response(
            result=response_serializer.data, code=1000, status_code=status.HTTP_200_OK
        )


class UpdateUserView(APIView):
    """
    Protected endpoint to update a user.
    Requires JWT authentication.
    Admin can update any user, regular users can only update their own profile.
    """

    authentication_classes = [JwtAuthentication]
    permission_classes = [IsAdminOrOwner]

    @extend_schema(
        request=UpdateUserSerializer,
        responses={200: UserResponseSerializer},
        tags=["Users"],
    )
    def put(self, request: Request, user_id: str):
        serializer = UpdateUserSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                code=2001,
                message="Invalid request data",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = update_user(
                user_id=user_id,
                email=serializer.validated_data.get("email"),
                password=serializer.validated_data.get("password"),
                name=serializer.validated_data.get("name"),
                role=serializer.validated_data.get("role"),
                status=serializer.validated_data.get("status"),
            )
        except UserServiceError as exc:
            return error_response(
                code=2004, message=str(exc), status_code=status.HTTP_400_BAD_REQUEST
            )

        response_serializer = UserResponseSerializer(user)
        return success_response(
            result=response_serializer.data, code=1000, status_code=status.HTTP_200_OK
        )


class DeleteUserView(APIView):

    authentication_classes = [JwtAuthentication]
    permission_classes = [IsAdmin]

    @extend_schema(
        responses={200: None},
        tags=["Users"],
    )
    def delete(self, request: Request, user_id: str):
        try:
            delete_user(user_id)
        except UserServiceError as exc:
            return error_response(
                code=2005, message=str(exc), status_code=status.HTTP_404_NOT_FOUND
            )

        return success_response(
            result={"deleted": True}, code=1000, status_code=status.HTTP_200_OK
        )


class ListUsersView(APIView):
    """
    Protected endpoint to list all users.
    Requires JWT authentication and admin role.
    Only admins can view the list of all users.
    """

    authentication_classes = [JwtAuthentication]
    permission_classes = [IsAdmin]

    @extend_schema(
        responses={200: UserResponseSerializer(many=True)},
        tags=["Users"],
    )
    def get(self, request: Request):
        users = list_users()
        response_serializer = UserResponseSerializer(users, many=True)
        return success_response(
            result=response_serializer.data, code=1000, status_code=status.HTTP_200_OK
        )
