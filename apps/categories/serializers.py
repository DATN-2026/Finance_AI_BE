from rest_framework import serializers


class CreateCategorySerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    type = serializers.ChoiceField(choices=["income", "expense"])
    color = serializers.CharField(
        max_length=100, required=False, allow_null=True, allow_blank=True
    )
    icon = serializers.CharField(
        max_length=100, required=False, allow_null=True, allow_blank=True
    )


class UpdateCategorySerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100, required=False)
    type = serializers.ChoiceField(choices=["income", "expense"], required=False)
    color = serializers.CharField(
        max_length=100, required=False, allow_null=True, allow_blank=True
    )
    icon = serializers.CharField(
        max_length=100, required=False, allow_null=True, allow_blank=True
    )


class CategoryListQuerySerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=["income", "expense"], required=False)
    month = serializers.IntegerField(min_value=1, max_value=12, required=False)
    year = serializers.IntegerField(min_value=2000, max_value=2100, required=False)

    def validate(self, attrs):
        month = attrs.get("month")
        year = attrs.get("year")

        if (month is None) != (year is None):
            raise serializers.ValidationError(
                "month and year must be provided together"
            )

        return attrs


class CategorySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    type = serializers.CharField()
    color = serializers.CharField(max_length=100)
    icon = serializers.CharField(max_length=100)


class CategoryResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    user_id = serializers.UUIDField(source="user.id")
    name = serializers.CharField()
    type = serializers.CharField()
    color = serializers.CharField(max_length=100, allow_null=True, allow_blank=True)
    icon = serializers.CharField(max_length=100, allow_null=True, allow_blank=True)
    is_active = serializers.BooleanField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class CategoryListResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    user_id = serializers.UUIDField(source="user.id")
    name = serializers.CharField()
    type = serializers.CharField()
    color = serializers.CharField(max_length=100, allow_null=True, allow_blank=True)
    icon = serializers.CharField(max_length=100, allow_null=True, allow_blank=True)
    is_active = serializers.BooleanField()
    transactions_count = serializers.IntegerField(read_only=True, default=0)
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
