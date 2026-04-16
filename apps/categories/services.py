from datetime import datetime
from typing import Optional
from django.db import IntegrityError

from apps.users.models import User
from .models import Category
from .selector import get_category_by_id, get_category_by_name


class CategoryServiceError(Exception):
    """Custom exception for category service errors."""

    pass


def create_category(
    user: User,
    name: str,
    type: str,
    color: Optional[str] = None,
    icon: Optional[str] = None,
) -> Category:

    # Check if there's a soft-deleted category with the same name
    deleted_category = Category.objects.filter(
        user=user, name=name, is_active=False
    ).first()

    if deleted_category:
        # Restore the deleted category
        deleted_category.is_active = True
        deleted_category.type = type
        deleted_category.color = color
        deleted_category.icon = icon
        deleted_category.updated_at = datetime.now()
        deleted_category.save(
            update_fields=["is_active", "type", "color", "icon", "updated_at"]
        )
        return deleted_category

    # Check if category name already exists (active)
    if get_category_by_name(name, user):
        raise CategoryServiceError("Category name already exists")

    # Create new category
    try:
        category = Category.objects.create(
            user=user,
            name=name,
            type=type,
            color=color,
            icon=icon,
        )
        return category
    except IntegrityError as exc:
        raise CategoryServiceError("Failed to create category") from exc


def get_category(category_id: str, user: User) -> Category:

    category = get_category_by_id(category_id, user)
    if not category:
        raise CategoryServiceError("Category not found")
    return category


def update_category(
    category_id: str,
    user: User,
    name: Optional[str] = None,
    type: Optional[str] = None,
    color: Optional[str] = None,
    icon: Optional[str] = None,
) -> Category:

    category = get_category_by_id(category_id, user)
    if not category:
        raise CategoryServiceError("Category not found")

    # Check if new name already exists for this user
    if name and name != category.name:
        # Check active categories
        existing = get_category_by_name(name, user)
        if existing:
            raise CategoryServiceError("Category name already exists")

        # Check soft-deleted categories to avoid conflicts
        deleted_existing = Category.objects.filter(
            user=user, name=name, is_active=False
        ).first()
        if deleted_existing:
            raise CategoryServiceError(
                "Category name already exists (deleted). Please restore it or choose another name."
            )

        category.name = name

    if type:
        category.type = type

    if color is not None:
        category.color = color

    if icon is not None:
        category.icon = icon

    category.updated_at = datetime.now()

    try:
        category.save()
        return category
    except IntegrityError as exc:
        raise CategoryServiceError("Failed to update category") from exc


def delete_category(category_id: str, user: User) -> None:

    category = get_category_by_id(category_id, user)
    if not category:
        raise CategoryServiceError("Category not found")

    category.is_active = False
    category.updated_at = datetime.now()
    category.save(update_fields=["is_active", "updated_at"])
