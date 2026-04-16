from typing import Any, TypeVar
from rest_framework import serializers
from django.db.models import QuerySet
import math

T = TypeVar("T")


class MetaSerializer(serializers.Serializer):
    """Pagination metadata"""

    limit = serializers.IntegerField()
    offset = serializers.IntegerField()
    total = serializers.IntegerField()
    total_pages = serializers.IntegerField(required=False, allow_null=True)


class PaginatedResponseSerializer(serializers.Serializer):
    """Generic paginated response"""

    items = serializers.ListField()
    meta = MetaSerializer()


class PaginationQuerySerializer(serializers.Serializer):
    """Query parameters for pagination"""

    limit = serializers.IntegerField(default=10, min_value=1, max_value=100)
    offset = serializers.IntegerField(default=0, min_value=0)


class PaginationHelper:
    """Helper class for handling pagination"""

    @staticmethod
    def get_paginated_response_serializer(
        item_serializer: serializers.BaseSerializer | type[serializers.Serializer],
    ) -> type[serializers.Serializer]:
        """
        Build a serializer for paginated API responses in this project format:
        {
            "code": 1000,
            "result": {
                "items": [...],
                "meta": {...}
            }
        }
        """
        if isinstance(item_serializer, type):
            if not issubclass(item_serializer, serializers.Serializer):
                raise TypeError(
                    "item_serializer class must inherit from serializers.Serializer"
                )
            items_field = item_serializer(many=True)
            item_serializer_name = item_serializer.__name__
        elif isinstance(item_serializer, serializers.ListSerializer):
            items_field = item_serializer
            item_serializer_name = item_serializer.child.__class__.__name__
        elif isinstance(item_serializer, serializers.BaseSerializer):
            items_field = item_serializer.__class__(many=True)
            item_serializer_name = item_serializer.__class__.__name__
        else:
            raise TypeError(
                "item_serializer must be a serializer instance or serializer class"
            )

        item_name = (
            item_serializer_name.replace("Serializer", "") or item_serializer_name
        )

        class PaginatedResultSerializer(serializers.Serializer):
            items = items_field
            meta = MetaSerializer()

        class PaginatedSuccessResponseSerializer(serializers.Serializer):
            code = serializers.IntegerField(default=1000)
            result = PaginatedResultSerializer()

        PaginatedResultSerializer.__name__ = f"Paginated{item_name}ResultSerializer"
        PaginatedResultSerializer.__qualname__ = PaginatedResultSerializer.__name__
        PaginatedSuccessResponseSerializer.__name__ = (
            f"Paginated{item_name}SuccessResponseSerializer"
        )
        PaginatedSuccessResponseSerializer.__qualname__ = (
            PaginatedSuccessResponseSerializer.__name__
        )

        return PaginatedSuccessResponseSerializer

    @staticmethod
    def pagination(
        limit: int, offset: int, total_items: int, items: list[Any]
    ) -> dict[str, Any]:
        """
        Create paginated response structure.

        Args:
            limit: Number of items per page
            offset: Starting position
            total_items: Total count of items
            items: List of items for current page

        Returns:
            Dict with items and meta fields
        """
        return {
            "items": items,
            "meta": {
                "limit": limit,
                "offset": offset,
                "total": total_items,
                "total_pages": math.ceil(total_items / limit) if limit > 0 else 0,
            },
        }

    @staticmethod
    def paginate_queryset(
        queryset: QuerySet, limit: int = 10, offset: int = 0
    ) -> dict[str, Any]:
        """
        Paginate a Django queryset.

        Args:
            queryset: Django queryset to paginate
            limit: Number of items per page (default: 10)
            offset: Starting position (default: 0)

        Returns:
            Dict with paginated items and metadata
        """
        total_items = queryset.count()
        items = list(queryset[offset : offset + limit])

        return PaginationHelper.pagination(limit, offset, total_items, items)
