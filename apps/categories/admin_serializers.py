from rest_framework import serializers


class OptionalBooleanField(serializers.Field):
    default_error_messages = {"invalid": "Invalid boolean value for is_active"}

    def to_internal_value(self, data):
        if data is None or data == "":
            return None
        if isinstance(data, bool):
            return data
        v = str(data).strip().lower()
        if v in ("true", "1", "t", "yes"):
            return True
        if v in ("false", "0", "f", "no"):
            return False
        self.fail("invalid")

    def to_representation(self, value):
        return value


class DefaultCategoryListQuerySerializer(serializers.Serializer):
    type = serializers.ChoiceField(
        choices=["income", "expense"],
        required=False,
        help_text="Filter by category type. Options: income, expense.",
    )
    is_active = OptionalBooleanField(
        required=False,
        help_text="Filter by active status. Options: true, false. Leave blank to include both.",
    )
    search = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=100,
        help_text="Search by category name. Example: Food.",
    )


class AdminUserCategoryListQuerySerializer(serializers.Serializer):
    user_id = serializers.UUIDField(
        required=False,
        help_text="Filter by user UUID.",
    )
    type = serializers.ChoiceField(
        choices=["income", "expense"],
        required=False,
        help_text="Filter by category type. Options: income, expense.",
    )
    is_active = OptionalBooleanField(
        required=False,
        help_text="Filter by active status. Options: true, false. Leave blank to include both.",
    )
    search = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=100,
        help_text="Search by category name. Example: Food.",
    )


class CreateDefaultCategorySerializer(serializers.Serializer):
    name = serializers.CharField(
        max_length=100,
        help_text="Display name of the default category. Example: Food.",
    )
    type = serializers.ChoiceField(
        choices=["income", "expense"],
        help_text="Category type. Options: income, expense.",
    )
    color = serializers.CharField(
        max_length=100,
        required=False,
        allow_null=True,
        allow_blank=True,
        help_text="Optional UI color. Example: #FF9800.",
    )
    icon = serializers.CharField(
        max_length=100,
        required=False,
        allow_null=True,
        allow_blank=True,
        help_text="Optional UI icon key. Example: utensils.",
    )
    sort_order = serializers.IntegerField(
        min_value=0,
        required=False,
        default=0,
        help_text="Display order. Lower values appear first. Default: 0.",
    )
    is_active = serializers.BooleanField(
        required=False,
        default=True,
        help_text="Whether this default category is copied to new users.",
    )


class UpdateDefaultCategorySerializer(serializers.Serializer):
    name = serializers.CharField(
        max_length=100,
        required=False,
        help_text="New display name. Example: Food & Dining.",
    )
    type = serializers.ChoiceField(
        choices=["income", "expense"],
        required=False,
        help_text="Category type. Options: income, expense.",
    )
    color = serializers.CharField(
        max_length=100,
        required=False,
        allow_null=True,
        allow_blank=True,
        help_text="Optional UI color. Use null to clear it. Example: #FF9800.",
    )
    icon = serializers.CharField(
        max_length=100,
        required=False,
        allow_null=True,
        allow_blank=True,
        help_text="Optional UI icon key. Use null to clear it. Example: utensils.",
    )
    sort_order = serializers.IntegerField(
        min_value=0,
        required=False,
        help_text="Display order. Lower values appear first.",
    )
    is_active = serializers.BooleanField(
        required=False,
        help_text="Set false to stop copying this default category to new users.",
    )


class SyncDefaultCategoriesSerializer(serializers.Serializer):
    scope = serializers.ChoiceField(
        choices=["single_user", "all_users"],
        default="single_user",
        help_text="Sync target. Options: single_user, all_users.",
    )
    user_id = serializers.UUIDField(
        required=False,
        help_text="Required when scope is single_user. Target user UUID.",
    )
    default_category_id = serializers.UUIDField(
        required=False,
        help_text="Optional. If provided, sync only this default category UUID.",
    )

    def validate(self, attrs):
        scope = attrs.get("scope", "single_user")
        user_id = attrs.get("user_id")

        if scope == "single_user" and not user_id:
            raise serializers.ValidationError(
                "user_id is required when scope is single_user"
            )

        if scope == "all_users" and user_id:
            raise serializers.ValidationError(
                "user_id must not be provided when scope is all_users"
            )

        return attrs


class DefaultCategoryResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    type = serializers.CharField()
    color = serializers.CharField(max_length=100, allow_null=True, allow_blank=True)
    icon = serializers.CharField(max_length=100, allow_null=True, allow_blank=True)
    sort_order = serializers.IntegerField()
    is_active = serializers.BooleanField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class AdminUserCategoryResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    user_id = serializers.UUIDField(source="user.id")
    user_email = serializers.EmailField(source="user.email")
    user_name = serializers.CharField(source="user.name")
    name = serializers.CharField()
    type = serializers.CharField()
    color = serializers.CharField(max_length=100, allow_null=True, allow_blank=True)
    icon = serializers.CharField(max_length=100, allow_null=True, allow_blank=True)
    is_active = serializers.BooleanField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class DefaultCategorySuccessResponseSerializer(serializers.Serializer):
    code = serializers.IntegerField(default=1000)
    result = DefaultCategoryResponseSerializer()


class SyncDefaultCategoriesResponseResultSerializer(serializers.Serializer):
    processed_users = serializers.IntegerField()
    created_count = serializers.IntegerField()
    skipped_count = serializers.IntegerField()


class SyncDefaultCategoriesSuccessResponseSerializer(serializers.Serializer):
    code = serializers.IntegerField(default=1000)
    result = SyncDefaultCategoriesResponseResultSerializer()
