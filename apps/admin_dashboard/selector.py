from collections import Counter
from datetime import date
from decimal import Decimal
from statistics import mean
from typing import Any

from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncDate

from apps.chats.models import AIChatMessage
from apps.transactions.models import Transaction
from apps.users.models import User


def _date_filtered_users(start_date: date | None, end_date: date | None):
    qs = User.objects.all()
    if start_date:
        qs = qs.filter(created_at__date__gte=start_date)
    if end_date:
        qs = qs.filter(created_at__date__lte=end_date)
    return qs


def _date_filtered_transactions(start_date: date | None, end_date: date | None):
    qs = Transaction.objects.all()
    if start_date:
        qs = qs.filter(transaction_date__gte=start_date)
    if end_date:
        qs = qs.filter(transaction_date__lte=end_date)
    return qs


def _date_filtered_ai_requests(start_date: date | None, end_date: date | None):
    qs = AIChatMessage.objects.filter(
        sender="assistant", deleted_by_admin_at__isnull=True
    )
    if start_date:
        qs = qs.filter(created_at__date__gte=start_date)
    if end_date:
        qs = qs.filter(created_at__date__lte=end_date)
    return qs


def get_admin_dashboard_overview(
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict[str, Any]:
    users_in_range = _date_filtered_users(start_date, end_date)
    transactions = _date_filtered_transactions(start_date, end_date)
    active_transactions = transactions.filter(is_deleted=False)
    ai_requests = _date_filtered_ai_requests(start_date, end_date)

    totals = active_transactions.aggregate(
        income=Sum("amount", filter=Q(type="income")),
        expenses=Sum("amount", filter=Q(type="expense")),
        active_transaction_count=Count("id"),
    )
    income = totals["income"] or Decimal("0.00")
    expenses = totals["expenses"] or Decimal("0.00")
    deleted_transaction_count = transactions.filter(is_deleted=True).count()

    status_counts = Counter()
    latencies: list[int] = []
    for msg in ai_requests:
        metadata = msg.metadata or {}
        status_counts[str(metadata.get("status", "unknown"))] += 1
        latency = metadata.get("latency_ms")
        if isinstance(latency, int):
            latencies.append(latency)

    return {
        "users": {
            "total": User.objects.count(),
            "active": User.objects.filter(status="active").count(),
            "inactive": User.objects.filter(status="inactive").count(),
            "new_in_range": users_in_range.count(),
        },
        "transactions": {
            "income": income,
            "expenses": expenses,
            "active_transaction_count": totals["active_transaction_count"] or 0,
            "deleted_transaction_count": deleted_transaction_count,
        },
        "ai_requests": {
            "total": ai_requests.count(),
            "success": status_counts.get("success", 0),
            "failed": status_counts.get("failed", 0) + status_counts.get("error", 0),
            "partial": status_counts.get("partial", 0),
            "avg_latency_ms": round(mean(latencies), 2) if latencies else 0,
        },
    }


def get_admin_user_growth(
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict[str, Any]]:
    return list(
        _date_filtered_users(start_date, end_date)
        .annotate(date=TruncDate("created_at"))
        .values("date")
        .annotate(new_users=Count("id"))
        .order_by("date")
    )


def get_admin_financial_trend(
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict[str, Any]]:
    rows = (
        _date_filtered_transactions(start_date, end_date)
        .filter(is_deleted=False)
        .values("transaction_date")
        .annotate(
            income=Sum("amount", filter=Q(type="income")),
            expenses=Sum("amount", filter=Q(type="expense")),
            transaction_count=Count("id"),
        )
        .order_by("transaction_date")
    )

    result = []
    for row in rows:
        income = row["income"] or Decimal("0.00")
        expenses = row["expenses"] or Decimal("0.00")
        result.append(
            {
                "date": row["transaction_date"],
                "income": income,
                "expenses": expenses,
                "transaction_count": row["transaction_count"],
            }
        )
    return result


def get_admin_top_users(
    start_date: date | None = None,
    end_date: date | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    ai_rows = (
        _date_filtered_ai_requests(start_date, end_date)
        .values("user_id")
        .annotate(ai_request_count=Count("id"))
        .order_by("-ai_request_count")[:limit]
    )

    user_ids = [row["user_id"] for row in ai_rows]
    users = {user.id: user for user in User.objects.filter(id__in=user_ids)}

    tx_counts = {
        row["user_id"]: row["transaction_count"]
        for row in _date_filtered_transactions(start_date, end_date)
        .filter(is_deleted=False)
        .filter(user_id__in=user_ids)
        .values("user_id")
        .annotate(transaction_count=Count("id"))
    }

    result = []
    for row in ai_rows:
        user = users.get(row["user_id"])
        if not user:
            continue
        result.append(
            {
                "user_id": user.id,
                "email": user.email,
                "name": user.name,
                "ai_request_count": row["ai_request_count"],
                "transaction_count": tx_counts.get(user.id, 0),
            }
        )
    return result


def get_admin_top_categories(
    start_date: date | None = None,
    end_date: date | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    rows = (
        _date_filtered_transactions(start_date, end_date)
        .filter(is_deleted=False)
        .values("category_id", "category__name", "category__type")
        .annotate(transaction_count=Count("id"), total_amount=Sum("amount"))
        .order_by("-transaction_count", "-total_amount")[:limit]
    )

    return [
        {
            "category_id": row["category_id"],
            "category_name": row["category__name"],
            "category_type": row["category__type"],
            "transaction_count": row["transaction_count"],
            "total_amount": row["total_amount"] or Decimal("0.00"),
        }
        for row in rows
    ]
