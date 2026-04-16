from decimal import Decimal

from rest_framework import serializers
from apps.categories.serializers import CategorySerializer


class CreateBudgetSerializer(serializers.Serializer):
    category_id = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=15, decimal_places=2, min_value=0)
    month = serializers.IntegerField(min_value=1, max_value=12)
    year = serializers.IntegerField(min_value=2000, max_value=2100)


class UpdateBudgetSerializer(serializers.Serializer):
    amount = serializers.DecimalField(
        max_digits=15, decimal_places=2, min_value=0, required=False
    )
    month = serializers.IntegerField(min_value=1, max_value=12, required=False)
    year = serializers.IntegerField(min_value=2000, max_value=2100, required=False)


class BudgetResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    user_id = serializers.UUIDField(source="user.id")
    category = CategorySerializer()
    amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    spent_amount = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        read_only=True,
        default=Decimal("0.00"),
    )
    month = serializers.IntegerField()
    year = serializers.IntegerField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
