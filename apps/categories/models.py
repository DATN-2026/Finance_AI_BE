import uuid
from django.db import models
from django.db.models import UniqueConstraint
from apps.users.models import User


class Category(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(User, on_delete=models.PROTECT, db_column="user_id")

    name = models.CharField(max_length=100)
    type = models.CharField(max_length=20)

    is_active = models.BooleanField(
        default=True
    )  # đảm bảo khi xóa category thì vẫn giữ lại các transaction liên quan, chỉ cần set is_active = False -> soft delete

    color = models.CharField(max_length=100, null=True, blank=True)
    icon = models.CharField(max_length=100, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "categories"
        constraints = [
            UniqueConstraint(
                fields=["user", "name"],
                name="unique_active_category_name",
            )
        ]


class DefaultCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    name = models.CharField(max_length=100)
    type = models.CharField(max_length=20)

    is_active = models.BooleanField(default=True)
    color = models.CharField(max_length=100, null=True, blank=True)
    icon = models.CharField(max_length=100, null=True, blank=True)
    sort_order = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "default_categories"
        constraints = [
            UniqueConstraint(
                fields=["name", "type"],
                name="unique_default_category_name_type",
            )
        ]
        ordering = ["sort_order", "name"]
