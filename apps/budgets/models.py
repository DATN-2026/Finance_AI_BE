from django.db import models
from django.db.models import UniqueConstraint
import uuid

from apps.users.models import User
from apps.categories.models import Category


class Budget(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(User, on_delete=models.PROTECT, db_column="user_id")
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, db_column="category_id"
    )

    amount = models.DecimalField(max_digits=15, decimal_places=2)
    month = models.IntegerField()
    year = models.IntegerField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "budgets"
        constraints = [
            UniqueConstraint(
                fields=["user", "category", "month", "year"],
                name="unique_user_category_month_year",
            )
        ]
