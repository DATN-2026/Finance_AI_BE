from rest_framework import serializers


class LoginRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(max_length=128, write_only=True)


class RefreshRequestSerializer(serializers.Serializer):
    refreshToken = serializers.CharField()


class LogoutRequestSerializer(serializers.Serializer):
    refreshToken = serializers.CharField()


class ForgotPasswordRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()
