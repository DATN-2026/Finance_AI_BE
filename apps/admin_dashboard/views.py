from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.views import APIView

from core.authentication.permissions import IsAdmin, JwtAuthentication
from core.untils.api_response import error_response, success_response

from .selector import (
    get_admin_dashboard_overview,
    get_admin_financial_trend,
    get_admin_top_categories,
    get_admin_top_users,
    get_admin_user_growth,
)
from .serializers import (
    AdminDashboardDateRangeQuerySerializer,
    AdminDashboardFinancialTrendResponseSerializer,
    AdminDashboardLimitQuerySerializer,
    AdminDashboardOverviewResponseSerializer,
    AdminDashboardTopCategoriesResponseSerializer,
    AdminDashboardTopUsersResponseSerializer,
    AdminDashboardUserGrowthResponseSerializer,
)


DATE_RANGE_PARAMS = [
    OpenApiParameter(
        name="start_date",
        type=str,
        location=OpenApiParameter.QUERY,
        description="Optional start date in YYYY-MM-DD format. Example: 2026-05-01",
        required=False,
    ),
    OpenApiParameter(
        name="end_date",
        type=str,
        location=OpenApiParameter.QUERY,
        description="Optional end date in YYYY-MM-DD format. Example: 2026-05-31",
        required=False,
    ),
]

LIMIT_PARAM = OpenApiParameter(
    name="limit",
    type=int,
    location=OpenApiParameter.QUERY,
    description="Maximum number of items. Min 1, max 100. Default: 10",
    required=False,
)


class AdminDashboardOverviewView(APIView):
    authentication_classes = [JwtAuthentication]
    permission_classes = [IsAdmin]

    @extend_schema(
        summary="Admin Dashboard Overview",
        description=(
            "Return global admin dashboard KPIs: users, transactions, and AI "
            "request health. Date filters apply to new users, transactions, "
            "and AI requests. Transaction totals exclude soft-deleted records; "
            "deleted_transaction_count shows how many records were soft-deleted."
        ),
        parameters=DATE_RANGE_PARAMS,
        responses={200: AdminDashboardOverviewResponseSerializer},
        tags=["Admin Dashboard"],
    )
    def get(self, request: Request):
        serializer = AdminDashboardDateRangeQuerySerializer(data=request.query_params)
        if not serializer.is_valid():
            return error_response(
                code=7001,
                message="Invalid query parameters",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        result = get_admin_dashboard_overview(**serializer.validated_data)
        return success_response(result=result, code=1000, status_code=status.HTTP_200_OK)


class AdminDashboardUserGrowthView(APIView):
    authentication_classes = [JwtAuthentication]
    permission_classes = [IsAdmin]

    @extend_schema(
        summary="Admin Dashboard User Growth",
        description=(
            "Return daily new-user counts. Use start_date/end_date to limit the "
            "time range. Without filters, returns all available user creation dates."
        ),
        parameters=DATE_RANGE_PARAMS,
        responses={200: AdminDashboardUserGrowthResponseSerializer},
        tags=["Admin Dashboard"],
    )
    def get(self, request: Request):
        serializer = AdminDashboardDateRangeQuerySerializer(data=request.query_params)
        if not serializer.is_valid():
            return error_response(
                code=7001,
                message="Invalid query parameters",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        result = get_admin_user_growth(**serializer.validated_data)
        return success_response(result=result, code=1000, status_code=status.HTTP_200_OK)


class AdminDashboardFinancialTrendView(APIView):
    authentication_classes = [JwtAuthentication]
    permission_classes = [IsAdmin]

    @extend_schema(
        summary="Admin Dashboard Financial Trend",
        description=(
            "Return daily income, expenses, and active transaction counts across "
            "all users. Uses transaction_date, not created_at. Soft-deleted "
            "transactions are excluded."
        ),
        parameters=DATE_RANGE_PARAMS,
        responses={200: AdminDashboardFinancialTrendResponseSerializer},
        tags=["Admin Dashboard"],
    )
    def get(self, request: Request):
        serializer = AdminDashboardDateRangeQuerySerializer(data=request.query_params)
        if not serializer.is_valid():
            return error_response(
                code=7001,
                message="Invalid query parameters",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        result = get_admin_financial_trend(**serializer.validated_data)
        return success_response(result=result, code=1000, status_code=status.HTTP_200_OK)


class AdminDashboardTopUsersView(APIView):
    authentication_classes = [JwtAuthentication]
    permission_classes = [IsAdmin]

    @extend_schema(
        summary="Admin Dashboard Top Users",
        description=(
            "Return users with the most AI requests in the selected date range. "
            "Each item also includes that user's transaction count in the same range."
        ),
        parameters=[*DATE_RANGE_PARAMS, LIMIT_PARAM],
        responses={200: AdminDashboardTopUsersResponseSerializer},
        tags=["Admin Dashboard"],
    )
    def get(self, request: Request):
        serializer = AdminDashboardLimitQuerySerializer(data=request.query_params)
        if not serializer.is_valid():
            return error_response(
                code=7001,
                message="Invalid query parameters",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        result = get_admin_top_users(**serializer.validated_data)
        return success_response(result=result, code=1000, status_code=status.HTTP_200_OK)


class AdminDashboardTopCategoriesView(APIView):
    authentication_classes = [JwtAuthentication]
    permission_classes = [IsAdmin]

    @extend_schema(
        summary="Admin Dashboard Top Categories",
        description=(
            "Return categories with the highest transaction volume across all users "
            "in the selected date range. Uses transaction_date."
        ),
        parameters=[*DATE_RANGE_PARAMS, LIMIT_PARAM],
        responses={200: AdminDashboardTopCategoriesResponseSerializer},
        tags=["Admin Dashboard"],
    )
    def get(self, request: Request):
        serializer = AdminDashboardLimitQuerySerializer(data=request.query_params)
        if not serializer.is_valid():
            return error_response(
                code=7001,
                message="Invalid query parameters",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        result = get_admin_top_categories(**serializer.validated_data)
        return success_response(result=result, code=1000, status_code=status.HTTP_200_OK)
