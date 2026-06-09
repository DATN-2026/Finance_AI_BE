from django.urls import path

from .views import (
    AdminDashboardFinancialTrendView,
    AdminDashboardOverviewView,
    AdminDashboardTopCategoriesView,
    AdminDashboardTopUsersView,
    AdminDashboardUserGrowthView,
)

urlpatterns = [
    path("overview/", AdminDashboardOverviewView.as_view(), name="admin-dashboard-overview"),
    path(
        "user-growth/",
        AdminDashboardUserGrowthView.as_view(),
        name="admin-dashboard-user-growth",
    ),
    path(
        "financial-trend/",
        AdminDashboardFinancialTrendView.as_view(),
        name="admin-dashboard-financial-trend",
    ),
    path("top-users/", AdminDashboardTopUsersView.as_view(), name="admin-dashboard-top-users"),
    path(
        "top-categories/",
        AdminDashboardTopCategoriesView.as_view(),
        name="admin-dashboard-top-categories",
    ),
]
