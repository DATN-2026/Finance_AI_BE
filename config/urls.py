"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from apps.transactions.views import (
    BalanceView,
    CashflowView,
    DashboardSummaryView,
    FinancialHealthScoreView,
    RecentTransactionsView,
    SpendingByCategoryView,
)

urlpatterns = [
    path("api/schema/", SpectacularAPIView.as_view(), name="api-schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="api-schema"),
        name="api-docs",
    ),
    path(
        "api/redoc/",
        SpectacularRedocView.as_view(url_name="api-schema"),
        name="api-redoc",
    ),
    path("api/auth/", include("core.authentication.urls")),
    path(
        "api/summary/",
        DashboardSummaryView.as_view(),
        name="dashboard-summary",
    ),
    path("api/cashflow/", CashflowView.as_view(), name="cashflow"),
    path(
        "api/financial-health-score/",
        FinancialHealthScoreView.as_view(),
        name="financial-health-score",
    ),
    path(
        "api/spending-by-category/",
        SpendingByCategoryView.as_view(),
        name="spending-by-category",
    ),
    path(
        "api/recent-transactions/",
        RecentTransactionsView.as_view(),
        name="recent-transactions",
    ),
    path("api/balance/", BalanceView.as_view(), name="balance"),
    path("api/users/", include("apps.users.urls")),
    path("api/categories/", include("apps.categories.urls")),
    path("api/admin/categories/", include("apps.categories.admin_urls")),
    path("api/transactions/", include("apps.transactions.urls")),
    path("api/budgets/", include("apps.budgets.urls")),
    path("api/chats/", include("apps.chats.urls")),
    path("api/admin/dashboard/", include("apps.admin_dashboard.urls")),
]
