from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import UUID
import calendar

from django.db.models import Count, Q, QuerySet, Sum

from .models import User


def get_user_by_id(user_id: str) -> Optional[User]:

    try:
        # Convert string UUID to UUID object to handle both formats (with/without hyphens)
        user_uuid = UUID(user_id)
        return User.objects.get(id=user_uuid)
    except (ValueError, User.DoesNotExist):
        return None


def get_user_by_email(email: str) -> Optional[User]:

    try:
        return User.objects.get(email=email.lower())
    except User.DoesNotExist:
        return None


def list_all_users(
    search: Optional[str] = None,
    role: Optional[str] = None,
    status: Optional[str] = None,
    sort_by: Optional[str] = None,
) -> QuerySet[User]:
    """
    Return a queryset of all users with optional search, filter, and sort.

    Args:
        search: Case-insensitive search against email or name.
        role: Filter by role ("user" or "admin").
        status: Filter by status ("active" or "inactive").
        sort_by: Field to sort by (prefix with "-" for descending).
                 Allowed: created_at, -created_at, name, -name, email, -email.

    Returns:
        Filtered and sorted QuerySet[User].
    """
    qs = User.objects.all()

    if search:
        qs = qs.filter(Q(email__icontains=search) | Q(name__icontains=search))

    if role:
        qs = qs.filter(role=role)

    if status:
        qs = qs.filter(status=status)

    order_field = sort_by if sort_by else "-created_at"
    qs = qs.order_by(order_field)

    return qs


def get_user_list_stats() -> dict[str, int]:
    return User.objects.aggregate(
        total_users=Count("id"),
        total_active=Count("id", filter=Q(status="active")),
        total_inactive=Count("id", filter=Q(status="inactive")),
        total_admins=Count("id", filter=Q(role="admin")),
    )


def get_user_usage_stats(
    user: User,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> dict:
    """
    Aggregate usage statistics for a given user.

    Queries:
      - transactions count + income/expense totals
      - budgets count
      - AI chat messages sent by the user (sender="user")

    Returns:
        dict with keys:
          total_transactions, total_income_amount, total_expense_amount,
          total_budgets, total_ai_requests
    """
    # Import here to avoid circular import at module level
    from apps.transactions.models import Transaction
    from apps.budgets.models import Budget
    from apps.chats.models import AIChatMessage

    today = date.today()
    if not start_date:
        start_date = today.replace(day=1)
    if not end_date:
        _, last_day = calendar.monthrange(today.year, today.month)
        end_date = today.replace(day=last_day)

    tx_qs = Transaction.objects.filter(
        user=user,
        transaction_date__gte=start_date,
        transaction_date__lte=end_date,
    )

    total_transactions = tx_qs.count()

    income_agg = tx_qs.filter(type="income").aggregate(total=Sum("amount"))
    expense_agg = tx_qs.filter(type="expense").aggregate(total=Sum("amount"))

    total_income_amount: Decimal = income_agg["total"] or Decimal("0.00")
    total_expense_amount: Decimal = expense_agg["total"] or Decimal("0.00")

    total_budgets = Budget.objects.filter(
        user=user,
        created_at__date__gte=start_date,
        created_at__date__lte=end_date,
    ).count()

    total_ai_requests = AIChatMessage.objects.filter(
        user=user,
        sender="user",
        created_at__date__gte=start_date,
        created_at__date__lte=end_date,
    ).count()

    return {
        "total_transactions": total_transactions,
        "total_income_amount": total_income_amount,
        "total_expense_amount": total_expense_amount,
        "total_budgets": total_budgets,
        "total_ai_requests": total_ai_requests,
    }
