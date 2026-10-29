from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import Membership
from apps.common.testing import client_for, make_business, make_member, make_variant, put_stock, stock_of
from apps.sales.models import Sale, SaleReturn
from apps.sales.tests.test_sales import sale_payload


class ReturnTests(TestCase):
    def setUp(self):
        self.business, (self.branch,), self.owner, _ = make_business()
        self.variant = make_variant(self.business, purchase="50000", sale="100000")
        put_stock(self.branch, self.variant, 5)
        self.cashier, self.cashier_m = make_member(self.business, Membership.Role.CASHIER, [self.branch])
        self.c = client_for(self.cashier)
        r = self.c.post("/api/sales/", sale_payload(self.branch, self.variant, qty=3, discount="30000"), format="json")
        self.sale = r.data
        self.line_id = r.data["lines"][0]["id"]

    def return_payload(self, qty=1, reason="Choki buzilgan"):
        return {"sale": self.sale["id"], "reason": reason, "lines": [{"sale_line": self.line_id, "quantity": qty}]}

    def test_cashier_creates_pending_request_and_owner_approves(self):
        r = self.c.post("/api/sales/returns/", self.return_payload(qty=2), format="json")
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data["status"], "pending")
        # Chegirma ulushi hisobga olinadi: (300000 - 30000) * 2 / 3.
        self.assertEqual(r.data["refund_total"], "180000.00")
        self.assertNotIn("cost_total", r.data)  # kassir tannarxni ko'rmaydi

        self.assertEqual(self.c.post(f"/api/sales/returns/{r.data['id']}/approve/").status_code, 403)
        r = client_for(self.owner).post(f"/api/sales/returns/{r.data['id']}/approve/")
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data["status"], "approved")
        self.assertEqual(r.data["cost_total"], "100000.00")

    def test_defective_goods_are_written_off_not_returned_to_stock(self):
        before = stock_of(self.branch, self.variant)
        r = client_for(self.owner).post("/api/sales/returns/", self.return_payload(), format="json")
        self.assertEqual(r.data["status"], "approved")  # huquqi bor xodimda bir qadamda
        self.assertEqual(stock_of(self.branch, self.variant), before)

    def test_cashier_with_permission_completes_in_one_step(self):
        self.cashier_m.can_approve_returns = True
        self.cashier_m.save()
        r = self.c.post("/api/sales/returns/", self.return_payload(), format="json")
        self.assertEqual(r.data["status"], "approved")

    def test_cannot_return_more_than_sold_including_pending(self):
        self.assertEqual(self.c.post("/api/sales/returns/", self.return_payload(qty=2), format="json").status_code, 201)
        r = self.c.post("/api/sales/returns/", self.return_payload(qty=2), format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.data["code"], "return_quantity_exceeded")

    def test_rejected_request_frees_quantity(self):
        r = self.c.post("/api/sales/returns/", self.return_payload(qty=3), format="json")
        client_for(self.owner).post(f"/api/sales/returns/{r.data['id']}/reject/", {"note": "Buzilmagan"}, format="json")
        self.assertEqual(SaleReturn.objects.get(pk=r.data["id"]).status, "rejected")
        r = self.c.post("/api/sales/returns/", self.return_payload(qty=3), format="json")
        self.assertEqual(r.status_code, 201, r.data)

    def test_cannot_decide_twice(self):
        r = self.c.post("/api/sales/returns/", self.return_payload(), format="json")
        owner = client_for(self.owner)
        owner.post(f"/api/sales/returns/{r.data['id']}/approve/")
        self.assertEqual(owner.post(f"/api/sales/returns/{r.data['id']}/reject/").status_code, 400)

    def test_return_window_is_24_hours(self):
        Sale.objects.filter(pk=self.sale["id"]).update(created_at=timezone.now() - timedelta(hours=25))
        r = self.c.post("/api/sales/returns/", self.return_payload(), format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.data["code"], "return_expired")

    def test_reason_required(self):
        r = self.c.post("/api/sales/returns/", self.return_payload(reason="  "), format="json")
        self.assertEqual(r.status_code, 400)

    def test_sale_shows_returned_quantity(self):
        self.c.post("/api/sales/returns/", self.return_payload(qty=2), format="json")
        r = self.c.get(f"/api/sales/{self.sale['id']}/")
        self.assertEqual(r.data["lines"][0]["returned_quantity"], 2)
        self.assertIn("return_deadline", r.data)

    def test_other_business_cannot_return_sale(self):
        _, _, other_owner, _ = make_business()
        r = client_for(other_owner).post("/api/sales/returns/", self.return_payload(), format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("sale", r.data)

    def test_sale_line_from_other_sale_rejected(self):
        r = self.c.post("/api/sales/", sale_payload(self.branch, self.variant, qty=1), format="json")
        payload = self.return_payload()
        payload["lines"][0]["sale_line"] = r.data["lines"][0]["id"]
        self.assertEqual(self.c.post("/api/sales/returns/", payload, format="json").status_code, 400)
