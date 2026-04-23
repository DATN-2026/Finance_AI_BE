from datetime import date
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from drf_spectacular.utils import OpenApiParameter, extend_schema

from core.untils.api_response import error_response, success_response
from core.untils.pagination import PaginationHelper, PaginationQuerySerializer
from core.authentication.permissions import IsAuthenticated, JwtAuthentication
from apps.transactions.serializers import TransactionSummaryQuerySerializer

from .serializers import (
    BudgetOverviewResponseSerializer,
    BudgetListResponseSerializer,
    CreateBudgetSerializer,
    UpdateBudgetSerializer,
    BudgetResponseSerializer,
)
from .services import (
    BudgetServiceError,
    create_budget,
    get_budget,
    get_budget_overview,
    update_budget,
    delete_budget,
)
from .selector import list_user_budgets


class BudgetViewSet(viewsets.ViewSet):

    authentication_classes = [JwtAuthentication]
    permission_classes = [IsAuthenticated]
    lookup_url_kwarg = "budget_id"

    @extend_schema(
        summary="List user budgets",
        description="Endpoint to list budgets for the authenticated user with optional filtering by month, year, and category.",
        parameters=[
            OpenApiParameter(
                name="category_id",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filter by category UUID",
                required=False,
            ),
            OpenApiParameter(
                name="month",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Filter by month (1-12)",
                required=False,
            ),
            OpenApiParameter(
                name="year",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Filter by year",
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
            200: PaginationHelper.get_paginated_response_serializer(
                BudgetListResponseSerializer(many=True)
            )
        },
        tags=["Budgets"],
    )
    def list(self, request: Request):
        pagination_serializer = PaginationQuerySerializer(data=request.query_params)
        if not pagination_serializer.is_valid():
            return error_response(
                code=4001,
                message="Invalid pagination parameters",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        limit = pagination_serializer.validated_data["limit"]
        offset = pagination_serializer.validated_data["offset"]

        month = request.query_params.get("month")
        year = request.query_params.get("year")
        category_id = request.query_params.get("category_id")

        month = int(month) if month else None
        year = int(year) if year else None

        budgets_queryset = list_user_budgets(
            request.user, month=month, year=year, category_id=category_id
        )

        paginated_result = PaginationHelper.paginate_queryset(
            budgets_queryset, limit=limit, offset=offset
        )

        response_serializer = BudgetListResponseSerializer(
            paginated_result["items"], many=True
        )
        paginated_result["items"] = response_serializer.data

        return success_response(
            result=paginated_result, code=1000, status_code=status.HTTP_200_OK
        )

    @extend_schema(
        summary="Monthly budget overview",
        description="Return monthly total budget, total expense from transactions, remaining amount, and usage percent for the authenticated user.",
        parameters=[
            OpenApiParameter(
                name="month",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Month (1-12). Must be used together with year.",
                required=False,
            ),
            OpenApiParameter(
                name="year",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Year (e.g. 2026). Must be used together with month.",
                required=False,
            ),
        ],
        responses={200: BudgetOverviewResponseSerializer},
        tags=["Budgets"],
    )
    @action(detail=False, methods=["get"], url_path="overview")
    def overview(self, request: Request):
        query_serializer = TransactionSummaryQuerySerializer(data=request.query_params)
        if not query_serializer.is_valid():
            return error_response(
                code=4001,
                message="Invalid query parameters",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        today = date.today()
        month = query_serializer.validated_data.get("month", today.month)
        year = query_serializer.validated_data.get("year", today.year)

        overview_result = get_budget_overview(request.user, month=month, year=year)
        return success_response(
            result=overview_result,
            code=1000,
            status_code=status.HTTP_200_OK,
        )

    @extend_schema(
        summary="Create a new budget",
        description="Endpoint to create a new budget for the authenticated user.",
        request=CreateBudgetSerializer,
        responses={201: BudgetResponseSerializer},
        tags=["Budgets"],
    )
    def create(self, request: Request):
        serializer = CreateBudgetSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                code=4001,
                message="Invalid request data",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        try:
            budget = create_budget(
                user=request.user,
                category_id=str(serializer.validated_data["category_id"]),
                amount=serializer.validated_data["amount"],
                month=serializer.validated_data["month"],
                year=serializer.validated_data["year"],
            )
        except BudgetServiceError as exc:
            return error_response(
                code=4002, message=str(exc), status_code=status.HTTP_400_BAD_REQUEST
            )

        response_serializer = BudgetResponseSerializer(budget)
        return success_response(
            result=response_serializer.data,
            code=1000,
            status_code=status.HTTP_201_CREATED,
        )

    @extend_schema(
        summary="Retrieve budget details",
        description="Endpoint to retrieve details of a specific budget for the authenticated user.",
        parameters=[
            OpenApiParameter(
                name="budget_id",
                type=str,
                location=OpenApiParameter.PATH,
                description="Budget ID",
                required=True,
            ),
        ],
        responses={200: BudgetListResponseSerializer},
        tags=["Budgets"],
    )
    def retrieve(self, request: Request, budget_id: str):
        try:
            budget = get_budget(budget_id, request.user)
        except BudgetServiceError as exc:
            return error_response(
                code=4003, message=str(exc), status_code=status.HTTP_404_NOT_FOUND
            )

        response_serializer = BudgetListResponseSerializer(budget)
        return success_response(
            result=response_serializer.data, code=1000, status_code=status.HTTP_200_OK
        )

    @extend_schema(
        summary="Update budget details",
        description="Endpoint to update details of a specific budget for the authenticated user.",
        parameters=[
            OpenApiParameter(
                name="budget_id",
                type=str,
                location=OpenApiParameter.PATH,
                description="Budget ID",
                required=True,
            ),
        ],
        request=UpdateBudgetSerializer,
        responses={200: BudgetResponseSerializer},
        tags=["Budgets"],
    )
    def update(self, request: Request, budget_id: str):
        serializer = UpdateBudgetSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                code=4001,
                message="Invalid request data",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        try:
            budget = update_budget(
                budget_id=budget_id,
                user=request.user,
                amount=serializer.validated_data.get("amount"),
                month=serializer.validated_data.get("month"),
                year=serializer.validated_data.get("year"),
            )
        except BudgetServiceError as exc:
            return error_response(
                code=4004, message=str(exc), status_code=status.HTTP_400_BAD_REQUEST
            )

        response_serializer = BudgetResponseSerializer(budget)
        return success_response(
            result=response_serializer.data, code=1000, status_code=status.HTTP_200_OK
        )

    @extend_schema(
        summary="Delete a budget",
        description="Endpoint to delete a specific budget for the authenticated user.",
        parameters=[
            OpenApiParameter(
                name="budget_id",
                type=str,
                location=OpenApiParameter.PATH,
                description="Budget ID",
                required=True,
            ),
        ],
        responses={200: None},
        tags=["Budgets"],
    )
    def destroy(self, request: Request, budget_id: str):
        try:
            delete_budget(budget_id, request.user)
        except BudgetServiceError as exc:
            return error_response(
                code=4005, message=str(exc), status_code=status.HTTP_404_NOT_FOUND
            )

        return success_response(
            result={"deleted": True}, code=1000, status_code=status.HTTP_200_OK
        )
