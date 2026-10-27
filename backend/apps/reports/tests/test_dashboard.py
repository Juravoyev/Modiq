import uuid
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import Membership
from apps.common.testing import client_for, make_business, make_member, make_variant, put_stock
from apps.sales.models import Sale


class DashboardTests(TestCase):
    def setUp(self):
        self.business, (self.branch,), self.owner, _ = make_business()
        self.v = make_variant(self.business, purchase="40000", sale="100000")
        self.v.min_stock = 3
        self.v.save()
        put_stock(self.branch, self.v, 10)
        self.c = client_for(self.owner)

    def sell(self, qty, discount="0"):
        r = self.c.post("/api/sales/", {"idempotency_key": str(uuid.uuid4()), "branch": self.branch.id,
                                        "lines": [{"variant": self.v.id, "quantity": qty, "discount_amount": discount}]},
                        format="json")
        assert r.status_code == 201, r.data
        return r.data

    def test_numbers_match_real_sales_and_returns(self):
        self.sell(2, discount="20000")  # 180 000, tannarx 80 000
        sale = self.sell(1)  # 100 000, tannarx 40 000
        old = self.sell(1)
        Sale.objects.filter(pk=old["id"]).update(created_at=timezone.now() - timedelta(days=3))  # bugun emas
        self.c.post(f"/api/sales/{sale['id']}/return/", {"lines": [{"sale_line": sale["lines"][0]["id"], "quantity": 1}]},
                    format="json")
        d = self.c.get("/api/reports/dashboard/").data
        self.assertEqual(d["sales_count"], 2)
        self.assertEqual(d["items_sold"], 3)
        self.assertEqual(d["revenue"], "180000.00")  # 280 000 − 100 000 qaytarilgan
        self.assertEqual(d["gross_profit"], "100000.00")  # (280 000 − 120 000) − (100 000 − 40 000)
        self.assertEqual(d["stock_units"], 7)  # 10 − 4 sotilgan + 1 qaytgan
        self.assertEqual(d["stock_value"], "280000.00")
        self.assertIn("revenue", d["formulas"])

    def test_cashier_does_not_see_profit(self):
        cashier, _ = make_member(self.business, Membership.Role.CASHIER, [self.branch])
        d = client_for(cashier).get("/api/reports/dashboard/").data
        self.assertNotIn("gross_profit", d)
        self.assertNotIn("stock_value", d)
