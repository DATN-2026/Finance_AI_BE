from decimal import Decimal

from rest_framework import serializers
from apps.categories.serializers import CategorySerializer


class CreateBudgetSerializer(serializers.Serializer):
    category_id = serializers.UUIDField()
    amount = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        min_value=Decimal("50000"),
        error_messages={
            "min_value": "Budget amount must be at least 50,000.",
        },
    )
    month = serializers.IntegerField(min_value=1, max_value=12)
    year = serializers.IntegerField(min_value=2000, max_value=2100)


class UpdateBudgetSerializer(serializers.Serializer):
    amount = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        min_value=Decimal("50000"),
        error_messages={
            "min_value": "Budget amount must be at least 50,000.",
        },
        required=False,
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


class BudgetListResponseSerializer(BudgetResponseSerializer):
    percent = serializers.DecimalField(max_digits=7, decimal_places=2, read_only=True)
    status = serializers.ChoiceField(
        choices=["over", "warning", "safe"],
        read_only=True,
    )


class BudgetOverviewPeriodSerializer(serializers.Serializer):
    month = serializers.IntegerField()
    year = serializers.IntegerField()


class BudgetOverviewResultSerializer(serializers.Serializer):
    period = BudgetOverviewPeriodSerializer()
    total_budget = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_spent = serializers.DecimalField(max_digits=15, decimal_places=2)
    remaining = serializers.DecimalField(max_digits=15, decimal_places=2)
    usage_percent = serializers.FloatField(allow_null=True)
    over_budget_categories_count = serializers.IntegerField()


class BudgetOverviewResponseSerializer(serializers.Serializer):
    code = serializers.IntegerField(default=1000)
    result = BudgetOverviewResultSerializer()
