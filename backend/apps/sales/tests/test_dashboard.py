from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import Membership
from apps.common.testing import client_for, make_business, make_member, make_variant, put_stock
from apps.sales.models import Sale
from apps.sales.tests.test_sales import sale_payload


class DashboardTests(TestCase):
    def setUp(self):
        self.business, (self.branch, self.other_branch), self.owner, _ = make_business(branches=("Markaz", "Ombor"))
        self.variant = make_variant(self.business, purchase="50000", sale="100000")
        self.slow = make_variant(self.business, purchase="80000", sale="150000", article="SLOW")
        put_stock(self.branch, self.variant, 10)
        put_stock(self.branch, self.slow, 4)
        self.c = client_for(self.owner)
        r = self.c.post("/api/sales/", sale_payload(self.branch, self.variant, qty=2), format="json")
        self.sale_id = r.data["id"]

    def test_totals_profit_and_returns(self):
        r = self.c.post("/api/sales/returns/", {"sale": self.sale_id, "reason": "Yirtiq",
                                                "lines": [{"sale_line": Sale.objects.get(pk=self.sale_id).lines.get().id,
                                                           "quantity": 1}]}, format="json")
        self.assertEqual(r.status_code, 201, r.data)

        d = self.c.get("/api/sales/dashboard/?days=7").data
        self.assertEqual(d["today"]["revenue"], "200000.00")
        self.assertEqual(d["today"]["sales_count"], 1)
        self.assertEqual(d["period"]["refunds"], "100000.00")
        self.assertEqual(d["period"]["written_off"], "50000.00")
        self.assertEqual(d["period"]["net_revenue"], "100000.00")
        # 200000 tushum - 100000 qaytarilgan - 100000 tannarx (yaroqsiz tovar ham tannarxda qoladi).
        self.assertEqual(d["period"]["gross_profit"], "0.00")
        self.assertEqual(len(d["daily"]), 7)
        self.assertEqual(d["daily"][-1]["revenue"], "200000.00")
        self.assertEqual(d["top_products"][0]["quantity"], 2)

    def test_stock_value_and_slow_movers(self):
        d = self.c.get("/api/sales/dashboard/").data
        # 8 * 50000 + 4 * 80000
        self.assertEqual(d["stock"]["value"], "720000.00")
        self.assertEqual([p["article"] for p in d["slow_movers"]], ["SLOW"])

    def test_old_sales_outside_period(self):
        Sale.objects.filter(pk=self.sale_id).update(created_at=timezone.now() - timedelta(days=10))
        d = self.c.get("/api/sales/dashboard/?days=7").data
        self.assertEqual(d["period"]["sales_count"], 0)
        self.assertEqual(self.c.get("/api/sales/dashboard/?days=30").data["period"]["sales_count"], 1)

    def test_branch_filter(self):
        d = self.c.get(f"/api/sales/dashboard/?branch={self.other_branch.id}").data
        self.assertEqual(d["period"]["sales_count"], 0)

    def test_cashier_forbidden_and_bad_params(self):
        cashier, _ = make_member(self.business, Membership.Role.CASHIER, [self.branch])
        self.assertEqual(client_for(cashier).get("/api/sales/dashboard/").status_code, 403)
        self.assertEqual(self.c.get("/api/sales/dashboard/?days=5").status_code, 400)
