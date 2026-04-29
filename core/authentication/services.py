from datetime import datetime

from django.contrib.auth.hashers import check_password, make_password
from django.db import IntegrityError

from apps.users.models import User
from .models import InvalidatedToken

from .jwt_provider import (
    JwtError,
    create_access_token,
    create_refresh_token,
    validate_refresh_token,
)
from .utils import generate_password
from .tasks import send_email_task


class AuthServiceError(Exception):
    pass


def _is_invalidated(jti: str) -> bool:
    return InvalidatedToken.objects.filter(id=jti).exists()


def _build_scope(user: User) -> str:
    # Placeholder scope mapping; you can enrich this with permission table later.
    if user.role == "admin":
        return "ROLE_ADMIN"
    return "ROLE_USER"


def verify(user: User, raw_password: str) -> bool:
    stored_password = user.password or ""
    return check_password(raw_password, stored_password)


def login(email: str, password: str) -> dict:
    try:
        user = User.objects.get(email=email.lower())
    except User.DoesNotExist as exc:
        raise AuthServiceError("Invalid email or password") from exc

    if user.status != "active":
        raise AuthServiceError("User is inactive")

    if not verify(user, password):
        raise AuthServiceError("Invalid email or password")

    scope = _build_scope(user)
    access_token = create_access_token(subject=user.email, scope=scope)
    refresh_token = create_refresh_token(subject=user.email)

    return {
        "authenticated": True,
        "accessToken": access_token,
        "refreshToken": refresh_token,
        "user": user,
    }


def refresh(refresh_token: str) -> dict:
    try:
        payload = validate_refresh_token(refresh_token)
    except JwtError as exc:
        raise AuthServiceError(str(exc)) from exc

    subject = payload.get("sub")
    token_jti = payload.get("jti")

    if not subject:
        raise AuthServiceError("Invalid refresh token")

    if not token_jti:
        raise AuthServiceError("Invalid refresh token")

    if _is_invalidated(token_jti):
        raise AuthServiceError("Refresh token has been invalidated")

    try:
        user = User.objects.get(email=subject.lower())
    except User.DoesNotExist as exc:
        raise AuthServiceError("User not found") from exc

    if user.status != "active":
        raise AuthServiceError("User is inactive")

    scope = _build_scope(user)
    return {
        "authenticated": True,
        "accessToken": create_access_token(subject=user.email, scope=scope),
        "refreshToken": create_refresh_token(subject=user.email),
    }


def logout(refresh_token: str) -> None:
    try:
        payload = validate_refresh_token(refresh_token)
    except JwtError as exc:
        raise AuthServiceError(str(exc)) from exc

    token_jti = payload.get("jti")
    token_exp = payload.get("exp")

    if not token_jti or not isinstance(token_exp, int):
        raise AuthServiceError("Invalid refresh token")

    expiry_time = datetime.fromtimestamp(token_exp)

    try:
        InvalidatedToken.objects.create(id=token_jti, expiryTime=expiry_time)
    except IntegrityError:
        # Idempotent logout: token already invalidated
        return


def reset_password(email: str) -> None:
    try:
        user = User.objects.get(email=email.lower())
    except User.DoesNotExist as exc:
        raise AuthServiceError("Invalid credentials") from exc

    if user.status != "active":
        raise AuthServiceError("User is inactive")

    new_password = generate_password(8)

    # Prepare email content (simple inline template)
    subject = "Your new password"
    body = f"Hi {getattr(user, 'full_name', user.email)},\n\nYour new password is: {new_password}\nPlease change it after login."
    html = f"<p>Hi {getattr(user, 'full_name', user.email)},</p><p>Your new password is: <b>{new_password}</b></p><p>Please change it after login.</p>"

    # Enqueue sending email (non-blocking). send_email_task exposes .delay() even if Celery absent.
    try:
        send_email_task.delay(
            to_address=user.email, subject=subject, body=body, html=html
        )
    except Exception:
        # if queue fails, continue to update password (do not block)
        pass

    user.password = make_password(new_password)
    user.updated_at = datetime.now()
    user.save(update_fields=["password", "updated_at"])
