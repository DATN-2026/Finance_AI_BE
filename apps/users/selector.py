from typing import Optional
from uuid import UUID
from django.db.models import QuerySet

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


def list_all_users() -> QuerySet[User]:

    return User.objects.filter(role="user").order_by("-created_at")
