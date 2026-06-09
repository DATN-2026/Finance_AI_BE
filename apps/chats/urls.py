from django.urls import path

from .views import (
    AdminAIErrorSummaryView,
    AdminAIMonitorOverviewView,
    AdminAIRequestDetailView,
    AdminAIRequestListView,
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
    path(
        "admin/monitor/overview/",
        AdminAIMonitorOverviewView.as_view(),
        name="admin-ai-monitor-overview",
    ),
    path(
        "admin/monitor/requests/",
        AdminAIRequestListView.as_view(),
        name="admin-ai-monitor-requests",
    ),
    path(
        "admin/monitor/requests/<str:message_id>/",
        AdminAIRequestDetailView.as_view(),
        name="admin-ai-monitor-request-detail",
    ),
    path(
        "admin/monitor/errors/",
        AdminAIErrorSummaryView.as_view(),
        name="admin-ai-monitor-errors",
    ),
]
