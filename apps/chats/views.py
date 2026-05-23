from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.views import APIView

from core.authentication.permissions import IsAuthenticated, JwtAuthentication
from core.untils.api_response import error_response, success_response
from core.untils.pagination import PaginationHelper, PaginationQuerySerializer

from apps.transactions.serializers import TransactionResponseSerializer
from apps.transactions.services import TransactionServiceError

from .serializers import (
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
            parse_result, raw_llm_output, model_name, intent_step_info = parse_message_for_commit(
                user=request.user,
                message=serializer.validated_data["message"],
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
        description="Delete chat history for the authenticated user.",
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
