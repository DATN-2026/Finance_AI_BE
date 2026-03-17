import uuid

from django.db import models

from apps.categories.models import Category
from apps.users.models import User


class Transaction(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(User, on_delete=models.PROTECT, db_column="user_id")
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, db_column="category_id"
    )

    type = models.CharField(max_length=20)
    amount = models.DecimalField(max_digits=15, decimal_places=2)

    note = models.TextField(null=True, blank=True)

    transaction_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "transactions"
