from rest_framework import serializers
from apps.users.serializers import UserResponseSerializer


class LoginRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(max_length=128, write_only=True)


class LoginResponseSerializer(serializers.Serializer):
    authenticated = serializers.BooleanField()
    accessToken = serializers.CharField()
    refreshToken = serializers.CharField()
    user = UserResponseSerializer()


class RefreshRequestSerializer(serializers.Serializer):
    refreshToken = serializers.CharField(required=False, allow_blank=True)


class RefreshResponseSerializer(serializers.Serializer):
    authenticated = serializers.BooleanField()
    accessToken = serializers.CharField()
    refreshToken = serializers.CharField()


class LogoutRequestSerializer(serializers.Serializer):
    refreshToken = serializers.CharField(required=False, allow_blank=True)


class LogoutResponseSerializer(serializers.Serializer):
    loggedOut = serializers.BooleanField()


class ForgotPasswordRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ForgotPasswordResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
