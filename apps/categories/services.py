from datetime import datetime
from typing import Optional
from django.db import IntegrityError, transaction

from apps.users.models import User
from .models import Category, DefaultCategory
from .selector import (
    get_category_by_id,
    get_category_by_name,
    get_default_category_by_id,
)


ERR_DEFAULT_CATEGORY_NOT_FOUND = "DEFAULT_CATEGORY_NOT_FOUND"
ERR_DEFAULT_CATEGORY_EXISTS = "DEFAULT_CATEGORY_EXISTS"
ERR_USER_NOT_FOUND = "USER_NOT_FOUND"
_UNSET = object()


class CategoryServiceError(Exception):
    """Custom exception for category service errors."""

    def __init__(self, message: str, code: str | None = None):
        super().__init__(message)
        self.code = code


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


def copy_default_categories_to_user(
    user: User,
    default_category_id: str | None = None,
) -> dict:
    defaults = DefaultCategory.objects.filter(is_active=True)
    if default_category_id:
        defaults = defaults.filter(id=default_category_id)

    existing_names = set(Category.objects.filter(user=user).values_list("name", flat=True))
    categories_to_create = []
    skipped_count = 0

    for default in defaults:
        if default.name in existing_names:
            skipped_count += 1
            continue

        categories_to_create.append(
            Category(
                user=user,
                name=default.name,
                type=default.type,
                color=default.color,
                icon=default.icon,
            )
        )
        existing_names.add(default.name)

    created_categories = Category.objects.bulk_create(categories_to_create)
    return {
        "created_count": len(created_categories),
        "skipped_count": skipped_count,
    }


def create_default_category(
    name: str,
    type: str,
    color: Optional[str] = None,
    icon: Optional[str] = None,
    sort_order: int = 0,
    is_active: bool = True,
) -> DefaultCategory:
    try:
        return DefaultCategory.objects.create(
            name=name,
            type=type,
            color=color,
            icon=icon,
            sort_order=sort_order,
            is_active=is_active,
        )
    except IntegrityError as exc:
        raise CategoryServiceError(
            "Default category with this name and type already exists",
            ERR_DEFAULT_CATEGORY_EXISTS,
        ) from exc


def get_default_category(default_category_id: str) -> DefaultCategory:
    default_category = get_default_category_by_id(default_category_id)
    if not default_category:
        raise CategoryServiceError(
            "Default category not found",
            ERR_DEFAULT_CATEGORY_NOT_FOUND,
        )
    return default_category


def update_default_category(
    default_category_id: str,
    name: object = _UNSET,
    type: object = _UNSET,
    color: object = _UNSET,
    icon: object = _UNSET,
    sort_order: object = _UNSET,
    is_active: object = _UNSET,
) -> DefaultCategory:
    default_category = get_default_category(default_category_id)

    if name is not _UNSET:
        default_category.name = name
    if type is not _UNSET:
        default_category.type = type
    if color is not _UNSET:
        default_category.color = color
    if icon is not _UNSET:
        default_category.icon = icon
    if sort_order is not _UNSET:
        default_category.sort_order = sort_order
    if is_active is not _UNSET:
        default_category.is_active = is_active

    try:
        default_category.save()
        return default_category
    except IntegrityError as exc:
        raise CategoryServiceError(
            "Default category with this name and type already exists",
            ERR_DEFAULT_CATEGORY_EXISTS,
        ) from exc


@transaction.atomic
def sync_default_categories(
    scope: str,
    user_id: str | None = None,
    default_category_id: str | None = None,
) -> dict:
    if default_category_id and not get_default_category_by_id(default_category_id):
        raise CategoryServiceError(
            "Default category not found",
            ERR_DEFAULT_CATEGORY_NOT_FOUND,
        )

    if scope == "single_user":
        try:
            users = [User.objects.get(id=user_id)]
        except User.DoesNotExist as exc:
            raise CategoryServiceError("User not found", ERR_USER_NOT_FOUND) from exc
    else:
        users = User.objects.filter(status="active")

    total_created = 0
    total_skipped = 0
    processed_users = 0

    for user in users:
        result = copy_default_categories_to_user(
            user=user,
            default_category_id=default_category_id,
        )
        total_created += result["created_count"]
        total_skipped += result["skipped_count"]
        processed_users += 1

    return {
        "processed_users": processed_users,
        "created_count": total_created,
        "skipped_count": total_skipped,
    }
