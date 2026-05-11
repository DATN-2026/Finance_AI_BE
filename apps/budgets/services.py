from decimal import ROUND_HALF_UP, Decimal
from typing import Optional
from django.db import IntegrityError

from apps.users.models import User
from apps.categories.selector import get_category_by_id
from .models import Budget
from .selector import (
    get_budget_by_category_month_year,
    get_budget_by_id,
    get_monthly_budget_totals,
    get_over_budget_categories_count,
)


class BudgetServiceError(Exception):
    """Custom exception for budget service errors."""

    pass


def create_budget(
    user: User, category_id: str, amount: float, month: int, year: int
) -> Budget:
    """
    Create a new budget for a user.
    Validates that the category exists and belongs to the user.
    """
    # Verify category exists and belongs to user
    category = get_category_by_id(category_id, user)
    if not category:
        raise BudgetServiceError("Category not found or does not belong to user")

    # Check if budget already exists for this category/month/year
    existing_budget = get_budget_by_category_month_year(user, category_id, month, year)
    if existing_budget:
        raise BudgetServiceError(
            "Budget already exists for this category, month, and year"
        )

    try:
        budget = Budget.objects.create(
            user=user,
            category_id=category_id,
            amount=amount,
            month=month,
            year=year,
        )
        return budget
    except IntegrityError as exc:
        raise BudgetServiceError("Failed to create budget") from exc


def get_budget(budget_id: str, user: User) -> Budget:
    """
    Get a budget by ID for the authenticated user.
    """
    budget = get_budget_by_id(budget_id, user)
    if not budget:
        raise BudgetServiceError("Budget not found")
    return budget


def update_budget(
    budget_id: str,
    user: User,
    amount: Optional[float] = None,
    month: Optional[int] = None,
    year: Optional[int] = None,
) -> Budget:
    """
    Update a budget. Only amount, month, and year can be updated.
    Category cannot be changed (delete and create new instead).
    """
    budget = get_budget_by_id(budget_id, user)
    if not budget:
        raise BudgetServiceError("Budget not found")

    # If month or year is being changed, check for conflicts
    new_month = month if month is not None else budget.month
    new_year = year if year is not None else budget.year

    if new_month != budget.month or new_year != budget.year:
        existing = get_budget_by_category_month_year(
            user, str(budget.category_id), new_month, new_year
        )
        if existing and existing.id != budget.id:
            raise BudgetServiceError(
                "Budget already exists for this category in the specified month/year"
            )

    if amount is not None:
        budget.amount = amount
    if month is not None:
        budget.month = month
    if year is not None:
        budget.year = year

    try:
        budget.save()
        return budget
    except IntegrityError as exc:
        raise BudgetServiceError("Failed to update budget") from exc


def delete_budget(budget_id: str, user: User) -> None:
    """
    Delete a budget (hard delete).
    """
    budget = get_budget_by_id(budget_id, user)
    if not budget:
        raise BudgetServiceError("Budget not found")

    budget.delete()


def _to_money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def get_budget_overview(user: User, month: int, year: int) -> dict[str, object]:
    totals = get_monthly_budget_totals(user=user, month=month, year=year)

    total_budget = _to_money(totals["total_budget"])
    total_spent = _to_money(totals["total_spent"])
    remaining = _to_money(total_budget - total_spent)

    usage_percent = None
    if total_budget != Decimal("0.00"):
        usage_percent = float(
            ((total_spent / total_budget) * Decimal("100")).quantize(
                Decimal("0.1"), rounding=ROUND_HALF_UP
            )
        )

    over_budget_categories = get_over_budget_categories_count(
        user=user, month=month, year=year
    )

    return {
        "period": {"month": month, "year": year},
        "total_budget": total_budget,
        "total_spent": total_spent,
        "remaining": remaining,
        "usage_percent": usage_percent,
        "over_budget_categories_count": over_budget_categories,
    }
