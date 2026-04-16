from datetime import date
from decimal import Decimal
from typing import Optional

from django.db import IntegrityError

from apps.categories.selector import get_category_by_id
from apps.users.models import User

from .models import Transaction
from .selector import get_transaction_by_id


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
