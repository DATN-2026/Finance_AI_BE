from datetime import datetime
from typing import Optional

from django.contrib.auth.hashers import make_password
from django.db import IntegrityError

from .models import User
from .selector import get_user_by_email, get_user_by_id

ERR_USER_NOT_FOUND = "USER_NOT_FOUND"
ERR_EMAIL_EXISTS = "EMAIL_EXISTS"
ERR_FORBIDDEN_ROLE_STATUS_UPDATE = "FORBIDDEN_ROLE_STATUS_UPDATE"
ERR_FORBIDDEN_SELF_DEACTIVATE = "FORBIDDEN_SELF_DEACTIVATE"
ERR_FORBIDDEN_SELF_DEMOTE = "FORBIDDEN_SELF_DEMOTE"
ERR_NO_VALID_TARGET_USERS = "NO_VALID_TARGET_USERS"
ERR_CREATE_FAILED = "CREATE_FAILED"
ERR_UPDATE_FAILED = "UPDATE_FAILED"


class UserServiceError(Exception):
    """Custom exception for user service errors."""

    def __init__(self, message: str, code: str):
        super().__init__(message)
        self.code = code


def create_user(email: str, password: str, name: str) -> User:
    """Create a new user."""
    if get_user_by_email(email):
        raise UserServiceError("Email already exists", ERR_EMAIL_EXISTS)

    try:
        return User.objects.create(
            email=email.lower(),
            password=make_password(password),
            name=name,
        )
    except IntegrityError as exc:
        raise UserServiceError("Failed to create user", ERR_CREATE_FAILED) from exc


def get_user(user_id: str) -> User:
    """Get a user by their ID."""
    user = get_user_by_id(user_id)
    if not user:
        raise UserServiceError("User not found", ERR_USER_NOT_FOUND)
    return user


def update_user(
    user_id: str,
    email: Optional[str] = None,
    password: Optional[str] = None,
    name: Optional[str] = None,
    role: Optional[str] = None,
    status: Optional[str] = None,
    requesting_user: Optional[User] = None,
    can_manage_role_status: bool = False,
) -> User:
    """Update an existing user."""
    user = get_user_by_id(user_id)
    if not user:
        raise UserServiceError("User not found", ERR_USER_NOT_FOUND)

    if requesting_user and not can_manage_role_status and (
        role is not None or status is not None
    ):
        raise UserServiceError(
            "Only admin can update role or status.",
            ERR_FORBIDDEN_ROLE_STATUS_UPDATE,
        )

    if requesting_user and str(requesting_user.id) == str(user.id):
        if status == "inactive":
            raise UserServiceError(
                "You cannot deactivate your own account.",
                ERR_FORBIDDEN_SELF_DEACTIVATE,
            )
        if role == "user":
            raise UserServiceError(
                "You cannot demote your own role.",
                ERR_FORBIDDEN_SELF_DEMOTE,
            )

    if email and email.lower() != user.email:
        existing_user = get_user_by_email(email)
        if existing_user:
            raise UserServiceError("Email already exists", ERR_EMAIL_EXISTS)
        user.email = email.lower()

    if password:
        user.password = make_password(password)

    if name:
        user.name = name

    if role:
        user.role = role

    if status:
        user.status = status

    user.updated_at = datetime.now()

    try:
        user.save()
        return user
    except IntegrityError as exc:
        raise UserServiceError("Failed to update user", ERR_UPDATE_FAILED) from exc


def delete_user(user_id: str, requesting_user: Optional[User] = None) -> None:
    """Soft delete a user by setting status = inactive."""
    user = get_user_by_id(user_id)
    if not user:
        raise UserServiceError("User not found", ERR_USER_NOT_FOUND)

    if requesting_user and str(requesting_user.id) == str(user.id):
        raise UserServiceError(
            "You cannot deactivate your own account.",
            ERR_FORBIDDEN_SELF_DEACTIVATE,
        )

    user.status = "inactive"
    user.updated_at = datetime.now()
    user.save(update_fields=["status", "updated_at"])


def bulk_update_user_status(
    user_ids: list[str],
    status: str,
    requesting_user: User,
) -> dict:
    """Bulk update status for multiple users."""
    safe_ids = [str(uid) for uid in user_ids]

    if status == "inactive":
        own_id = str(requesting_user.id)
        safe_ids = [uid for uid in safe_ids if uid != own_id]

    if not safe_ids:
        raise UserServiceError(
            "No valid users to update after guard checks.",
            ERR_NO_VALID_TARGET_USERS,
        )

    updated_count = User.objects.filter(id__in=safe_ids).update(
        status=status,
        updated_at=datetime.now(),
    )

    return {"updated_count": updated_count}
