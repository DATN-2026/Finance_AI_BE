from rest_framework import serializers


class CreateUserSerializer(serializers.Serializer):

    email = serializers.EmailField(max_length=255)
    password = serializers.CharField(max_length=128, write_only=True, min_length=6)
    name = serializers.CharField(max_length=100)


class UpdateUserSerializer(serializers.Serializer):

    email = serializers.EmailField(max_length=255, required=False)
    password = serializers.CharField(
        max_length=128, write_only=True, min_length=6, required=False
    )
    name = serializers.CharField(max_length=100, required=False)
    role = serializers.ChoiceField(choices=["user", "admin"], required=False)
    status = serializers.ChoiceField(choices=["active", "inactive"], required=False)


class UserResponseSerializer(serializers.Serializer):

    id = serializers.UUIDField(read_only=True)
    email = serializers.EmailField()
    name = serializers.CharField()
    role = serializers.CharField()
    status = serializers.CharField()
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class UserListQuerySerializer(serializers.Serializer):
    """Query params for admin user list: search, filter, sort."""

    SORT_BY_CHOICES = [
        "created_at",
        "-created_at",
        "name",
        "-name",
        "email",
        "-email",
    ]

    search = serializers.CharField(required=False, allow_blank=True)
    role = serializers.ChoiceField(choices=["user", "admin"], required=False)
    status = serializers.ChoiceField(choices=["active", "inactive"], required=False)
    sort_by = serializers.ChoiceField(choices=SORT_BY_CHOICES, required=False)


class UserUsageQuerySerializer(serializers.Serializer):
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)

    def validate(self, attrs):
        start_date = attrs.get("start_date")
        end_date = attrs.get("end_date")

        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError("start_date must be before end_date")

        return attrs


class UserUsageSerializer(serializers.Serializer):
    """Usage statistics embedded in user detail responses."""

    total_transactions = serializers.IntegerField()
    total_income_amount = serializers.DecimalField(max_digits=20, decimal_places=2)
    total_expense_amount = serializers.DecimalField(max_digits=20, decimal_places=2)
    total_budgets = serializers.IntegerField()
    total_ai_requests = serializers.IntegerField()


class UserDetailResponseSerializer(serializers.Serializer):
    """Extended user response including usage stats (for retrieve endpoint)."""

    id = serializers.UUIDField(read_only=True)
    email = serializers.EmailField()
    name = serializers.CharField()
    role = serializers.CharField()
    status = serializers.CharField()
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    usage = UserUsageSerializer()


class BulkUpdateStatusSerializer(serializers.Serializer):
    """Input serializer for bulk status update action."""

    user_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1,
    )
    status = serializers.ChoiceField(choices=["active", "inactive"])


class BulkUpdateStatusResponseSerializer(serializers.Serializer):
    """Response serializer for bulk status update action."""

    updated_count = serializers.IntegerField()
