import uuid
from datetime import date, timedelta

from django.test import TestCase
from django.utils import timezone

from apps.catalog.models import Season
from apps.common.testing import client_for, make_business, make_variant, put_stock
from apps.insights.engine import compute_insights
from apps.insights.seasons import season_state
from apps.inventory.models import StockMovement
from apps.sales.models import Sale


def backdate_stock(variant, days):
    StockMovement.objects.filter(variant=variant).update(created_at=timezone.now() - timedelta(days=days))


class SeasonStateTests(TestCase):
    def test_wraparound_winter(self):
        s = season_state(12, 2, date(2027, 1, 10))
        self.assertTrue(s.in_season)
        self.assertEqual(s.days_to_end, (date(2027, 2, 28) - date(2027, 1, 10)).days)
        s = season_state(12, 2, date(2026, 12, 5))
        self.assertEqual(s.days_to_end, (date(2027, 2, 28) - date(2026, 12, 5)).days)
        s = season_state(12, 2, date(2026, 7, 1))
        self.assertFalse(s.in_season)
        self.assertEqual(s.days_to_start, (date(2026, 12, 1) - date(2026, 7, 1)).days)


class RiskRuleTests(TestCase):
    def setUp(self):
        self.business, (self.branch,), self.owner, _ = make_business()
        self.c = client_for(self.owner)

    def sell(self, variant, qty, days_ago):
        r = self.c.post("/api/sales/", {"idempotency_key": str(uuid.uuid4()), "branch": self.branch.id,
                                        "lines": [{"variant": variant.id, "quantity": qty}]}, format="json")
        assert r.status_code == 201, r.data
        Sale.objects.filter(pk=r.data["id"]).update(created_at=timezone.now() - timedelta(days=days_ago))

    def risks(self, variant, today=None):
        items = [i for i in compute_insights(self.business, [self.branch], today=today) if i.variant == variant.id]
        return {r.type: r for r in items[0].risks} if items else {}

    def test_no_sale_for_long_time_is_flagged_with_reason(self):
        v = make_variant(self.business)
        put_stock(self.branch, v, 10)
        self.sell(v, 1, days_ago=45)
        risk = self.risks(v)["no_sale"]
        self.assertEqual(risk.level, "medium")
        self.assertIn("45 kun", risk.reason)
        self.assertIn("30 kun", risk.reason)

    def test_never_sold_uses_arrival_date(self):
        v = make_variant(self.business)
        put_stock(self.branch, v, 4)
        backdate_stock(v, 70)
        risk = self.risks(v)["no_sale"]
        self.assertEqual(risk.level, "high")
        self.assertIn("bir marta ham sotilmadi", risk.reason)

    def test_fresh_stock_is_not_flagged(self):
        v = make_variant(self.business)
        put_stock(self.branch, v, 4)
        self.assertEqual(self.risks(v), {})

    def test_threshold_is_configurable(self):
        v = make_variant(self.business)
        put_stock(self.branch, v, 10)
        self.sell(v, 1, days_ago=20)
        self.assertNotIn("no_sale", self.risks(v))
        r = self.c.patch("/api/insights/settings/", {"no_sale_days": 14}, format="json")
        self.assertEqual(r.status_code, 200, r.data)
        self.assertIn("no_sale", self.risks(v))

    def test_overstock_needs_enough_sales_data(self):
        v = make_variant(self.business)
        put_stock(self.branch, v, 200)
        self.sell(v, 1, days_ago=2)
        self.assertNotIn("overstock", self.risks(v))  # 1 ta sotuv: sur'at hisoblanmaydi
        self.sell(v, 3, days_ago=1)
        risk = self.risks(v)["overstock"]
        self.assertIn("kunga yetadi", risk.reason)

    def test_restock_suggests_other_branch(self):
        from apps.accounts.models import Branch

        other = Branch.objects.create(business=self.business, name="Ombor")
        v = make_variant(self.business)
        v.min_stock = 2
        v.save()
        put_stock(self.branch, v, 3)
        put_stock(other, v, 20)
        self.sell(v, 2, days_ago=1)
        items = [i for i in compute_insights(self.business, [self.branch, other]) if i.branch == self.branch.id]
        restock = {r.type: r for r in items[0].risks}["restock"]
        self.assertIn("Ombor", restock.action)

    def test_seasonal_risk_near_season_end(self):
        v = make_variant(self.business)
        today = timezone.localdate()
        end_month = today.month
        start_month = (today.month - 2) % 12 + 1
        season = Season.objects.create(business=self.business, name="Test mavsum", start_month=start_month,
                                       end_month=end_month)
        v.product.season = season
        v.product.save()
        put_stock(self.branch, v, 30)
        state = season_state(start_month, end_month, today)
        risks = self.risks(v)
        if state.days_to_end <= 21:
            self.assertIn("seasonal", risks)
            self.assertIn("Test mavsum", risks["seasonal"].reason)
        else:
            self.assertNotIn("seasonal", risks)

    def test_api_returns_explanations_and_respects_tenant(self):
        v = make_variant(self.business)
        put_stock(self.branch, v, 4)
        backdate_stock(v, 70)
        r = self.c.get("/api/insights/risks/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 1)
        self.assertTrue(r.data["results"][0]["risks"][0]["reason"])
        _, _, stranger, _ = make_business()
        self.assertEqual(client_for(stranger).get("/api/insights/risks/").data["count"], 0)
