from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import UUID

from django.db.models import Q, Sum

from apps.users.models import User

from .models import Transaction


def get_transaction_by_id(transaction_id: str, user: User) -> Optional[Transaction]:

    try:
        # normalized_id = transaction_id.strip()

        # if len(normalized_id) == 32 and "-" not in normalized_id:
        #     normalized_id = (
        #         f"{normalized_id[:8]}-{normalized_id[8:12]}-{normalized_id[12:16]}-"
        #         f"{normalized_id[16:20]}-{normalized_id[20:]}"
        #     )

        transaction_uuid = UUID(transaction_id)
        return Transaction.objects.select_related("category").get(
            id=transaction_uuid, user=user
        )
    except (ValueError, Transaction.DoesNotExist):
        return None


def list_user_transactions(
    user: User,
    type: Optional[str] = None,
    category_id: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
):
    """
    List transactions for a specific user with optional filters.
    """
    queryset = Transaction.objects.select_related("category").filter(user=user)

    if type:
        queryset = queryset.filter(type=type)

    if category_id:
        queryset = queryset.filter(category_id=category_id)

    if start_date:
        queryset = queryset.filter(transaction_date__gte=start_date)

    if end_date:
        queryset = queryset.filter(transaction_date__lte=end_date)

    return queryset.order_by("-transaction_date", "-created_at")


def get_monthly_transaction_totals(
    user: User, month: int, year: int
) -> dict[str, Decimal]:
    totals = Transaction.objects.filter(
        user=user,
        transaction_date__month=month,
        transaction_date__year=year,
    ).aggregate(
        income=Sum("amount", filter=Q(type="income")),
        expenses=Sum("amount", filter=Q(type="expense")),
    )

    income_total = totals["income"] or Decimal("0.00")
    expense_total = totals["expenses"] or Decimal("0.00")

    return {
        "income": income_total,
        "expenses": expense_total,
        "balance": income_total - expense_total,
    }


def get_spending_by_category(user: User, month: int, year: int):
    return (
        Transaction.objects.filter(
            user=user,
            type="expense",
            transaction_date__month=month,
            transaction_date__year=year,
        )
        .values(
            "category_id",
            "category__name",
            "category__type",
            "category__color",
            "category__icon",
        )
        .annotate(total_expense=Sum("amount"))
        .order_by("-total_expense", "category__name")
    )


def list_recent_transactions_by_month(user: User, month: int, year: int, limit: int):
    return (
        Transaction.objects.select_related("category")
        .filter(
            user=user,
            transaction_date__month=month,
            transaction_date__year=year,
        )
        .order_by("-transaction_date", "-created_at")[:limit]
    )
