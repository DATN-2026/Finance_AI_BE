from django.urls import path

from .views import (
    ChatHistoryClearView,
    ChatHistoryView,
    ChatParseCommitView,
    ChatParseLLMResponseView,
    ChatParseView,
)

urlpatterns = [
    path("parse/", ChatParseView.as_view(), name="chat-parse"),
    path("parse/commit/", ChatParseCommitView.as_view(), name="chat-parse-commit"),
    path(
        "parse/response/llm/",
        ChatParseLLMResponseView.as_view(),
        name="chat-parse-llm-response",
    ),
    path("history/", ChatHistoryView.as_view(), name="chat-history"),
    path("history/clear/", ChatHistoryClearView.as_view(), name="chat-history-clear"),
]
