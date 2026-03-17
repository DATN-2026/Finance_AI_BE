from uuid import UUID
from rest_framework.authentication import BaseAuthentication
from rest_framework.permissions import BasePermission
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.request import Request

from apps.users.models import User
from .jwt_provider import JwtError, decode_jwt


class JwtAuthentication(BaseAuthentication):
    """
    JWT authentication class for protected endpoints.
    Validates access token from Authorization header.
    """

    def authenticate(self, request: Request):
        auth_header = request.headers.get("Authorization", "")

        if not auth_header.startswith("Bearer "):
            return None

        token = auth_header[7:]  # Remove "Bearer " prefix

        if not token:
            return None

        try:
            payload = decode_jwt(token)
        except JwtError as exc:
            raise AuthenticationFailed(str(exc))

        # Verify token type (should be access token, not refresh)
        if payload.get("typ") == "refresh":
            raise AuthenticationFailed("Invalid token type")

        email = payload.get("sub")
        if not email:
            raise AuthenticationFailed("Invalid token")

        try:
            user = User.objects.get(email=email.lower())
        except User.DoesNotExist:
            raise AuthenticationFailed("User not found")

        if user.status != "active":
            raise AuthenticationFailed("User account is not active")

        # Return (user, auth) tuple
        # We can store payload as auth for later use
        return (user, payload)


class IsAuthenticated(BasePermission):
    """
    Permission class that requires authentication.
    """

    def has_permission(self, request: Request, view):
        return request.user and isinstance(request.user, User)


class IsAdmin(BasePermission):
    """
    Permission class that only allows admin users (scope="ROLE_ADMIN").
    """

    def has_permission(self, request: Request, view):
        # First check if user is authenticated
        if not request.user or not isinstance(request.user, User):
            return False

        # Get the scope from JWT auth (stored in request.auth by JwtAuthentication)
        scope = request.auth.get("scope") if request.auth else None

        # Only admin has access
        return scope == "ROLE_ADMIN"


class IsAdminOrOwner(BasePermission):
    """
    Permission class that allows:
    - Admins (scope="ROLE_ADMIN") can access any resource
    - Regular users can only access their own resources (user_id must match)
    """

    def has_permission(self, request: Request, view):
        # First check if user is authenticated
        if not request.user or not isinstance(request.user, User):
            return False

        # Get the scope from JWT auth (stored in request.auth by JwtAuthentication)
        scope = request.auth.get("scope") if request.auth else None

        # Admin has full access
        if scope == "ROLE_ADMIN":
            return True

        # For non-admin users, check if they're accessing their own resource
        # Get user_id from URL kwargs
        user_id = view.kwargs.get("user_id")
        if not user_id:
            return False

        # Normalize both UUIDs to the same format for comparison
        try:
            user_uuid = UUID(str(request.user.id))
            url_uuid = UUID(user_id)
            return user_uuid == url_uuid
        except (ValueError, AttributeError):
            return False
