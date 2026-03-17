from django.urls import path

from .views import (
    CreateUserView,
    DeleteUserView,
    GetUserView,
    GetCurrentUserView,
    ListUsersView,
    UpdateUserView,
)

urlpatterns = [
    path("", CreateUserView.as_view(), name="user-create"),
    path("list/", ListUsersView.as_view(), name="user-list"),
    path("me/", GetCurrentUserView.as_view(), name="user-me"),
    path("<str:user_id>/", GetUserView.as_view(), name="user-get"),
    path("<str:user_id>/update/", UpdateUserView.as_view(), name="user-update"),
    path("<str:user_id>/delete/", DeleteUserView.as_view(), name="user-delete"),
]
