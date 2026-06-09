import uuid

from django.db import models
from apps.users.models import User


class AIChatMessage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(User, on_delete=models.PROTECT, db_column="user_id")

    sender = models.CharField(max_length=20)
    content = models.TextField()

    metadata = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    deleted_by_user_at = models.DateTimeField(null=True, blank=True, db_index=True)

    deleted_by_admin_at = models.DateTimeField(null=True, blank=True, db_index=True)

    purge_after = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        db_table = "ai_chat_messages"
