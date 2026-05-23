from apps.users.models import User

from .models import AIChatMessage


def list_user_chat_messages(user: User):
    return AIChatMessage.objects.filter(user=user).order_by("-created_at")


def delete_user_chat_messages(user: User) -> int:
    deleted_count, _ = AIChatMessage.objects.filter(user=user).delete()
    return deleted_count
