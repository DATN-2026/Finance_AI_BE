from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from drf_spectacular.utils import OpenApiParameter, extend_schema

from core.untils.api_response import error_response, success_response
from core.untils.pagination import PaginationHelper, PaginationQuerySerializer
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
    update_user,
)
from .selector import list_all_users


class UserViewSet(viewsets.ViewSet):

    lookup_url_kwarg = "user_id"

    def get_authenticators(self):
        action_name = getattr(self, "action", None)
        if action_name == "create":
            return []
        return [JwtAuthentication()]

    def get_permissions(self):
        action_name = getattr(self, "action", None)
        permission_map = {
            "create": [AllowAny],
            "list": [IsAdmin],
            "retrieve": [IsAdminOrOwner],
            "update": [IsAdminOrOwner],
            "destroy": [IsAdmin],
            "me": [IsAuthenticated],
        }
        permission_classes = permission_map.get(action_name, [IsAuthenticated])
        return [permission() for permission in permission_classes]

    @extend_schema(
        summary="List all users",
        description="Admin-only endpoint to list all users .",
        parameters=[
            OpenApiParameter(
                name="limit",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Number of items per page (default: 10, max: 100)",
                required=False,
            ),
            OpenApiParameter(
                name="offset",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Starting position (default: 0)",
                required=False,
            ),
        ],
        responses={200: UserResponseSerializer(many=True)},
        tags=["Users"],
    )
    def list(self, request: Request):
        pagination_serializer = PaginationQuerySerializer(data=request.query_params)
        if not pagination_serializer.is_valid():
            return error_response(
                code=2001,
                message="Invalid pagination parameters",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        limit = pagination_serializer.validated_data["limit"]
        offset = pagination_serializer.validated_data["offset"]

        users_queryset = list_all_users()
        paginated_result = PaginationHelper.paginate_queryset(
            users_queryset, limit=limit, offset=offset
        )

        response_serializer = UserResponseSerializer(
            paginated_result["items"], many=True
        )
        paginated_result["items"] = response_serializer.data

        return success_response(
            result=paginated_result, code=1000, status_code=status.HTTP_200_OK
        )

    @extend_schema(
        summary="Create a new user",
        description="Public endpoint to create a new user. Role and status are set by the system.",
        request=CreateUserSerializer,
        responses={201: UserResponseSerializer},
        tags=["Users"],
    )
    def create(self, request: Request):
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

    @extend_schema(
        summary="Retrieve user details",
        description="Endpoint to retrieve details of a specific user. Accessible by admin and the user themselves.",
        parameters=[
            OpenApiParameter(
                name="user_id",
                type=str,
                location=OpenApiParameter.PATH,
                description="User ID",
                required=True,
            ),
        ],
        responses={200: UserResponseSerializer},
        tags=["Users"],
    )
    def retrieve(self, request: Request, user_id: str):
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

    @extend_schema(
        summary="Update user details",
        description="Endpoint to update user details. Accessible by admin and the user themselves.",
        parameters=[
            OpenApiParameter(
                name="user_id",
                type=str,
                location=OpenApiParameter.PATH,
                description="User ID",
                required=True,
            ),
        ],
        request=UpdateUserSerializer,
        responses={200: UserResponseSerializer},
        tags=["Users"],
    )
    def update(self, request: Request, user_id: str):
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

    @extend_schema(
        summary="Delete a user (Soft delete)",
        description="The endpoint is for admin to delete user by their ID.",
        parameters=[
            OpenApiParameter(
                name="user_id",
                type=str,
                location=OpenApiParameter.PATH,
                description="User ID",
                required=True,
            ),
        ],
        responses={200: None},
        tags=["Users"],
    )
    def destroy(self, request: Request, user_id: str):
        if not hasattr(request.user, "role") or request.user.role != "admin":
            return error_response(
                code=2006,
                message="Only admins can delete users",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        try:
            delete_user(user_id)
        except UserServiceError as exc:
            return error_response(
                code=2005, message=str(exc), status_code=status.HTTP_404_NOT_FOUND
            )

        return success_response(
            result={"deleted": True}, code=1000, status_code=status.HTTP_200_OK
        )

    @extend_schema(
        summary="Get current user details",
        description="Endpoint to retrieve details of the currently authenticated user.",
        responses={200: UserResponseSerializer},
        tags=["Users"],
    )
    @action(detail=False, methods=["get"], url_path="me")
    def me(self, request: Request):
        response_serializer = UserResponseSerializer(request.user)
        return success_response(
            result=response_serializer.data, code=1000, status_code=status.HTTP_200_OK
        )
