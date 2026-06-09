from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.views import APIView

from core.authentication.permissions import IsAdmin, JwtAuthentication
from core.untils.api_response import error_response, success_response
from core.untils.pagination import PaginationHelper, PaginationQuerySerializer

from .admin_serializers import (
    AdminUserCategoryListQuerySerializer,
    AdminUserCategoryResponseSerializer,
    CreateDefaultCategorySerializer,
    DefaultCategoryListQuerySerializer,
    DefaultCategoryResponseSerializer,
    DefaultCategorySuccessResponseSerializer,
    SyncDefaultCategoriesSerializer,
    SyncDefaultCategoriesSuccessResponseSerializer,
    UpdateDefaultCategorySerializer,
)
from .selector import list_admin_user_categories, list_default_categories
from .services import (
    ERR_DEFAULT_CATEGORY_EXISTS,
    ERR_DEFAULT_CATEGORY_NOT_FOUND,
    ERR_USER_NOT_FOUND,
    CategoryServiceError,
    create_default_category,
    get_default_category,
    sync_default_categories,
    update_default_category,
)

PAGINATION_PARAMS = [
    OpenApiParameter(
        name="limit",
        type=int,
        location=OpenApiParameter.QUERY,
        description="Number of items per page. Min: 1, max: 100, default: 10.",
        required=False,
    ),
    OpenApiParameter(
        name="offset",
        type=int,
        location=OpenApiParameter.QUERY,
        description="Starting item index. Min: 0, default: 0.",
        required=False,
    ),
]

TYPE_PARAM = OpenApiParameter(
    name="type",
    type=str,
    location=OpenApiParameter.QUERY,
    description="Filter by category type. Options: income, expense.",
    required=False,
)

IS_ACTIVE_PARAM = OpenApiParameter(
    name="is_active",
    type=bool,
    location=OpenApiParameter.QUERY,
    description="Filter by active status. Options: true, false.",
    required=False,
)

SEARCH_PARAM = OpenApiParameter(
    name="search",
    type=str,
    location=OpenApiParameter.QUERY,
    description="Search by category name. Example: Food.",
    required=False,
)


def _category_error_status(exc: CategoryServiceError):
    if exc.code in (ERR_DEFAULT_CATEGORY_NOT_FOUND, ERR_USER_NOT_FOUND):
        return status.HTTP_404_NOT_FOUND
    if exc.code == ERR_DEFAULT_CATEGORY_EXISTS:
        return status.HTTP_400_BAD_REQUEST
    return status.HTTP_400_BAD_REQUEST


class AdminDefaultCategoryListCreateView(APIView):
    authentication_classes = [JwtAuthentication]
    permission_classes = [IsAdmin]

    @extend_schema(
        summary="List default categories",
        operation_id="admin_default_category_list",
        description=(
            "Admin-only. Return default/global categories used as templates for "
            "new users. These records are not used directly by transactions."
        ),
        parameters=[
            TYPE_PARAM,
            IS_ACTIVE_PARAM,
            SEARCH_PARAM,
            *PAGINATION_PARAMS,
        ],
        responses={
            200: PaginationHelper.get_paginated_response_serializer(
                DefaultCategoryResponseSerializer
            )
        },
        tags=["Admin Category Management"],
    )
    def get(self, request: Request):
        pagination_serializer = PaginationQuerySerializer(data=request.query_params)
        if not pagination_serializer.is_valid():
            return error_response(
                code=3101,
                message="Invalid pagination parameters",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        query_serializer = DefaultCategoryListQuerySerializer(data=request.query_params)
        if not query_serializer.is_valid():
            return error_response(
                code=3101,
                message="Invalid query parameters",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        queryset = list_default_categories(**query_serializer.validated_data)
        paginated_result = PaginationHelper.paginate_queryset(
            queryset,
            limit=pagination_serializer.validated_data["limit"],
            offset=pagination_serializer.validated_data["offset"],
        )
        paginated_result["items"] = DefaultCategoryResponseSerializer(
            paginated_result["items"],
            many=True,
        ).data

        return success_response(
            result=paginated_result,
            code=1000,
            status_code=status.HTTP_200_OK,
        )

    @extend_schema(
        summary="Create default category",
        description=(
            "Admin-only. Create a default/global category. New users created "
            "after this will receive a copied user category from active defaults. "
            "Existing users are not updated automatically; use the sync endpoint."
        ),
        request=CreateDefaultCategorySerializer,
        responses={201: DefaultCategorySuccessResponseSerializer},
        tags=["Admin Category Management"],
    )
    def post(self, request: Request):
        serializer = CreateDefaultCategorySerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                code=3101,
                message="Invalid request data",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        try:
            default_category = create_default_category(**serializer.validated_data)
        except CategoryServiceError as exc:
            return error_response(
                code=3102,
                message=str(exc),
                status_code=_category_error_status(exc),
            )

        return success_response(
            result=DefaultCategoryResponseSerializer(default_category).data,
            code=1000,
            status_code=status.HTTP_201_CREATED,
        )


class AdminDefaultCategoryDetailView(APIView):
    authentication_classes = [JwtAuthentication]
    permission_classes = [IsAdmin]

    @extend_schema(
        summary="Get default category detail",
        operation_id="admin_default_category_detail",
        description="Admin-only. Return one default/global category by ID.",
        parameters=[
            OpenApiParameter(
                name="default_category_id",
                type=str,
                location=OpenApiParameter.PATH,
                description="Default category UUID.",
                required=True,
            ),
        ],
        responses={200: DefaultCategorySuccessResponseSerializer},
        tags=["Admin Category Management"],
    )
    def get(self, request: Request, default_category_id: str):
        try:
            default_category = get_default_category(default_category_id)
        except CategoryServiceError as exc:
            return error_response(
                code=3103,
                message=str(exc),
                status_code=_category_error_status(exc),
            )

        return success_response(
            result=DefaultCategoryResponseSerializer(default_category).data,
            code=1000,
            status_code=status.HTTP_200_OK,
        )

    @extend_schema(
        summary="Update default category",
        description=(
            "Admin-only. Update a default/global category. This does not modify "
            "categories already copied to existing users."
        ),
        parameters=[
            OpenApiParameter(
                name="default_category_id",
                type=str,
                location=OpenApiParameter.PATH,
                description="Default category UUID.",
                required=True,
            ),
        ],
        request=UpdateDefaultCategorySerializer,
        responses={200: DefaultCategorySuccessResponseSerializer},
        tags=["Admin Category Management"],
    )
    def patch(self, request: Request, default_category_id: str):
        serializer = UpdateDefaultCategorySerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                code=3101,
                message="Invalid request data",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        try:
            default_category = update_default_category(
                default_category_id=default_category_id,
                **serializer.validated_data,
            )
        except CategoryServiceError as exc:
            return error_response(
                code=3104,
                message=str(exc),
                status_code=_category_error_status(exc),
            )

        return success_response(
            result=DefaultCategoryResponseSerializer(default_category).data,
            code=1000,
            status_code=status.HTTP_200_OK,
        )


class AdminUserCategoryListView(APIView):
    authentication_classes = [JwtAuthentication]
    permission_classes = [IsAdmin]

    @extend_schema(
        summary="List user categories for admin",
        description=(
            "Admin-only. Return user-owned categories for monitoring/support. "
            "These are the actual categories used by transactions and budgets."
        ),
        parameters=[
            OpenApiParameter(
                name="user_id",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filter by user UUID. Example: ff8fbf43-92ee-464f-8357-f96e6cc19d08.",
                required=False,
            ),
            TYPE_PARAM,
            IS_ACTIVE_PARAM,
            SEARCH_PARAM,
            *PAGINATION_PARAMS,
        ],
        responses={
            200: PaginationHelper.get_paginated_response_serializer(
                AdminUserCategoryResponseSerializer
            )
        },
        tags=["Admin Category Management"],
    )
    def get(self, request: Request):
        pagination_serializer = PaginationQuerySerializer(data=request.query_params)
        if not pagination_serializer.is_valid():
            return error_response(
                code=3101,
                message="Invalid pagination parameters",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        query_serializer = AdminUserCategoryListQuerySerializer(
            data=request.query_params
        )
        if not query_serializer.is_valid():
            return error_response(
                code=3101,
                message="Invalid query parameters",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        queryset = list_admin_user_categories(**query_serializer.validated_data)
        paginated_result = PaginationHelper.paginate_queryset(
            queryset,
            limit=pagination_serializer.validated_data["limit"],
            offset=pagination_serializer.validated_data["offset"],
        )
        paginated_result["items"] = AdminUserCategoryResponseSerializer(
            paginated_result["items"],
            many=True,
        ).data

        return success_response(
            result=paginated_result,
            code=1000,
            status_code=status.HTTP_200_OK,
        )


class AdminDefaultCategorySyncView(APIView):
    authentication_classes = [JwtAuthentication]
    permission_classes = [IsAdmin]

    @extend_schema(
        summary="Sync default categories to users",
        description=(
            "Admin-only. Copy active default/global categories to user-owned "
            "categories. Use scope=single_user with user_id for one user, or "
            "scope=all_users for all active users. Optional default_category_id "
            "syncs only one default category."
        ),
        request=SyncDefaultCategoriesSerializer,
        responses={200: SyncDefaultCategoriesSuccessResponseSerializer},
        tags=["Admin Category Management"],
    )
    def post(self, request: Request):
        serializer = SyncDefaultCategoriesSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                code=3101,
                message="Invalid request data",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = sync_default_categories(**serializer.validated_data)
        except CategoryServiceError as exc:
            return error_response(
                code=3105,
                message=str(exc),
                status_code=_category_error_status(exc),
            )

        return success_response(
            result=result,
            code=1000,
            status_code=status.HTTP_200_OK,
        )
