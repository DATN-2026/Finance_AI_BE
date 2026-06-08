from django.urls import path

from .admin_views import (
    AdminDefaultCategoryDetailView,
    AdminDefaultCategoryListCreateView,
    AdminDefaultCategorySyncView,
    AdminUserCategoryListView,
)

urlpatterns = [
    path(
        "defaults/",
        AdminDefaultCategoryListCreateView.as_view(),
        name="admin-default-categories",
    ),
    path(
        "defaults/sync/",
        AdminDefaultCategorySyncView.as_view(),
        name="admin-default-categories-sync",
    ),
    path(
        "defaults/<uuid:default_category_id>/",
        AdminDefaultCategoryDetailView.as_view(),
        name="admin-default-category-detail",
    ),
    path(
        "user-categories/",
        AdminUserCategoryListView.as_view(),
        name="admin-user-categories",
    ),
]
