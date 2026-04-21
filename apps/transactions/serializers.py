from decimal import Decimal

from rest_framework import serializers
from apps.categories.serializers import CategorySerializer


class CreateTransactionSerializer(serializers.Serializer):
    category_id = serializers.UUIDField()
    amount = serializers.DecimalField(
        max_digits=15, decimal_places=2, min_value=Decimal("0.01")
    )
    note = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    transaction_date = serializers.DateField()


class UpdateTransactionSerializer(serializers.Serializer):
    category_id = serializers.UUIDField(required=False)
    amount = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        min_value=Decimal("0.01"),
        required=False,
    )
    note = serializers.CharField(required=False, allow_blank=True, allow_null=True)
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


class TransactionResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    user_id = serializers.UUIDField(source="user.id")
    category = CategorySerializer()
    type = serializers.CharField()
    amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    note = serializers.CharField(allow_null=True, allow_blank=True)
    transaction_date = serializers.DateField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
