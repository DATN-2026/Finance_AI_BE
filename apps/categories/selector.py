from datetime import date
from typing import Optional

from django.db.models import Count, IntegerField, OuterRef, Subquery, Value
from django.db.models.functions import Coalesce

from apps.transactions.models import Transaction
from apps.users.models import User

from .models import Category


def get_category_by_id(category_id: str, user: User) -> Optional[Category]:
    """
    Get a category by ID for a specific user.
    Only returns the category if it belongs to the user.
    """
    try:
        return Category.objects.get(id=category_id, user=user, is_active=True)
    except Category.DoesNotExist:
        return None


def get_category_by_name(name: str, user: User) -> Optional[Category]:
    """
    Get a category by name for a specific user.
    """
    try:
        return Category.objects.get(name=name, user=user, is_active=True)
    except Category.DoesNotExist:
        return None


def list_user_categories(
    user: User,
    type: Optional[str] = None,
    month: Optional[int] = None,
    year: Optional[int] = None,
):
    """
    List all active categories for a specific user.
    Optionally filter by type (income/expense).
    """
    today = date.today()
    filter_month = month if month is not None else today.month
    filter_year = year if year is not None else today.year

    transactions_count_subquery = (
        Transaction.objects.filter(
            user=user,
            category_id=OuterRef("id"),
            transaction_date__month=filter_month,
            transaction_date__year=filter_year,
        )
        .values("category_id")
        .annotate(total_transactions=Count("id"))
        .values("total_transactions")[:1]
    )

    queryset = Category.objects.filter(user=user, is_active=True).annotate(
        transactions_count=Coalesce(
            Subquery(transactions_count_subquery, output_field=IntegerField()),
            Value(0),
            output_field=IntegerField(),
        )
    )

    if type:
        queryset = queryset.filter(type=type)

    return queryset.order_by("-created_at")
