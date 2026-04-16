from rest_framework import status, viewsets
from rest_framework.request import Request
from drf_spectacular.utils import OpenApiParameter, extend_schema

from core.authentication.permissions import IsAuthenticated, JwtAuthentication
from core.untils.api_response import error_response, success_response
from core.untils.pagination import PaginationHelper, PaginationQuerySerializer

from .selector import list_user_transactions
from .serializers import (
    CreateTransactionSerializer,
    TransactionListQuerySerializer,
    TransactionResponseSerializer,
    UpdateTransactionSerializer,
)
from .services import (
    TransactionServiceError,
    create_transaction,
    delete_transaction,
    get_transaction,
    update_transaction,
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
