from decimal import Decimal
from typing import Optional
from uuid import UUID

from django.db.models import (
    Case,
    CharField,
    DecimalField,
    ExpressionWrapper,
    F,
    OuterRef,
    Subquery,
    Sum,
    Value,
    When,
)
from django.db.models.functions import Coalesce, Round

from apps.transactions.models import Transaction
from apps.users.models import User

from .models import Budget


def _get_budget_queryset_with_spending_annotations(user: User):
    spent_amount_subquery = (
        Transaction.objects.filter(
            user=user,
            category_id=OuterRef("category_id"),
            type="expense",
            transaction_date__month=OuterRef("month"),
            transaction_date__year=OuterRef("year"),
            is_deleted=False,
        )
        .values("category_id")
        .annotate(total_spent=Sum("amount"))
        .values("total_spent")[:1]
    )

    queryset = (
        Budget.objects.select_related("category")
        .filter(user=user)
        .annotate(
            spent_amount=Coalesce(
                Subquery(
                    spent_amount_subquery,
                    output_field=DecimalField(max_digits=15, decimal_places=2),
                ),
                Value(Decimal("0.00")),
                output_field=DecimalField(max_digits=15, decimal_places=2),
            )
        )
    )

    percent_expression = Case(
        When(
            amount__lte=0,
            then=Case(
                When(spent_amount__lte=0, then=Value(Decimal("0.00"))),
                default=Value(Decimal("100.01")),
                output_field=DecimalField(max_digits=7, decimal_places=2),
            ),
        ),
        default=ExpressionWrapper(
            (F("spent_amount") * Value(Decimal("100.00"))) / F("amount"),
            output_field=DecimalField(max_digits=7, decimal_places=2),
        ),
        output_field=DecimalField(max_digits=7, decimal_places=2),
    )

    return queryset.annotate(percent=Round(percent_expression, 2)).annotate(
        status=Case(
            When(percent__gt=Decimal("100"), then=Value("over")),
            When(percent__gte=Decimal("70"), then=Value("warning")),
            default=Value("safe"),
            output_field=CharField(),
        )
    )


def get_budget_by_id(budget_id: str, user: User) -> Optional[Budget]:
    """
    Get a budget by ID for a specific user.
    Only returns the budget if it belongs to the user.
    Accepts UUID in both formats (with/without hyphens).
    """
    try:
        # Normalize the UUID string
        budget_id = budget_id.strip()

        # If UUID without hyphens (32 chars), add hyphens
        if len(budget_id) == 32 and "-" not in budget_id:
            budget_id = f"{budget_id[:8]}-{budget_id[8:12]}-{budget_id[12:16]}-{budget_id[16:20]}-{budget_id[20:]}"

        # Convert to UUID object
        budget_uuid = UUID(budget_id)
        return _get_budget_queryset_with_spending_annotations(user=user).get(
            id=budget_uuid
        )
    except (ValueError, Budget.DoesNotExist):
        return None


def get_budget_by_category_month_year(
    user: User, category_id: str, month: int, year: int
) -> Optional[Budget]:
    """
    Get a budget for a specific category, month, and year.
    """
    try:
        return Budget.objects.select_related("category").get(
            user=user, category_id=category_id, month=month, year=year
        )
    except Budget.DoesNotExist:
        return None


def list_user_budgets(
    user: User,
    month: Optional[int] = None,
    year: Optional[int] = None,
    category_id: Optional[str] = None,
):
    """
    List all budgets for a specific user.
    Optionally filter by month, year, and/or category.
    """
    queryset = _get_budget_queryset_with_spending_annotations(user=user)

    if month is not None:
        queryset = queryset.filter(month=month)

    if year is not None:
        queryset = queryset.filter(year=year)

    if category_id:
        queryset = queryset.filter(category_id=category_id)

    return queryset.order_by("-percent", "-year", "-month", "category__name")


# def get_monthly_budget_totals(user: User, month: int, year: int) -> dict[str, Decimal]:
#     total_budget = Budget.objects.filter(user=user, month=month, year=year).aggregate(
#         total=Sum("amount")
#     )["total"] or Decimal("0.00")

#     total_spent = Transaction.objects.filter(
#         user=user,
#         type="expense",
#         transaction_date__month=month,
#         transaction_date__year=year,
#         is_deleted=False,
#     ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

#     return {
#         "total_budget": total_budget,
#         "total_spent": total_spent,
#     }


def get_monthly_budget_totals(
    user: User,
    month: int,
    year: int,
) -> dict[str, Decimal]:
    budget_queryset = Budget.objects.filter(
        user=user,
        month=month,
        year=year,
    )

    total_budget = budget_queryset.aggregate(total=Sum("amount"))["total"] or Decimal(
        "0.00"
    )

    budget_category_ids = budget_queryset.values_list(
        "category_id",
        flat=True,
    )

    total_spent = Transaction.objects.filter(
        user=user,
        type="expense",
        category_id__in=budget_category_ids,
        transaction_date__month=month,
        transaction_date__year=year,
        is_deleted=False,
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

    return {
        "total_budget": total_budget,
        "total_spent": total_spent,
    }


def get_over_budget_categories_count(user: User, month: int, year: int) -> int:
    return (
        _get_budget_queryset_with_spending_annotations(user=user)
        .filter(month=month, year=year)
        .filter(spent_amount__gt=F("amount"))
        .count()
    )


def get_monthly_budget_compliance(user: User, month: int, year: int) -> dict[str, int]:
    queryset = _get_budget_queryset_with_spending_annotations(user=user).filter(
        month=month,
        year=year,
    )

    return {
        "total_budget_categories": queryset.count(),
        "over_budget_categories_count": queryset.filter(
            spent_amount__gt=F("amount")
        ).count(),
    }
