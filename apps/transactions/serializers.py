from decimal import Decimal

from rest_framework import serializers
from apps.categories.serializers import CategorySerializer


class CreateTransactionSerializer(serializers.Serializer):
    category_id = serializers.UUIDField()
    amount = serializers.DecimalField(
        max_digits=15, decimal_places=2, min_value=Decimal("0.01")
    )
    description = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    transaction_date = serializers.DateField()


class UpdateTransactionSerializer(serializers.Serializer):
    category_id = serializers.UUIDField(required=False)
    amount = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        min_value=Decimal("0.01"),
        required=False,
    )
    description = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    transaction_date = serializers.DateField(required=False)


class TransactionListQuerySerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=["income", "expense"], required=False)
    category_id = serializers.UUIDField(required=False)
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)

    def validate(self, attrs):
        start_date = attrs.get("start_date")
        end_date = attrs.get("end_date")

        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError("start_date must be before end_date")

        return attrs


class TransactionSummaryQuerySerializer(serializers.Serializer):
    month = serializers.IntegerField(min_value=1, max_value=12, required=False)
    year = serializers.IntegerField(min_value=2000, max_value=2100, required=False)

    def validate(self, attrs):
        has_month = "month" in attrs
        has_year = "year" in attrs

        if has_month != has_year:
            raise serializers.ValidationError(
                "month and year must be provided together"
            )

        return attrs


class RecentTransactionsQuerySerializer(TransactionSummaryQuerySerializer):
    limit = serializers.IntegerField(
        min_value=1, max_value=100, required=False, default=5
    )


class TransactionResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    user_id = serializers.UUIDField(source="user.id")
    category = CategorySerializer()
    type = serializers.CharField()
    amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    description = serializers.CharField(allow_null=True, allow_blank=True)
    transaction_date = serializers.DateField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class SummaryPeriodSerializer(serializers.Serializer):
    month = serializers.IntegerField()
    year = serializers.IntegerField()


class SummaryMetricSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    previous_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    delta_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    change_percent = serializers.FloatField(allow_null=True)
    trend = serializers.ChoiceField(choices=["up", "down", "flat"])
    comparable = serializers.BooleanField()
    # Nếu Previous Amount là 0, thì không thể so sánh được, nên sẽ đặt comparable = False và change_percent = Null


class TransactionSummaryResultSerializer(serializers.Serializer):
    period = SummaryPeriodSerializer()
    previous_period = SummaryPeriodSerializer()
    income = SummaryMetricSerializer()
    expenses = SummaryMetricSerializer()
    balance = SummaryMetricSerializer()


class TransactionSummaryResponseSerializer(serializers.Serializer):
    code = serializers.IntegerField(default=1000)
    result = TransactionSummaryResultSerializer()


class FinancialHealthSavingsSerializer(serializers.Serializer):
    available = serializers.BooleanField()
    score = serializers.IntegerField(allow_null=True)
    weight = serializers.FloatField()
    income = serializers.DecimalField(max_digits=15, decimal_places=2)
    expenses = serializers.DecimalField(max_digits=15, decimal_places=2)
    balance = serializers.DecimalField(max_digits=15, decimal_places=2)
    savings_rate = serializers.FloatField(allow_null=True)
    status = serializers.ChoiceField(
        choices=["good", "warning", "poor", "no_data"]
    )


class FinancialHealthBudgetSerializer(serializers.Serializer):
    available = serializers.BooleanField()
    score = serializers.IntegerField(allow_null=True)
    weight = serializers.FloatField()
    total_budget = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_spent = serializers.DecimalField(max_digits=15, decimal_places=2)
    usage_percent = serializers.FloatField(allow_null=True)
    total_budget_categories = serializers.IntegerField()
    over_budget_categories_count = serializers.IntegerField()
    over_budget_rate = serializers.FloatField(allow_null=True)
    status = serializers.ChoiceField(
        choices=["good", "warning", "poor", "no_data"]
    )


class FinancialHealthComponentsSerializer(serializers.Serializer):
    savings = FinancialHealthSavingsSerializer()
    budget = FinancialHealthBudgetSerializer()


class FinancialHealthResultSerializer(serializers.Serializer):
    period = SummaryPeriodSerializer()
    score = serializers.IntegerField(min_value=0, max_value=100)
    level = serializers.ChoiceField(
        choices=["excellent", "good", "fair", "poor", "no_data"]
    )
    label = serializers.CharField()
    components = FinancialHealthComponentsSerializer()


class FinancialHealthResponseSerializer(serializers.Serializer):
    code = serializers.IntegerField(default=1000)
    result = FinancialHealthResultSerializer()


class CashflowPeriodSerializer(serializers.Serializer):
    period = SummaryPeriodSerializer()
    income = serializers.DecimalField(max_digits=15, decimal_places=2)
    expenses = serializers.DecimalField(max_digits=15, decimal_places=2)


class CashflowResultSerializer(serializers.Serializer):
    periods = CashflowPeriodSerializer(many=True)


class CashflowResponseSerializer(serializers.Serializer):
    code = serializers.IntegerField(default=1000)
    result = CashflowResultSerializer()


class BalancePeriodSerializer(serializers.Serializer):
    period = SummaryPeriodSerializer()
    balance = serializers.DecimalField(max_digits=15, decimal_places=2)


class BalanceResultSerializer(serializers.Serializer):
    periods = BalancePeriodSerializer(many=True)


class BalanceResponseSerializer(serializers.Serializer):
    code = serializers.IntegerField(default=1000)
    result = BalanceResultSerializer()


class SpendingByCategoryItemSerializer(serializers.Serializer):
    category = CategorySerializer()
    total_expense = serializers.DecimalField(max_digits=15, decimal_places=2)
    percent = serializers.DecimalField(max_digits=5, decimal_places=2)


class SpendingByCategoryResultSerializer(serializers.Serializer):
    total_spending = serializers.DecimalField(max_digits=15, decimal_places=2)
    categories = SpendingByCategoryItemSerializer(many=True)


class SpendingByCategoryResponseSerializer(serializers.Serializer):
    code = serializers.IntegerField(default=1000)
    result = SpendingByCategoryResultSerializer()


class RecentTransactionsResponseSerializer(serializers.Serializer):
    code = serializers.IntegerField(default=1000)
    result = TransactionResponseSerializer(many=True)
