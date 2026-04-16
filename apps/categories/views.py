from datetime import date

from rest_framework import status, viewsets
from rest_framework.request import Request
from drf_spectacular.utils import OpenApiParameter, extend_schema

from core.untils.api_response import error_response, success_response
from core.untils.pagination import PaginationHelper, PaginationQuerySerializer
from core.authentication.permissions import IsAuthenticated, JwtAuthentication

from .serializers import (
    CreateCategorySerializer,
    UpdateCategorySerializer,
    CategoryResponseSerializer,
    CategoryListQuerySerializer,
    CategoryListResponseSerializer,
)
from .services import (
    CategoryServiceError,
    create_category,
    get_category,
    update_category,
    delete_category,
)
from .selector import list_user_categories


class CategoryViewSet(viewsets.ViewSet):

    authentication_classes = [JwtAuthentication]
    permission_classes = [IsAuthenticated]
    lookup_url_kwarg = "category_id"

    @extend_schema(
        summary="List user categories",
        description="Endpoint to list categories for the authenticated user with optional filtering by type (income or expense)",
        parameters=[
            OpenApiParameter(
                name="type",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filter by type: income or expense",
                required=False,
            ),
            OpenApiParameter(
                name="month",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Month (1-12). Must be used together with year",
                required=False,
            ),
            OpenApiParameter(
                name="year",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Year (e.g. 2026). Must be used together with month",
                required=False,
            ),
            OpenApiParameter(
                name="limit",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Number of items per page (default: 10, max: 100)",
                required=False,
            ),
            OpenApiParameter(
                name="offset",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Starting position (default: 0)",
                required=False,
            ),
        ],
        responses={
            200: PaginationHelper.get_paginated_response_serializer(
                CategoryListResponseSerializer(many=True)
            )
        },
        tags=["Categories"],
    )
    def list(self, request: Request):
        pagination_serializer = PaginationQuerySerializer(data=request.query_params)
        if not pagination_serializer.is_valid():
            return error_response(
                code=3001,
                message="Invalid pagination parameters",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        query_serializer = CategoryListQuerySerializer(data=request.query_params)
        if not query_serializer.is_valid():
            return error_response(
                code=3001,
                message="Invalid query parameters",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        limit = pagination_serializer.validated_data["limit"]
        offset = pagination_serializer.validated_data["offset"]

        category_type = query_serializer.validated_data.get("type")

        today = date.today()
        month = query_serializer.validated_data.get("month", today.month)
        year = query_serializer.validated_data.get("year", today.year)

        categories_queryset = list_user_categories(
            request.user,
            type=category_type,
            month=month,
            year=year,
        )

        paginated_result = PaginationHelper.paginate_queryset(
            categories_queryset, limit=limit, offset=offset
        )

        response_serializer = CategoryListResponseSerializer(
            paginated_result["items"], many=True
        )
        paginated_result["items"] = response_serializer.data

        return success_response(
            result=paginated_result, code=1000, status_code=status.HTTP_200_OK
        )

    @extend_schema(
        summary="Create a new category",
        description="Endpoint to create a new category for the authenticated user.",
        request=CreateCategorySerializer,
        responses={201: CategoryResponseSerializer},
        tags=["Categories"],
    )
    def create(self, request: Request):
        serializer = CreateCategorySerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                code=3001,
                message="Invalid request data",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        try:
            category = create_category(
                user=request.user,
                name=serializer.validated_data["name"],
                type=serializer.validated_data["type"],
                color=serializer.validated_data.get("color"),
                icon=serializer.validated_data.get("icon"),
            )
        except CategoryServiceError as exc:
            return error_response(
                code=3002, message=str(exc), status_code=status.HTTP_400_BAD_REQUEST
            )

        response_serializer = CategoryResponseSerializer(category)
        return success_response(
            result=response_serializer.data,
            code=1000,
            status_code=status.HTTP_201_CREATED,
        )

    @extend_schema(
        summary="Retrieve category details",
        description="Endpoint to retrieve details of a specific category for the authenticated user.",
        parameters=[
            OpenApiParameter(
                name="category_id",
                type=str,
                location=OpenApiParameter.PATH,
                description="Category ID",
                required=True,
            ),
        ],
        responses={200: CategoryResponseSerializer},
        tags=["Categories"],
    )
    def retrieve(self, request: Request, category_id: str):
        try:
            category = get_category(category_id, request.user)
        except CategoryServiceError as exc:
            return error_response(
                code=3003, message=str(exc), status_code=status.HTTP_404_NOT_FOUND
            )

        response_serializer = CategoryResponseSerializer(category)
        return success_response(
            result=response_serializer.data, code=1000, status_code=status.HTTP_200_OK
        )

    @extend_schema(
        summary="Update category details",
        description="Endpoint to update details of a specific category for the authenticated user.",
        parameters=[
            OpenApiParameter(
                name="category_id",
                type=str,
                location=OpenApiParameter.PATH,
                description="Category ID",
                required=True,
            ),
        ],
        request=UpdateCategorySerializer,
        responses={200: CategoryResponseSerializer},
        tags=["Categories"],
    )
    def update(self, request: Request, category_id: str):
        serializer = UpdateCategorySerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                code=3001,
                message="Invalid request data",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        try:
            category = update_category(
                category_id=category_id,
                user=request.user,
                name=serializer.validated_data.get("name"),
                type=serializer.validated_data.get("type"),
                color=serializer.validated_data.get("color"),
                icon=serializer.validated_data.get("icon"),
            )
        except CategoryServiceError as exc:
            return error_response(
                code=3004, message=str(exc), status_code=status.HTTP_400_BAD_REQUEST
            )

        response_serializer = CategoryResponseSerializer(category)
        return success_response(
            result=response_serializer.data, code=1000, status_code=status.HTTP_200_OK
        )

    @extend_schema(
        summary="Delete a category",
        description="Endpoint to delete a specific category for the authenticated user.",
        parameters=[
            OpenApiParameter(
                name="category_id",
                type=str,
                location=OpenApiParameter.PATH,
                description="Category ID",
                required=True,
            ),
        ],
        responses={200: None},
        tags=["Categories"],
    )
    def destroy(self, request: Request, category_id: str):
        try:
            delete_category(category_id, request.user)
        except CategoryServiceError as exc:
            return error_response(
                code=3005, message=str(exc), status_code=status.HTTP_404_NOT_FOUND
            )

        return success_response(
            result={"deleted": True}, code=1000, status_code=status.HTTP_200_OK
        )
