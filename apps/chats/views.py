from drf_spectacular.utils import OpenApiParameter, extend_schema
from datetime import datetime, time
from rest_framework import status
from rest_framework.request import Request
from rest_framework.views import APIView

from core.authentication.permissions import IsAuthenticated, JwtAuthentication
from core.authentication.permissions import IsAdmin
from core.untils.api_response import error_response, success_response
from core.untils.pagination import PaginationHelper, PaginationQuerySerializer

from apps.transactions.serializers import TransactionResponseSerializer
from apps.transactions.services import TransactionServiceError

from .serializers import (
    AdminAIErrorItemSerializer,
    AdminAIOverviewResponseSerializer,
    AdminAIRequestDeleteResponseSerializer,
    AdminAIRequestDetailResponseSerializer,
    AdminAIRequestListItemSerializer,
    AdminAIRequestQuerySerializer,
    ChatDeleteHistoryResponseSerializer,
    ChatMessageSerializer,
    ChatParseCommitResponseSerializer,
    ChatParseLLMResponseSerializer,
    ChatParseRequestSerializer,
    ChatParseResponseSerializer,
)
from .services import (
    ChatServiceError,
    _build_response_message_llm,
    commit_parse_result,
    parse_message,
    parse_message_for_commit,
)
from .selector import delete_user_chat_messages, list_user_chat_messages
from .selector import (
    build_error_groups,
    build_overview_metrics,
    find_related_user_message_content,
    list_admin_ai_requests,
    mark_admin_ai_request_deleted,
    map_related_user_message_contents,
)


def _order_parse_result(parse_result: dict) -> dict:
    if not isinstance(parse_result, dict):
        return parse_result

    ordered = {}
    preferred_keys = (
        "intent",
        "subject_scope",
        "sql",
        "query_result",
        "query_error",
        "actions",
        "rejected_actions",
        "reason",
    )

    for key in preferred_keys:
        if key in parse_result:
            ordered[key] = parse_result[key]

    for key, value in parse_result.items():
        if key not in ordered:
            ordered[key] = value

    return ordered


def _format_admin_metadata(metadata: dict) -> dict:
    if not isinstance(metadata, dict):
        return metadata

    formatted = dict(metadata)
    if "parse_result" in formatted:
        formatted["parse_result"] = _order_parse_result(formatted["parse_result"])

    return formatted


class ChatParseView(APIView):
    authentication_classes = [JwtAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Parse Chat Message",
        description="Parse a Vietnamese or English chat message into intents and transaction actions using Gemini.",
        request=ChatParseRequestSerializer,
        responses={200: ChatParseResponseSerializer},
        tags=["Chats"],
    )
    def post(self, request: Request):
        serializer = ChatParseRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                code=5001,
                message="Invalid request data",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = parse_message(
                user=request.user,
                message=serializer.validated_data["message"],
            )
        except ChatServiceError as exc:
            return error_response(
                code=5002,
                message=str(exc),
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        return success_response(
            result=result,
            code=1000,
            status_code=status.HTTP_200_OK,
        )


class ChatParseCommitView(APIView):
    authentication_classes = [JwtAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Parse and Create Transactions",
        description="Parse a chat message then create transactions for valid actions.",
        request=ChatParseRequestSerializer,
        responses={200: ChatParseCommitResponseSerializer},
        tags=["Chats"],
    )
    def post(self, request: Request):
        import time
        from datetime import datetime

        overall_start_time = time.time()
        overall_started_at = datetime.now().isoformat()

        serializer = ChatParseRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                code=5001,
                message="Invalid request data",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        try:
            parse_result, raw_llm_output, model_name, intent_step_info = (
                parse_message_for_commit(
                    user=request.user,
                    message=serializer.validated_data["message"],
                )
            )
        except ChatServiceError as exc:
            return error_response(
                code=5002,
                message=str(exc),
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        try:
            response_message, created_transactions = commit_parse_result(
                user=request.user,
                user_message=serializer.validated_data["message"],
                parse_result=parse_result,
                raw_llm_output=raw_llm_output,
                model_name=model_name,
                intent_step_info=intent_step_info,
                overall_start_time=overall_start_time,
                overall_started_at=overall_started_at,
            )
        except TransactionServiceError as exc:
            return error_response(
                code=5003,
                message=str(exc),
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        response_serializer = TransactionResponseSerializer(
            created_transactions, many=True
        )
        result = {
            "message": response_message,
            "created_transactions": response_serializer.data,
        }
        if "query_result" in parse_result:
            result["query_result"] = parse_result["query_result"]

        return success_response(
            result=result,
            code=1000,
            status_code=status.HTTP_200_OK,
        )


class ChatParseLLMResponseView(APIView):
    authentication_classes = [JwtAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Parse and Build LLM Response",
        description=(
            "Parse a chat message and generate a user response with a separate LLM prompt."
        ),
        request=ChatParseRequestSerializer,
        responses={200: ChatParseLLMResponseSerializer},
        tags=["Chats"],
    )
    def post(self, request: Request):
        serializer = ChatParseRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                code=5001,
                message="Invalid request data",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        try:
            parse_result = parse_message(
                user=request.user,
                message=serializer.validated_data["message"],
            )
            response_message = _build_response_message_llm(parse_result)
        except ChatServiceError as exc:
            return error_response(
                code=5002,
                message=str(exc),
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        return success_response(
            result={"message": response_message},
            code=1000,
            status_code=status.HTTP_200_OK,
        )


class ChatHistoryView(APIView):
    authentication_classes = [JwtAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Chat History",
        description="Get chat history for the authenticated user.",
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
        responses={
            200: PaginationHelper.get_paginated_response_serializer(
                ChatMessageSerializer(many=True)
            )
        },
        tags=["Chats"],
    )
    def get(self, request: Request):
        pagination_serializer = PaginationQuerySerializer(data=request.query_params)
        if not pagination_serializer.is_valid():
            return error_response(
                code=5001,
                message="Invalid pagination parameters",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        limit = pagination_serializer.validated_data["limit"]
        offset = pagination_serializer.validated_data["offset"]

        messages_queryset = list_user_chat_messages(request.user)
        paginated_result = PaginationHelper.paginate_queryset(
            messages_queryset, limit=limit, offset=offset
        )

        response_serializer = ChatMessageSerializer(
            paginated_result["items"], many=True
        )
        paginated_result["items"] = response_serializer.data

        return success_response(
            result=paginated_result, code=1000, status_code=status.HTTP_200_OK
        )


class ChatHistoryClearView(APIView):
    authentication_classes = [JwtAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Delete Chat History",
        description=(
            "Hide chat history for the authenticated user. This is a soft delete "
            "for the user view; admin monitoring data remains available."
        ),
        responses={200: ChatDeleteHistoryResponseSerializer},
        tags=["Chats"],
    )
    def delete(self, request: Request):
        deleted_count = delete_user_chat_messages(request.user)
        return success_response(
            result={
                "message": "Chat history cleared successfully.",
                "deleted": deleted_count,
            },
            code=1000,
            status_code=status.HTTP_200_OK,
        )


class AdminAIMonitorOverviewView(APIView):
    authentication_classes = [JwtAuthentication]
    permission_classes = [IsAdmin]

    @extend_schema(
        summary="Admin AI Monitor Overview",
        parameters=[
            OpenApiParameter(
                name="user_id",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filter by user UUID. ",
            ),
            OpenApiParameter(
                name="status",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filter by status. Options: success, failed, partial",
            ),
            OpenApiParameter(
                name="intent",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filter by intent. Options: transaction_batch, financial_question, greeting, unknown",
            ),
            OpenApiParameter(
                name="model",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filter by model name. Example: gemini-2.5-flash",
            ),
            OpenApiParameter(
                name="start_date",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Start date in YYYY-MM-DD format. Example: 2026-05-01",
            ),
            OpenApiParameter(
                name="end_date",
                type=str,
                location=OpenApiParameter.QUERY,
                description="End date in YYYY-MM-DD format. Example: 2026-05-31",
            ),
        ],
        responses={200: AdminAIOverviewResponseSerializer},
        tags=["Chats Admin"],
    )
    def get(self, request: Request):
        query_serializer = AdminAIRequestQuerySerializer(data=request.query_params)
        if not query_serializer.is_valid():
            return error_response(
                5001, "Invalid query parameters", status.HTTP_400_BAD_REQUEST
            )

        filters = dict(query_serializer.validated_data)
        start_date = filters.pop("start_date", None)
        end_date = filters.pop("end_date", None)
        if start_date:
            filters["start_at"] = datetime.combine(start_date, time.min)
        if end_date:
            filters["end_at"] = datetime.combine(end_date, time.max)

        qs = list_admin_ai_requests(**filters)
        result = build_overview_metrics(qs)
        return success_response(
            result=result, code=1000, status_code=status.HTTP_200_OK
        )


class AdminAIRequestListView(APIView):
    authentication_classes = [JwtAuthentication]
    permission_classes = [IsAdmin]

    @extend_schema(
        summary="Admin AI Request List",
        operation_id="admin_ai_monitor_request_list",
        parameters=[
            OpenApiParameter(
                name="user_id",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filter by user UUID. ",
            ),
            OpenApiParameter(
                name="status",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filter by status. Options: success, failed, partial",
            ),
            OpenApiParameter(
                name="intent",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filter by intent. Options: transaction_batch, financial_question, greeting, unknown",
            ),
            OpenApiParameter(
                name="model",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filter by model name. Example: gemini-2.5-flash",
            ),
            OpenApiParameter(
                name="start_date",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Start date in YYYY-MM-DD format. Example: 2026-05-01",
            ),
            OpenApiParameter(
                name="end_date",
                type=str,
                location=OpenApiParameter.QUERY,
                description="End date in YYYY-MM-DD format. Example: 2026-05-31",
            ),
            OpenApiParameter(
                name="limit",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Page size. Min 1, max 100. Default: 10",
            ),
            OpenApiParameter(
                name="offset",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Pagination offset. Min: 0. Example: 0, 10, 20",
            ),
        ],
        responses={
            200: PaginationHelper.get_paginated_response_serializer(
                AdminAIRequestListItemSerializer
            )
        },
        tags=["Chats Admin"],
    )
    def get(self, request: Request):
        pagination_serializer = PaginationQuerySerializer(data=request.query_params)
        if not pagination_serializer.is_valid():
            return error_response(
                5001, "Invalid pagination parameters", status.HTTP_400_BAD_REQUEST
            )

        query_serializer = AdminAIRequestQuerySerializer(data=request.query_params)
        if not query_serializer.is_valid():
            return error_response(
                5001, "Invalid query parameters", status.HTTP_400_BAD_REQUEST
            )

        filters = dict(query_serializer.validated_data)
        start_date = filters.pop("start_date", None)
        end_date = filters.pop("end_date", None)
        if start_date:
            filters["start_at"] = datetime.combine(start_date, time.min)
        if end_date:
            filters["end_at"] = datetime.combine(end_date, time.max)

        qs = list_admin_ai_requests(**filters)
        paginated = PaginationHelper.paginate_queryset(
            qs,
            limit=pagination_serializer.validated_data["limit"],
            offset=pagination_serializer.validated_data["offset"],
        )

        items = []
        related_user_messages = map_related_user_message_contents(paginated["items"])
        for msg in paginated["items"]:
            metadata = msg.metadata or {}
            parse_result = metadata.get("parse_result") or {}
            items.append(
                {
                    "id": msg.id,
                    "user_id": msg.user_id,
                    "user_email": msg.user.email,
                    "user_message": related_user_messages.get(str(msg.id)),
                    "assistant_message": msg.content,
                    "intent": parse_result.get("intent"),
                    "status": metadata.get("status"),
                    "model": metadata.get("model"),
                    "latency_ms": metadata.get("latency_ms"),
                    "created_at": msg.created_at,
                }
            )

        paginated["items"] = AdminAIRequestListItemSerializer(items, many=True).data
        return success_response(
            result=paginated, code=1000, status_code=status.HTTP_200_OK
        )


class AdminAIRequestDetailView(APIView):
    authentication_classes = [JwtAuthentication]
    permission_classes = [IsAdmin]

    @extend_schema(
        summary="Admin AI Request Detail",
        operation_id="admin_ai_monitor_request_detail",
        parameters=[
            OpenApiParameter(
                name="message_id",
                type=str,
                location=OpenApiParameter.PATH,
                description="Assistant message UUID from /admin/monitor/requests/",
                required=True,
            )
        ],
        responses={200: AdminAIRequestDetailResponseSerializer},
        tags=["Chats Admin"],
    )
    def get(self, request: Request, message_id: str):
        msg = list_admin_ai_requests().filter(id=message_id).first()
        if not msg:
            return error_response(
                5004, "Request log not found", status.HTTP_404_NOT_FOUND
            )

        result = {
            "id": msg.id,
            "user_id": msg.user_id,
            "user_email": msg.user.email,
            "user_message": find_related_user_message_content(msg),
            "assistant_message": msg.content,
            "metadata": _format_admin_metadata(msg.metadata or {}),
            "created_at": msg.created_at,
        }
        return success_response(
            result=result, code=1000, status_code=status.HTTP_200_OK
        )

    @extend_schema(
        summary="Delete Admin AI Request Log",
        description=(
            "Admin-only. Soft-delete this AI request log from Admin Monitoring "
            "and schedule it for hard deletion after the configured retention "
            "period. The related user message is marked with the same admin "
            "deletion metadata to avoid orphan chat rows."
        ),
        parameters=[
            OpenApiParameter(
                name="message_id",
                type=str,
                location=OpenApiParameter.PATH,
                description="Assistant message UUID from /admin/monitor/requests/",
                required=True,
            )
        ],
        responses={200: AdminAIRequestDeleteResponseSerializer},
        tags=["Chats Admin"],
    )
    def delete(self, request: Request, message_id: str):
        result = mark_admin_ai_request_deleted(message_id)
        if not result:
            return error_response(
                5004, "Request log not found", status.HTTP_404_NOT_FOUND
            )

        return success_response(
            result=result, code=1000, status_code=status.HTTP_200_OK
        )


class AdminAIErrorSummaryView(APIView):
    authentication_classes = [JwtAuthentication]
    permission_classes = [IsAdmin]

    @extend_schema(
        summary="Admin AI Error Summary",
        parameters=[
            OpenApiParameter(
                name="user_id",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filter by user UUID. ",
            ),
            OpenApiParameter(
                name="status",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filter by status. Options: success, failed, partial",
            ),
            OpenApiParameter(
                name="intent",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filter by intent. Options: transaction_batch, financial_question, greeting, unknown",
            ),
            OpenApiParameter(
                name="model",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filter by model name. Example: gemini-2.5-flash",
            ),
            OpenApiParameter(
                name="start_date",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Start date in YYYY-MM-DD format. Example: 2026-05-01",
            ),
            OpenApiParameter(
                name="end_date",
                type=str,
                location=OpenApiParameter.QUERY,
                description="End date in YYYY-MM-DD format. Example: 2026-05-31",
            ),
            OpenApiParameter(
                name="limit",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Page size. Min 1, max 100. Default: 10",
            ),
            OpenApiParameter(
                name="offset",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Pagination offset. Min: 0. Example: 0, 10, 20",
            ),
        ],
        responses={
            200: PaginationHelper.get_paginated_response_serializer(
                AdminAIErrorItemSerializer
            )
        },
        tags=["Chats Admin"],
    )
    def get(self, request: Request):
        pagination_serializer = PaginationQuerySerializer(data=request.query_params)
        if not pagination_serializer.is_valid():
            return error_response(
                5001, "Invalid pagination parameters", status.HTTP_400_BAD_REQUEST
            )

        query_serializer = AdminAIRequestQuerySerializer(data=request.query_params)
        if not query_serializer.is_valid():
            return error_response(
                5001, "Invalid query parameters", status.HTTP_400_BAD_REQUEST
            )

        filters = dict(query_serializer.validated_data)
        start_date = filters.pop("start_date", None)
        end_date = filters.pop("end_date", None)
        if start_date:
            filters["start_at"] = datetime.combine(start_date, time.min)
        if end_date:
            filters["end_at"] = datetime.combine(end_date, time.max)

        qs = list_admin_ai_requests(**filters)
        grouped = build_error_groups(qs)

        limit = pagination_serializer.validated_data["limit"]
        offset = pagination_serializer.validated_data["offset"]
        items = grouped[offset : offset + limit]
        paginated = PaginationHelper.pagination(limit, offset, len(grouped), items)
        paginated["items"] = AdminAIErrorItemSerializer(
            paginated["items"], many=True
        ).data
        return success_response(
            result=paginated, code=1000, status_code=status.HTTP_200_OK
        )
