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
    BulkUpdateStatusSerializer,
    BulkUpdateStatusResponseSerializer,
    CreateUserSerializer,
    UpdateUserSerializer,
    UserDetailResponseSerializer,
    UserListQuerySerializer,
    UserListSuccessResponseSerializer,
    UserResponseSerializer,
    UserUsageQuerySerializer,
)
from .services import (
    ERR_FORBIDDEN_ROLE_STATUS_UPDATE,
    ERR_FORBIDDEN_SELF_DEACTIVATE,
    ERR_FORBIDDEN_SELF_DEMOTE,
    ERR_USER_NOT_FOUND,
    UserServiceError,
    bulk_update_user_status,
    create_user,
    delete_user,
    get_user,
    update_user,
)
from .selector import get_user_list_stats, get_user_usage_stats, list_all_users


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
            "bulk_status": [IsAdmin],
        }
        permission_classes = permission_map.get(action_name, [IsAuthenticated])
        return [permission() for permission in permission_classes]

    @staticmethod
    def _is_admin_scope(request: Request) -> bool:
        scope = request.auth.get("scope") if request.auth else None
        return scope == "ROLE_ADMIN"

    @extend_schema(
        summary="List all users",
        description="Admin-only endpoint to list all users with optional search, filter, and sort.",
        parameters=[
            OpenApiParameter(
                name="search",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Search by email or name (case-insensitive)",
                required=False,
            ),
            OpenApiParameter(
                name="role",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filter by role: user | admin",
                required=False,
            ),
            OpenApiParameter(
                name="status",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filter by status: active | inactive",
                required=False,
            ),
            OpenApiParameter(
                name="sort_by",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Sort field: created_at | -created_at | name | -name | email | -email (default: -created_at)",
                required=False,
            ),
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
        responses={
            200: UserListSuccessResponseSerializer
        },
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

        query_serializer = UserListQuerySerializer(data=request.query_params)
        if not query_serializer.is_valid():
            return error_response(
                code=2001,
                message="Invalid query parameters",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        limit = pagination_serializer.validated_data["limit"]
        offset = pagination_serializer.validated_data["offset"]

        users_queryset = list_all_users(
            search=query_serializer.validated_data.get("search"),
            role=query_serializer.validated_data.get("role"),
            status=query_serializer.validated_data.get("status"),
            sort_by=query_serializer.validated_data.get("sort_by"),
        )

        paginated_result = PaginationHelper.paginate_queryset(
            users_queryset, limit=limit, offset=offset
        )

        response_serializer = UserResponseSerializer(
            paginated_result["items"], many=True
        )
        paginated_result["items"] = response_serializer.data
        paginated_result["stats"] = get_user_list_stats()

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
        description=(
            "Retrieve details of a specific user including usage statistics "
            "(transactions, budgets, AI requests). Accessible by admin or the user themselves."
        ),
        parameters=[
            OpenApiParameter(
                name="user_id",
                type=str,
                location=OpenApiParameter.PATH,
                description="User ID",
                required=True,
            ),
            OpenApiParameter(
                name="start_date",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filter usage from date (YYYY-MM-DD)",
                required=False,
            ),
            OpenApiParameter(
                name="end_date",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filter usage to date (YYYY-MM-DD)",
                required=False,
            ),
        ],
        responses={200: UserDetailResponseSerializer},
        tags=["Users"],
    )
    def retrieve(self, request: Request, user_id: str):
        query_serializer = UserUsageQuerySerializer(data=request.query_params)
        if not query_serializer.is_valid():
            return error_response(
                code=2001,
                message="Invalid query parameters",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        start_date = query_serializer.validated_data.get("start_date")
        end_date = query_serializer.validated_data.get("end_date")

        try:
            user = get_user(user_id)
        except UserServiceError as exc:
            return error_response(
                code=2003, message=str(exc), status_code=status.HTTP_404_NOT_FOUND
            )

        usage = get_user_usage_stats(user, start_date=start_date, end_date=end_date)
        response_data = UserDetailResponseSerializer(
            {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "role": user.role,
                "status": user.status,
                "created_at": user.created_at,
                "updated_at": user.updated_at,
                "usage": usage,
            }
        )
        return success_response(
            result=response_data.data, code=1000, status_code=status.HTTP_200_OK
        )

    @extend_schema(
        summary="Update user details",
        description=(
            "Update user details. Accessible by admin and the user themselves. "
            "Guard: cannot self-deactivate or self-demote role."
        ),
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
                requesting_user=request.user,
                can_manage_role_status=self._is_admin_scope(request),
            )
        except UserServiceError as exc:
            status_code = (
                status.HTTP_404_NOT_FOUND
                if getattr(exc, "code", "") == ERR_USER_NOT_FOUND
                else (
                    status.HTTP_403_FORBIDDEN
                    if getattr(exc, "code", "")
                    in (
                        ERR_FORBIDDEN_ROLE_STATUS_UPDATE,
                        ERR_FORBIDDEN_SELF_DEACTIVATE,
                        ERR_FORBIDDEN_SELF_DEMOTE,
                    )
                    else status.HTTP_400_BAD_REQUEST
                )
            )
            return error_response(code=2004, message=str(exc), status_code=status_code)

        response_serializer = UserResponseSerializer(user)
        return success_response(
            result=response_serializer.data, code=1000, status_code=status.HTTP_200_OK
        )

    @extend_schema(
        summary="Delete a user (Soft delete)",
        description=(
            "Admin-only. Soft-deletes a user by setting status to inactive. "
            "Guard: admin cannot delete their own account."
        ),
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
        try:
            delete_user(user_id, requesting_user=request.user)
        except UserServiceError as exc:
            status_code = (
                status.HTTP_404_NOT_FOUND
                if getattr(exc, "code", "") == ERR_USER_NOT_FOUND
                else (
                    status.HTTP_403_FORBIDDEN
                    if getattr(exc, "code", "") == ERR_FORBIDDEN_SELF_DEACTIVATE
                    else status.HTTP_400_BAD_REQUEST
                )
            )
            return error_response(code=2005, message=str(exc), status_code=status_code)

        return success_response(
            result={"deleted": True}, code=1000, status_code=status.HTTP_200_OK
        )

    @extend_schema(
        summary="Get current user details",
        description="Retrieve details (including usage stats) of the currently authenticated user.",
        parameters=[
            OpenApiParameter(
                name="start_date",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filter usage from date (YYYY-MM-DD)",
                required=False,
            ),
            OpenApiParameter(
                name="end_date",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filter usage to date (YYYY-MM-DD)",
                required=False,
            ),
        ],
        responses={200: UserDetailResponseSerializer},
        tags=["Users"],
    )
    @action(detail=False, methods=["get"], url_path="me")
    def me(self, request: Request):
        query_serializer = UserUsageQuerySerializer(data=request.query_params)
        if not query_serializer.is_valid():
            return error_response(
                code=2001,
                message="Invalid query parameters",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        start_date = query_serializer.validated_data.get("start_date")
        end_date = query_serializer.validated_data.get("end_date")

        user = request.user
        usage = get_user_usage_stats(user, start_date=start_date, end_date=end_date)
        response_data = UserDetailResponseSerializer(
            {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "role": user.role,
                "status": user.status,
                "created_at": user.created_at,
                "updated_at": user.updated_at,
                "usage": usage,
            }
        )
        return success_response(
            result=response_data.data, code=1000, status_code=status.HTTP_200_OK
        )

    @extend_schema(
        summary="Bulk update user status",
        description=(
            "Admin-only. Update the status of multiple users at once. "
            "Guard: if setting status to 'inactive', the requesting admin is automatically excluded."
        ),
        request=BulkUpdateStatusSerializer,
        responses={200: BulkUpdateStatusResponseSerializer},
        tags=["Users"],
    )
    @action(detail=False, methods=["post"], url_path="bulk-status")
    def bulk_status(self, request: Request):
        serializer = BulkUpdateStatusSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                code=2001,
                message="Invalid request data",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = bulk_update_user_status(
                user_ids=[str(uid) for uid in serializer.validated_data["user_ids"]],
                status=serializer.validated_data["status"],
                requesting_user=request.user,
            )
        except UserServiceError as exc:
            return error_response(
                code=2006, message=str(exc), status_code=status.HTTP_400_BAD_REQUEST
            )

        return success_response(
            result=result, code=1000, status_code=status.HTTP_200_OK
        )
