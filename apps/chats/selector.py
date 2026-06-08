from collections import Counter
from datetime import datetime, timedelta
from statistics import mean
from typing import Any

from django.conf import settings
from django.db.models import QuerySet
from django.utils import timezone

from apps.users.models import User

from .models import AIChatMessage


def list_user_chat_messages(user: User):
    return AIChatMessage.objects.filter(
        user=user,
        deleted_by_user_at__isnull=True,
    ).order_by("-created_at")


def delete_user_chat_messages(user: User) -> int:
    return AIChatMessage.objects.filter(
        user=user,
        deleted_by_user_at__isnull=True,
    ).update(deleted_by_user_at=timezone.now())


def list_admin_ai_requests(
    user_id: str | None = None,
    status: str | None = None,
    intent: str | None = None,
    model: str | None = None,
    start_at: datetime | None = None,
    end_at: datetime | None = None,
) -> QuerySet[AIChatMessage]:
    qs = AIChatMessage.objects.filter(
        sender="assistant",
        deleted_by_admin_at__isnull=True,
    ).select_related("user")

    if user_id:
        qs = qs.filter(user_id=user_id)
    if start_at:
        qs = qs.filter(created_at__gte=start_at)
    if end_at:
        qs = qs.filter(created_at__lte=end_at)

    if status:
        qs = qs.filter(metadata__status=status)
    if intent:
        qs = qs.filter(metadata__parse_result__intent=intent)
    if model:
        qs = qs.filter(metadata__model=model)

    return qs.order_by("-created_at")


def _percentile(values: list[int], pct: float) -> int:
    if not values:
        return 0
    sorted_vals = sorted(values)
    idx = int(round((pct / 100.0) * (len(sorted_vals) - 1)))
    return sorted_vals[max(0, min(idx, len(sorted_vals) - 1))]


def build_overview_metrics(request_qs: QuerySet[AIChatMessage]) -> dict[str, Any]:
    total_requests = request_qs.count()

    status_counts = Counter()
    intent_counts = Counter()
    latencies: list[int] = []

    for msg in request_qs:
        metadata = msg.metadata or {}
        status_counts[str(metadata.get("status", "unknown"))] += 1
        parse_result = metadata.get("parse_result") or {}
        intent_counts[str(parse_result.get("intent", "unknown"))] += 1
        latency = metadata.get("latency_ms")
        if isinstance(latency, int):
            latencies.append(latency)

    success_count = status_counts.get("success", 0)
    failed_count = status_counts.get("failed", 0) + status_counts.get("error", 0)
    partial_count = status_counts.get("partial", 0)
    success_rate = (success_count / total_requests * 100.0) if total_requests else 0.0

    return {
        "total_requests": total_requests,
        "success_count": success_count,
        "failed_count": failed_count,
        "partial_count": partial_count,
        "success_rate": round(success_rate, 2),
        "avg_latency_ms": round(mean(latencies), 2) if latencies else 0,
        "p95_latency_ms": _percentile(latencies, 95),
        "intent_distribution": dict(intent_counts),
    }


def find_related_user_message_content(assistant_msg: AIChatMessage) -> str | None:
    user_msg = (
        AIChatMessage.objects.filter(
            user=assistant_msg.user,
            sender="user",
            created_at__lte=assistant_msg.created_at,
            deleted_by_admin_at__isnull=True,
        )
        .order_by("-created_at")
        .first()
    )
    return user_msg.content if user_msg else None


def map_related_user_message_contents(
    assistant_messages: list[AIChatMessage],
) -> dict[str, str | None]:
    if not assistant_messages:
        return {}

    user_ids = {msg.user_id for msg in assistant_messages}
    max_created_at = max(msg.created_at for msg in assistant_messages)
    user_messages = list(
        AIChatMessage.objects.filter(
            user_id__in=user_ids,
            sender="user",
            created_at__lte=max_created_at,
            deleted_by_admin_at__isnull=True,
        )
        .only("id", "user_id", "content", "created_at")
        .order_by("user_id", "-created_at")
    )

    grouped_user_messages: dict[str, list[AIChatMessage]] = {}
    for msg in user_messages:
        grouped_user_messages.setdefault(str(msg.user_id), []).append(msg)

    related: dict[str, str | None] = {}
    for assistant_msg in assistant_messages:
        content = None
        for user_msg in grouped_user_messages.get(str(assistant_msg.user_id), []):
            if user_msg.created_at <= assistant_msg.created_at:
                content = user_msg.content
                break
        related[str(assistant_msg.id)] = content

    return related


def build_error_groups(request_qs: QuerySet[AIChatMessage]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}

    def add_error(error_type: str, message: str, seen_at: datetime) -> None:
        key = f"{error_type}:{message}"
        if key not in grouped:
            grouped[key] = {
                "error_type": error_type,
                "message": message,
                "count": 0,
                "last_seen_at": seen_at,
            }

        grouped[key]["count"] += 1
        if seen_at > grouped[key]["last_seen_at"]:
            grouped[key]["last_seen_at"] = seen_at

    for msg in request_qs:
        metadata = msg.metadata or {}
        parse_result = metadata.get("parse_result") or {}
        has_specific_error = False

        query_error = parse_result.get("query_error")
        if query_error:
            add_error("query_error", str(query_error), msg.created_at)
            has_specific_error = True

        for rejected in parse_result.get("rejected_actions") or []:
            if not isinstance(rejected, dict):
                continue
            reason = rejected.get("reason")
            if reason:
                add_error("rejected_action", str(reason), msg.created_at)
                has_specific_error = True

        request_status = metadata.get("status")
        if request_status in {"failed", "error", "partial"} and not has_specific_error:
            add_error("request_status", str(request_status), msg.created_at)

    items = list(grouped.values())
    items.sort(key=lambda x: (x["count"], x["last_seen_at"]), reverse=True)
    return items


def mark_admin_ai_request_deleted(message_id: str) -> dict[str, Any] | None:
    assistant_msg = list_admin_ai_requests().filter(id=message_id).first()
    if not assistant_msg:
        return None

    now = timezone.now()
    retention_days = getattr(settings, "CHAT_ADMIN_DELETE_RETENTION_DAYS", 30)
    purge_after = now + timedelta(days=retention_days)

    related_user_msg = (
        AIChatMessage.objects.filter(
            user=assistant_msg.user,
            sender="user",
            created_at__lte=assistant_msg.created_at,
            deleted_by_admin_at__isnull=True,
        )
        .order_by("-created_at")
        .first()
    )

    message_ids = [assistant_msg.id]
    if related_user_msg:
        message_ids.append(related_user_msg.id)

    updated_count = AIChatMessage.objects.filter(id__in=message_ids).update(
        deleted_by_admin_at=now,
        purge_after=purge_after,
    )

    return {
        "message": "Deleted successfully.",
        "deleted": updated_count,
        "purge_after": purge_after,
    }
