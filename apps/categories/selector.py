from datetime import date
from typing import Optional

from django.db.models import Count, IntegerField, OuterRef, Q, Subquery, Value
from django.db.models.functions import Coalesce

from apps.transactions.models import Transaction
from apps.users.models import User

from .models import Category, DefaultCategory


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
            is_deleted=False,
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


def get_default_category_by_id(default_category_id: str) -> Optional[DefaultCategory]:
    try:
        return DefaultCategory.objects.get(id=default_category_id)
    except DefaultCategory.DoesNotExist:
        return None


def list_default_categories(
    type: Optional[str] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
):
    queryset = DefaultCategory.objects.all()

    if type:
        queryset = queryset.filter(type=type)

    if is_active is not None:
        queryset = queryset.filter(is_active=is_active)

    if search:
        queryset = queryset.filter(name__icontains=search)

    return queryset.order_by("sort_order", "name")


def get_default_category_list_stats() -> dict[str, int]:
    return DefaultCategory.objects.aggregate(
        total_default_templates=Count("id"),
        total_active_defaults=Count("id", filter=Q(is_active=True)),
        total_expense_types=Count("id", filter=Q(type="expense")),
        total_income_types=Count("id", filter=Q(type="income")),
    )


def list_admin_user_categories(
    user_id: Optional[str] = None,
    type: Optional[str] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
):
    queryset = Category.objects.select_related("user").all()

    if user_id:
        queryset = queryset.filter(user_id=user_id)

    if type:
        queryset = queryset.filter(type=type)

    if is_active is not None:
        queryset = queryset.filter(is_active=is_active)

    if search:
        queryset = queryset.filter(name__icontains=search)

    return queryset.order_by("-created_at")
