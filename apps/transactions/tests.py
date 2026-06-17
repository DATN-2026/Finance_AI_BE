from decimal import Decimal
from unittest.mock import patch

from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.users.models import User

from .services import get_financial_health_score
from .views import FinancialHealthScoreView


class FinancialHealthScoreViewTests(SimpleTestCase):
    @patch("apps.transactions.views.get_financial_health_score")
    def test_passes_selected_month_and_year_to_service(self, health_score_mock):
        health_score_mock.return_value = {
            "period": {"month": 6, "year": 2026},
            "score": 0,
            "level": "no_data",
            "label": "Not enough data",
            "components": {},
        }
        request = APIRequestFactory().get(
            "/api/financial-health-score/",
            {"month": 6, "year": 2026},
        )
        user = User(email="user@example.com", name="User", password="password")
        force_authenticate(request, user=user)

        response = FinancialHealthScoreView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        health_score_mock.assert_called_once_with(user, month=6, year=2026)


class FinancialHealthScoreServiceTests(SimpleTestCase):
    @patch("apps.transactions.services.get_monthly_budget_compliance")
    @patch("apps.transactions.services.get_monthly_budget_totals")
    @patch("apps.transactions.services.get_monthly_transaction_totals")
    def test_calculates_weighted_score(
        self,
        transaction_totals_mock,
        budget_totals_mock,
        budget_compliance_mock,
    ):
        transaction_totals_mock.return_value = {
            "income": Decimal("10000000.00"),
            "expenses": Decimal("8000000.00"),
            "balance": Decimal("2000000.00"),
        }
        budget_totals_mock.return_value = {
            "total_budget": Decimal("9000000.00"),
            "total_spent": Decimal("8000000.00"),
        }
        budget_compliance_mock.return_value = {
            "total_budget_categories": 4,
            "over_budget_categories_count": 1,
        }

        result = get_financial_health_score(object(), month=6, year=2026)

        self.assertEqual(result["score"], 90)
        self.assertEqual(result["level"], "excellent")
        self.assertEqual(result["components"]["savings"]["score"], 100)
        self.assertEqual(result["components"]["savings"]["savings_rate"], 20.0)
        self.assertEqual(result["components"]["budget"]["score"], 75)
        self.assertEqual(result["components"]["budget"]["over_budget_rate"], 25.0)

    @patch("apps.transactions.services.get_monthly_budget_compliance")
    @patch("apps.transactions.services.get_monthly_budget_totals")
    @patch("apps.transactions.services.get_monthly_transaction_totals")
    def test_uses_savings_score_when_user_has_no_budget(
        self,
        transaction_totals_mock,
        budget_totals_mock,
        budget_compliance_mock,
    ):
        transaction_totals_mock.return_value = {
            "income": Decimal("10000000.00"),
            "expenses": Decimal("9000000.00"),
            "balance": Decimal("1000000.00"),
        }
        budget_totals_mock.return_value = {
            "total_budget": Decimal("0.00"),
            "total_spent": Decimal("9000000.00"),
        }
        budget_compliance_mock.return_value = {
            "total_budget_categories": 0,
            "over_budget_categories_count": 0,
        }

        result = get_financial_health_score(object(), month=6, year=2026)

        self.assertEqual(result["score"], 50)
        self.assertEqual(result["level"], "fair")
        self.assertFalse(result["components"]["budget"]["available"])
        self.assertIsNone(result["components"]["budget"]["score"])
        self.assertEqual(result["components"]["budget"]["status"], "no_data")

    @patch("apps.transactions.services.get_monthly_budget_compliance")
    @patch("apps.transactions.services.get_monthly_budget_totals")
    @patch("apps.transactions.services.get_monthly_transaction_totals")
    def test_returns_no_data_when_no_component_can_be_scored(
        self,
        transaction_totals_mock,
        budget_totals_mock,
        budget_compliance_mock,
    ):
        transaction_totals_mock.return_value = {
            "income": Decimal("0.00"),
            "expenses": Decimal("0.00"),
            "balance": Decimal("0.00"),
        }
        budget_totals_mock.return_value = {
            "total_budget": Decimal("0.00"),
            "total_spent": Decimal("0.00"),
        }
        budget_compliance_mock.return_value = {
            "total_budget_categories": 0,
            "over_budget_categories_count": 0,
        }

        result = get_financial_health_score(object(), month=6, year=2026)

        self.assertEqual(result["score"], 0)
        self.assertEqual(result["level"], "no_data")
        self.assertEqual(result["label"], "Not enough data")
        self.assertFalse(result["components"]["savings"]["available"])
        self.assertFalse(result["components"]["budget"]["available"])

    @patch("apps.transactions.services.get_monthly_budget_compliance")
    @patch("apps.transactions.services.get_monthly_budget_totals")
    @patch("apps.transactions.services.get_monthly_transaction_totals")
    def test_scores_savings_as_zero_when_expenses_exist_without_income(
        self,
        transaction_totals_mock,
        budget_totals_mock,
        budget_compliance_mock,
    ):
        transaction_totals_mock.return_value = {
            "income": Decimal("0.00"),
            "expenses": Decimal("1000000.00"),
            "balance": Decimal("-1000000.00"),
        }
        budget_totals_mock.return_value = {
            "total_budget": Decimal("0.00"),
            "total_spent": Decimal("1000000.00"),
        }
        budget_compliance_mock.return_value = {
            "total_budget_categories": 0,
            "over_budget_categories_count": 0,
        }

        result = get_financial_health_score(object(), month=6, year=2026)

        self.assertEqual(result["score"], 0)
        self.assertEqual(result["level"], "poor")
        self.assertTrue(result["components"]["savings"]["available"])
        self.assertEqual(result["components"]["savings"]["score"], 0)
        self.assertIsNone(result["components"]["savings"]["savings_rate"])
