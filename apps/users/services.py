from datetime import datetime
from typing import Optional

from django.contrib.auth.hashers import make_password
from django.db import IntegrityError

from .models import User
from .selector import get_user_by_email, get_user_by_id


class UserServiceError(Exception):
    """Custom exception for user service errors."""

    pass


def create_user(email: str, password: str, name: str) -> User:
    """
    Create a new user.
    Default role is "user" and status is "active" (from model defaults).

    Args:
        email: User's email address
        password: Plain text password (will be hashed)
        name: User's full name

    Returns:
        Created User instance

    Raises:
        UserServiceError: If email already exists or other errors occur
    """
    # Check if email already exists
    if get_user_by_email(email):
        raise UserServiceError("Email already exists")

    try:
        user = User.objects.create(
            email=email.lower(),
            password=make_password(password),
            name=name,
            # role and status will use model defaults
        )
        return user
    except IntegrityError as exc:
        raise UserServiceError("Failed to create user") from exc


def get_user(user_id: str) -> User:
    """
    Get a user by their ID.

    Args:
        user_id: User's UUID

    Returns:
        User instance

    Raises:
        UserServiceError: If user does not exist
    """
    user = get_user_by_id(user_id)
    if not user:
        raise UserServiceError("User not found")
    return user


def update_user(
    user_id: str,
    email: Optional[str] = None,
    password: Optional[str] = None,
    name: Optional[str] = None,
    role: Optional[str] = None,
    status: Optional[str] = None,
) -> User:
    """
    Update an existing user.

    Args:
        user_id: User's UUID
        email: New email (optional)
        password: New password (optional, will be hashed)
        name: New name (optional)
        role: New role (optional, "user" or "admin")
        status: New status (optional, "active" or "inactive")

    Returns:
        Updated User instance

    Raises:
        UserServiceError: If user does not exist or email already taken
    """
    user = get_user_by_id(user_id)
    if not user:
        raise UserServiceError("User not found")

    # Check if email is being changed and if it's already taken
    if email and email.lower() != user.email:
        existing_user = get_user_by_email(email)
        if existing_user:
            raise UserServiceError("Email already exists")
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
        raise UserServiceError("Failed to update user") from exc


def delete_user(user_id: str) -> None:
    """
    Soft delete a user by setting status = "inactive".
    Preserves user data and associated transactions/budgets/categories for audit.

    Args:
        user_id: User's UUID

    Raises:
        UserServiceError: If user does not exist
    """
    user = get_user_by_id(user_id)
    if not user:
        raise UserServiceError("User not found")

    user.status = "inactive"
    user.updated_at = datetime.now()
    user.save(update_fields=["status", "updated_at"])


def list_users():
    """
    Get all users.

    Returns:
        QuerySet of all users
    """
    from .selector import list_all_users

    return list_all_users()
