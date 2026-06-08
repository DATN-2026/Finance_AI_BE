from rest_framework import serializers


class AdminDashboardDateRangeQuerySerializer(serializers.Serializer):
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)

    def validate(self, attrs):
        start_date = attrs.get("start_date")
        end_date = attrs.get("end_date")
        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError("start_date must be before end_date")
        return attrs


class AdminDashboardLimitQuerySerializer(AdminDashboardDateRangeQuerySerializer):
    limit = serializers.IntegerField(min_value=1, max_value=100, default=10)


class AdminDashboardMetricSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    active = serializers.IntegerField(required=False)
    inactive = serializers.IntegerField(required=False)
    new_in_range = serializers.IntegerField(required=False)


class AdminDashboardMoneyMetricSerializer(serializers.Serializer):
    income = serializers.DecimalField(max_digits=20, decimal_places=2)
    expenses = serializers.DecimalField(max_digits=20, decimal_places=2)
    active_transaction_count = serializers.IntegerField()
    deleted_transaction_count = serializers.IntegerField()


class AdminDashboardAIRequestMetricSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    success = serializers.IntegerField()
    failed = serializers.IntegerField()
    partial = serializers.IntegerField()
    avg_latency_ms = serializers.FloatField()


class AdminDashboardOverviewSerializer(serializers.Serializer):
    users = AdminDashboardMetricSerializer()
    transactions = AdminDashboardMoneyMetricSerializer()
    ai_requests = AdminDashboardAIRequestMetricSerializer()


class AdminDashboardOverviewResponseSerializer(serializers.Serializer):
    code = serializers.IntegerField(default=1000)
    result = AdminDashboardOverviewSerializer()


class AdminDashboardUserGrowthItemSerializer(serializers.Serializer):
    date = serializers.DateField()
    new_users = serializers.IntegerField()


class AdminDashboardUserGrowthResponseSerializer(serializers.Serializer):
    code = serializers.IntegerField(default=1000)
    result = AdminDashboardUserGrowthItemSerializer(many=True)


class AdminDashboardFinancialTrendItemSerializer(serializers.Serializer):
    date = serializers.DateField()
    income = serializers.DecimalField(max_digits=20, decimal_places=2)
    expenses = serializers.DecimalField(max_digits=20, decimal_places=2)
    transaction_count = serializers.IntegerField()


class AdminDashboardFinancialTrendResponseSerializer(serializers.Serializer):
    code = serializers.IntegerField(default=1000)
    result = AdminDashboardFinancialTrendItemSerializer(many=True)


class AdminDashboardTopUserItemSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    email = serializers.EmailField()
    name = serializers.CharField()
    ai_request_count = serializers.IntegerField()
    transaction_count = serializers.IntegerField()


class AdminDashboardTopUsersResponseSerializer(serializers.Serializer):
    code = serializers.IntegerField(default=1000)
    result = AdminDashboardTopUserItemSerializer(many=True)


class AdminDashboardTopCategoryItemSerializer(serializers.Serializer):
    category_id = serializers.UUIDField()
    category_name = serializers.CharField()
    category_type = serializers.CharField()
    transaction_count = serializers.IntegerField()
    total_amount = serializers.DecimalField(max_digits=20, decimal_places=2)


class AdminDashboardTopCategoriesResponseSerializer(serializers.Serializer):
    code = serializers.IntegerField(default=1000)
    result = AdminDashboardTopCategoryItemSerializer(many=True)
