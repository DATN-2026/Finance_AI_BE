from datetime import date

from rest_framework import status, viewsets
from rest_framework.request import Request
from rest_framework.views import APIView
from drf_spectacular.utils import OpenApiParameter, extend_schema

from core.authentication.permissions import IsAuthenticated, JwtAuthentication
from core.untils.api_response import error_response, success_response
from core.untils.pagination import PaginationHelper, PaginationQuerySerializer

from .selector import list_user_transactions
from .serializers import (
    BalanceResponseSerializer,
    CashflowResponseSerializer,
    CreateTransactionSerializer,
    RecentTransactionsQuerySerializer,
    RecentTransactionsResponseSerializer,
    SpendingByCategoryResponseSerializer,
    TransactionSummaryQuerySerializer,
    TransactionSummaryResponseSerializer,
    TransactionListQuerySerializer,
    TransactionResponseSerializer,
    UpdateTransactionSerializer,
)
from .services import (
    TransactionServiceError,
    get_balance_period_summary,
    get_cashflow_period_summary,
    get_recent_transactions,
    get_spending_by_category_summary,
    create_transaction,
    delete_transaction,
    get_dashboard_summary,
    get_transaction,
    update_transaction,
)


def _get_month_year_from_validated_data(
    validated_data: dict[str, object],
) -> tuple[int, int]:
    today = date.today()
    month = validated_data.get("month", today.month)
    year = validated_data.get("year", today.year)
    return int(month), int(year)


class DashboardSummaryView(APIView):
    authentication_classes = [JwtAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Dashboard Summary",
        description="Get income, expenses, and balance for a month/year with comparison to the previous month.",
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
        responses={200: TransactionSummaryResponseSerializer},
        tags=["Dashboard"],
    )
    def get(self, request: Request):
        query_serializer = TransactionSummaryQuerySerializer(data=request.query_params)
        if not query_serializer.is_valid():
            return error_response(
                code=5001,
                message="Invalid query parameters",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        today = date.today()
        month = query_serializer.validated_data.get("month", today.month)
        year = query_serializer.validated_data.get("year", today.year)

        summary_result = get_dashboard_summary(request.user, month=month, year=year)

        return success_response(
            result=summary_result, code=1000, status_code=status.HTTP_200_OK
        )


class CashflowView(APIView):
    authentication_classes = [JwtAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Cashflow 12 Periods",
        description="Get total income and expenses for 12 monthly periods ending at the provided month/year.",
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
        responses={200: CashflowResponseSerializer},
        tags=["Dashboard"],
    )
    def get(self, request: Request):
        query_serializer = TransactionSummaryQuerySerializer(data=request.query_params)
        if not query_serializer.is_valid():
            return error_response(
                code=5001,
                message="Invalid query parameters",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        month, year = _get_month_year_from_validated_data(
            query_serializer.validated_data
        )
        result = get_cashflow_period_summary(request.user, month=month, year=year)

        return success_response(
            result=result, code=1000, status_code=status.HTTP_200_OK
        )


class SpendingByCategoryView(APIView):
    authentication_classes = [JwtAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Spending By Category",
        description="Get total expense amount grouped by category in the provided month/year.",
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
        responses={200: SpendingByCategoryResponseSerializer},
        tags=["Dashboard"],
    )
    def get(self, request: Request):
        query_serializer = TransactionSummaryQuerySerializer(data=request.query_params)
        if not query_serializer.is_valid():
            return error_response(
                code=5001,
                message="Invalid query parameters",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        month, year = _get_month_year_from_validated_data(
            query_serializer.validated_data
        )

        spending_by_category = get_spending_by_category_summary(
            request.user,
            month=month,
            year=year,
        )

        return success_response(
            result=spending_by_category,
            code=1000,
            status_code=status.HTTP_200_OK,
        )


class RecentTransactionsView(APIView):
    authentication_classes = [JwtAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Recent Transactions",
        description="Get recent transactions in the provided month/year.",
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
            OpenApiParameter(
                name="limit",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Maximum number of transactions to return (default: 5).",
                required=False,
            ),
        ],
        responses={200: RecentTransactionsResponseSerializer},
        tags=["Dashboard"],
    )
    def get(self, request: Request):
        query_serializer = RecentTransactionsQuerySerializer(data=request.query_params)
        if not query_serializer.is_valid():
            return error_response(
                code=5001,
                message="Invalid query parameters",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        month, year = _get_month_year_from_validated_data(
            query_serializer.validated_data
        )
        limit = query_serializer.validated_data["limit"]

        recent_transactions = get_recent_transactions(
            request.user,
            month=month,
            year=year,
            limit=limit,
        )

        response_serializer = TransactionResponseSerializer(
            recent_transactions,
            many=True,
        )
        return success_response(
            result=response_serializer.data,
            code=1000,
            status_code=status.HTTP_200_OK,
        )


class BalanceView(APIView):
    authentication_classes = [JwtAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Balance 12 Periods",
        description="Get total balance for 12 monthly periods ending at the provided month/year.",
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
        responses={200: BalanceResponseSerializer},
        tags=["Dashboard"],
    )
    def get(self, request: Request):
        query_serializer = TransactionSummaryQuerySerializer(data=request.query_params)
        if not query_serializer.is_valid():
            return error_response(
                code=5001,
                message="Invalid query parameters",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        month, year = _get_month_year_from_validated_data(
            query_serializer.validated_data
        )
        result = get_balance_period_summary(request.user, month=month, year=year)

        return success_response(
            result=result, code=1000, status_code=status.HTTP_200_OK
        )


class TransactionViewSet(viewsets.ViewSet):

    authentication_classes = [JwtAuthentication]
    permission_classes = [IsAuthenticated]
    lookup_url_kwarg = "transaction_id"

    @extend_schema(
        summary="List Transactions",
        description="Retrieve a list of transactions for the authenticated user with optional filters and pagination.",
        parameters=[
            OpenApiParameter(
                name="category_id",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filter by category UUID",
                required=False,
            ),
            OpenApiParameter(
                name="type",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filter by type: income or expense",
                required=False,
            ),
            OpenApiParameter(
                name="start_date",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filter from date (YYYY-MM-DD)",
                required=False,
            ),
            OpenApiParameter(
                name="end_date",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filter to date (YYYY-MM-DD)",
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
                TransactionResponseSerializer(many=True)
            )
        },
        tags=["Transactions"],
    )
    def list(self, request: Request):
        pagination_serializer = PaginationQuerySerializer(data=request.query_params)
        if not pagination_serializer.is_valid():
            return error_response(
                code=5001,
                message="Invalid pagination parameters",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        query_serializer = TransactionListQuerySerializer(data=request.query_params)
        if not query_serializer.is_valid():
            return error_response(
                code=5001,
                message="Invalid query parameters",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        limit = pagination_serializer.validated_data["limit"]
        offset = pagination_serializer.validated_data["offset"]

        transactions_queryset = list_user_transactions(
            request.user,
            type=query_serializer.validated_data.get("type"),
            category_id=query_serializer.validated_data.get("category_id"),
            start_date=query_serializer.validated_data.get("start_date"),
            end_date=query_serializer.validated_data.get("end_date"),
        )

        paginated_result = PaginationHelper.paginate_queryset(
            transactions_queryset, limit=limit, offset=offset
        )

        response_serializer = TransactionResponseSerializer(
            paginated_result["items"], many=True
        )
        paginated_result["items"] = response_serializer.data

        return success_response(
            result=paginated_result, code=1000, status_code=status.HTTP_200_OK
        )

    @extend_schema(
        summary="Create Transaction",
        description="Create a new transaction for the authenticated user. The transaction type is inferred from the request data.",
        request=CreateTransactionSerializer,
        responses={201: TransactionResponseSerializer},
        tags=["Transactions"],
    )
    def create(self, request: Request):
        serializer = CreateTransactionSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                code=5001,
                message="Invalid request data",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        try:
            transaction = create_transaction(
                user=request.user,
                category_id=str(serializer.validated_data["category_id"]),
                amount=serializer.validated_data["amount"],
                note=serializer.validated_data.get("note"),
                transaction_date=serializer.validated_data["transaction_date"],
            )
        except TransactionServiceError as exc:
            return error_response(
                code=5002, message=str(exc), status_code=status.HTTP_400_BAD_REQUEST
            )

        response_serializer = TransactionResponseSerializer(transaction)
        return success_response(
            result=response_serializer.data,
            code=1000,
            status_code=status.HTTP_201_CREATED,
        )

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="transaction_id",
                type=str,
                location=OpenApiParameter.PATH,
                description="Transaction ID",
                required=True,
            ),
        ],
        responses={200: TransactionResponseSerializer},
        tags=["Transactions"],
    )
    def retrieve(self, request: Request, transaction_id: str = None):
        try:
            transaction = get_transaction(transaction_id, request.user)
        except TransactionServiceError as exc:
            return error_response(
                code=5003, message=str(exc), status_code=status.HTTP_404_NOT_FOUND
            )

        response_serializer = TransactionResponseSerializer(transaction)
        return success_response(
            result=response_serializer.data, code=1000, status_code=status.HTTP_200_OK
        )

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="transaction_id",
                type=str,
                location=OpenApiParameter.PATH,
                description="Transaction ID",
                required=True,
            ),
        ],
        request=UpdateTransactionSerializer,
        responses={200: TransactionResponseSerializer},
        tags=["Transactions"],
    )
    def update(self, request: Request, transaction_id: str = None):
        serializer = UpdateTransactionSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                code=5001,
                message="Invalid request data",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # dữ liệu sạch để dùng
        data = serializer.validated_data

        # Clean transform
        category_id = data.get("category_id")
        if category_id:
            category_id = str(category_id)

        try:
            transaction = update_transaction(
                transaction_id=transaction_id,
                user=request.user,
                category_id=category_id,
                amount=data.get("amount"),
                note=data.get("note"),
                transaction_date=data.get("transaction_date"),
            )
        except TransactionServiceError as exc:
            return error_response(
                code=5004, message=str(exc), status_code=status.HTTP_400_BAD_REQUEST
            )

        response_serializer = TransactionResponseSerializer(transaction)
        return success_response(
            result=response_serializer.data, code=1000, status_code=status.HTTP_200_OK
        )

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="transaction_id",
                type=str,
                location=OpenApiParameter.PATH,
                description="Transaction ID",
                required=True,
            ),
        ],
        responses={200: None},
        tags=["Transactions"],
    )
    def destroy(self, request: Request, transaction_id: str = None):
        try:
            delete_transaction(transaction_id, request.user)
        except TransactionServiceError as exc:
            return error_response(
                code=5005, message=str(exc), status_code=status.HTTP_404_NOT_FOUND
            )

        return success_response(
            result={"deleted": True}, code=1000, status_code=status.HTTP_200_OK
        )
