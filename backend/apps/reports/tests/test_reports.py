import uuid

from django.test import TestCase

from apps.accounts.models import Membership
from apps.common.testing import client_for, make_business, make_member, make_variant, put_stock


class ReportTests(TestCase):
    def setUp(self):
        self.business, (self.branch,), self.owner, _ = make_business()
        self.variant = make_variant(self.business, purchase="50000", sale="100000")
        put_stock(self.branch, self.variant, 10)
        self.c = client_for(self.owner)
        r = self.c.post("/api/sales/", {"idempotency_key": str(uuid.uuid4()), "branch": self.branch.id,
                                        "lines": [{"variant": self.variant.id, "quantity": 2}]}, format="json")
        self.sale = r.data

    def test_daily_sales_separates_revenue_and_gross_profit(self):
        line = self.sale["lines"][0]["id"]
        self.c.post(f"/api/sales/{self.sale['id']}/return/", {"lines": [{"sale_line": line, "quantity": 1}]},
                    format="json")
        r = self.c.get("/api/reports/sales/?group=day")
        self.assertEqual(r.status_code, 200)
        t = r.data["totals"]
        self.assertEqual((t["gross_sales"], t["returns"], t["revenue"]), (200000, 100000, 100000))
        self.assertEqual(t["gross_profit"], 50000)
        self.assertEqual(len(r.data["rows"]), 30)

    def test_weekly_and_monthly_grouping(self):
        for group in ("week", "month"):
            r = self.c.get(f"/api/reports/sales/?group={group}")
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.data["totals"]["revenue"], 200000)

    def test_products_and_stock_reports(self):
        r = self.c.get("/api/reports/products/")
        self.assertEqual(r.data["rows"][0]["quantity"], 2)
        r = self.c.get("/api/reports/stock/")
        self.assertEqual(r.data["totals"]["quantity"], 8)
        self.assertEqual(r.data["totals"]["cost_value"], 400000)

    def test_csv_export(self):
        r = self.c.get("/api/reports/products/?export=csv")
        self.assertEqual(r.status_code, 200)
        self.assertIn("text/csv", r["Content-Type"])
        text = r.content.decode("utf-8-sig")
        self.assertIn("Tushum", text.splitlines()[0])
        self.assertIn(self.variant.sku, text)

    def test_bad_dates_are_rejected(self):
        r = self.c.get("/api/reports/sales/?date_from=2026-05-01&date_to=2026-01-01")
        self.assertEqual(r.status_code, 400)
        r = self.c.get("/api/reports/sales/?date_from=2020-01-01&date_to=2026-01-01")
        self.assertEqual(r.status_code, 400)

    def test_cashier_cannot_open_reports(self):
        cashier, _ = make_member(self.business, Membership.Role.CASHIER, [self.branch])
        self.assertEqual(client_for(cashier).get("/api/reports/sales/").status_code, 403)

    def test_unknown_report_is_404(self):
        self.assertEqual(self.c.get("/api/reports/nimadir/").status_code, 404)
