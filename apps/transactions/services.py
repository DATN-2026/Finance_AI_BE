from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional

from django.db import IntegrityError

from apps.categories.selector import get_category_by_id
from apps.users.models import User

from .models import Transaction
from .selector import (
    get_monthly_transaction_totals,
    get_spending_by_category,
    get_transaction_by_id,
    list_recent_transactions_by_month,
)


class TransactionServiceError(Exception):
    """Custom exception for transaction service errors."""

    pass


def create_transaction(
    user: User,
    category_id: str,
    amount: Decimal,
    transaction_date: date,
    note: Optional[str] = None,
) -> Transaction:
    """
    Create a transaction for the authenticated user.
    Transaction type is inferred from category type.
    """
    category = get_category_by_id(category_id, user)
    if not category:
        raise TransactionServiceError("Category not found or does not belong to user")

    try:
        transaction = Transaction.objects.create(
            user=user,
            category=category,
            type=category.type,
            amount=amount,
            note=note,
            transaction_date=transaction_date,
        )
        return transaction
    except IntegrityError as exc:
        raise TransactionServiceError("Failed to create transaction") from exc


def get_transaction(transaction_id: str, user: User) -> Transaction:
    transaction = get_transaction_by_id(transaction_id, user)
    if not transaction:
        raise TransactionServiceError("Transaction not found")
    return transaction


def update_transaction(
    transaction_id: str,
    user: User,
    category_id: Optional[str] = None,
    amount: Optional[Decimal] = None,
    note: Optional[str] = None,
    transaction_date: Optional[date] = None,
) -> Transaction:
    transaction = get_transaction_by_id(transaction_id, user)
    if not transaction:
        raise TransactionServiceError("Transaction not found")

    if category_id:
        category = get_category_by_id(category_id, user)
        if not category:
            raise TransactionServiceError(
                "Category not found or does not belong to user"
            )
        transaction.category = category
        transaction.type = category.type

    if amount is not None:
        transaction.amount = amount

    if note is not None:
        transaction.note = note

    if transaction_date is not None:
        transaction.transaction_date = transaction_date

    try:
        transaction.save()
        return transaction
    except IntegrityError as exc:
        raise TransactionServiceError("Failed to update transaction") from exc


def delete_transaction(transaction_id: str, user: User) -> None:
    transaction = get_transaction_by_id(transaction_id, user)
    if not transaction:
        raise TransactionServiceError("Transaction not found")

    transaction.delete()


def _to_money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _build_summary_metric(current: Decimal, previous: Decimal) -> dict[str, object]:
    current_amount = _to_money(current)
    previous_amount = _to_money(previous)
    delta_amount = _to_money(current_amount - previous_amount)

    trend = "flat"
    if delta_amount > 0:
        trend = "up"
    elif delta_amount < 0:
        trend = "down"

    comparable = previous_amount != Decimal("0.00")
    change_percent = None

    if comparable:
        ratio = (delta_amount / abs(previous_amount)) * Decimal("100")
        change_percent = float(ratio.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))

    return {
        "amount": current_amount,
        "previous_amount": previous_amount,
        "delta_amount": delta_amount,
        "change_percent": change_percent,
        "trend": trend,
        "comparable": comparable,
    }


def get_dashboard_summary(user: User, month: int, year: int) -> dict[str, object]:
    previous_month = 12 if month == 1 else month - 1
    previous_year = year - 1 if month == 1 else year

    current_totals = get_monthly_transaction_totals(user=user, month=month, year=year)
    previous_totals = get_monthly_transaction_totals(
        user=user,
        month=previous_month,
        year=previous_year,
    )

    return {
        "period": {"month": month, "year": year},
        "previous_period": {"month": previous_month, "year": previous_year},
        "income": _build_summary_metric(
            current=current_totals["income"],
            previous=previous_totals["income"],
        ),
        "expenses": _build_summary_metric(
            current=current_totals["expenses"],
            previous=previous_totals["expenses"],
        ),
        "balance": _build_summary_metric(
            current=current_totals["balance"],
            previous=previous_totals["balance"],
        ),
    }


def _get_last_12_periods(month: int, year: int) -> list[tuple[int, int]]:
    periods: list[tuple[int, int]] = []
    current_month = month
    current_year = year

    for _ in range(12):
        periods.append((current_month, current_year))
        current_month -= 1
        if current_month == 0:
            current_month = 12
            current_year -= 1

    periods.reverse()
    return periods


def get_cashflow_period_summary(user: User, month: int, year: int) -> dict[str, object]:
    periods = _get_last_12_periods(month=month, year=year)
    result = []

    for period_month, period_year in periods:
        totals = get_monthly_transaction_totals(
            user=user,
            month=period_month,
            year=period_year,
        )
        result.append(
            {
                "period": {"month": period_month, "year": period_year},
                "income": _to_money(totals["income"]),
                "expenses": _to_money(totals["expenses"]),
            }
        )

    return {"periods": result}


def get_balance_period_summary(user: User, month: int, year: int) -> dict[str, object]:
    periods = _get_last_12_periods(month=month, year=year)
    result = []

    for period_month, period_year in periods:
        totals = get_monthly_transaction_totals(
            user=user,
            month=period_month,
            year=period_year,
        )
        result.append(
            {
                "period": {"month": period_month, "year": period_year},
                "balance": _to_money(totals["balance"]),
            }
        )

    return {"periods": result}


def get_spending_by_category_summary(
    user: User, month: int, year: int
) -> dict[str, object]:
    rows = get_spending_by_category(user=user, month=month, year=year)
    total_spending = Decimal("0.00")

    for row in rows:
        total_spending += row["total_expense"] or Decimal("0.00")

    total_spending = _to_money(total_spending)
    categories: list[dict[str, object]] = []

    for row in rows:
        expense_amount = _to_money(row["total_expense"] or Decimal("0.00"))
        if total_spending == Decimal("0.00"):
            percent = Decimal("0.00")
        else:
            percent = ((expense_amount / total_spending) * Decimal("100")).quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP,
            )

        categories.append(
            {
                "category": {
                    "id": row["category_id"],
                    "name": row["category__name"],
                    "type": row["category__type"],
                    "color": row["category__color"],
                    "icon": row["category__icon"],
                },
                "total_expense": expense_amount,
                "percent": percent,
            }
        )

    return {
        "total_spending": total_spending,
        "categories": categories,
    }


def get_recent_transactions(user: User, month: int, year: int, limit: int):
    return list_recent_transactions_by_month(
        user=user,
        month=month,
        year=year,
        limit=limit,
    )
