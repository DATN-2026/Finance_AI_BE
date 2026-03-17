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
    """
    Serializer for user response data.
    """

    id = serializers.UUIDField(read_only=True)
    email = serializers.EmailField()
    name = serializers.CharField()
    role = serializers.CharField()
    status = serializers.CharField()
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
