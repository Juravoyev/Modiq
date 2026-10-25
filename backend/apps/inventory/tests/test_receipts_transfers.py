from django.test import TestCase

from apps.accounts.models import Membership
from apps.common.testing import client_for, make_business, make_member, make_variant, put_stock, stock_of
from apps.inventory.models import StockMovement


class ReceiptTests(TestCase):
    def setUp(self):
        self.business, (self.branch,), self.owner, _ = make_business()
        self.variant = make_variant(self.business)
        self.c = client_for(self.owner)

    def _draft(self, qty=10):
        r = self.c.post("/api/inventory/receipts/", {
            "branch": self.branch.id, "supplier_name": "Ta'minotchi", "document_number": "N-1",
            "document_date": "2026-10-20", "lines": [{"variant": self.variant.id, "quantity": qty,
                                                      "purchase_price": "50000"}]}, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        return r.data["id"]

    def test_draft_does_not_change_stock_confirm_does(self):
        rid = self._draft()
        self.assertEqual(stock_of(self.branch, self.variant), 0)
        r = self.c.post(f"/api/inventory/receipts/{rid}/confirm/")
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data["status"], "confirmed")
        self.assertEqual(stock_of(self.branch, self.variant), 10)

    def test_second_confirm_does_not_add_stock_again(self):
        rid = self._draft()
        self.c.post(f"/api/inventory/receipts/{rid}/confirm/")
        r = self.c.post(f"/api/inventory/receipts/{rid}/confirm/")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(stock_of(self.branch, self.variant), 10)
        self.assertEqual(StockMovement.objects.filter(kind="receipt").count(), 1)

    def test_confirmed_receipt_cannot_be_edited(self):
        rid = self._draft()
        self.c.post(f"/api/inventory/receipts/{rid}/confirm/")
        r = self.c.patch(f"/api/inventory/receipts/{rid}/", {"lines": [
            {"variant": self.variant.id, "quantity": 99, "purchase_price": "1"}]}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_cashier_cannot_create_receipt(self):
        cashier, _ = make_member(self.business, Membership.Role.CASHIER, [self.branch])
        r = client_for(cashier).post("/api/inventory/receipts/", {}, format="json")
        self.assertEqual(r.status_code, 403)


class TransferTests(TestCase):
    def setUp(self):
        self.business, (self.a, self.b), self.owner, _ = make_business(branches=("A", "B"))
        self.variant = make_variant(self.business)
        put_stock(self.a, self.variant, 10)
        self.c = client_for(self.owner)

    def _draft(self, qty=4):
        r = self.c.post("/api/inventory/transfers/", {
            "from_branch": self.a.id, "to_branch": self.b.id,
            "lines": [{"variant": self.variant.id, "quantity": qty}]}, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        return r.data["id"]

    def test_send_then_receive_moves_stock(self):
        tid = self._draft()
        self.assertEqual(self.c.post(f"/api/inventory/transfers/{tid}/send/").status_code, 200)
        self.assertEqual((stock_of(self.a, self.variant), stock_of(self.b, self.variant)), (6, 0))
        self.assertEqual(self.c.post(f"/api/inventory/transfers/{tid}/receive/").status_code, 200)
        self.assertEqual((stock_of(self.a, self.variant), stock_of(self.b, self.variant)), (6, 4))

    def test_double_send_and_double_receive_are_blocked(self):
        tid = self._draft()
        self.c.post(f"/api/inventory/transfers/{tid}/send/")
        self.assertEqual(self.c.post(f"/api/inventory/transfers/{tid}/send/").status_code, 400)
        self.c.post(f"/api/inventory/transfers/{tid}/receive/")
        self.assertEqual(self.c.post(f"/api/inventory/transfers/{tid}/receive/").status_code, 400)
        self.assertEqual((stock_of(self.a, self.variant), stock_of(self.b, self.variant)), (6, 4))

    def test_cancel_sent_transfer_returns_stock(self):
        tid = self._draft()
        self.c.post(f"/api/inventory/transfers/{tid}/send/")
        r = self.c.post(f"/api/inventory/transfers/{tid}/cancel/")
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(stock_of(self.a, self.variant), 10)
        self.assertEqual(self.c.post(f"/api/inventory/transfers/{tid}/receive/").status_code, 400)

    def test_cannot_send_more_than_available(self):
        tid = self._draft(qty=11)
        r = self.c.post(f"/api/inventory/transfers/{tid}/send/")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(stock_of(self.a, self.variant), 10)

    def test_same_branch_rejected(self):
        r = self.c.post("/api/inventory/transfers/", {"from_branch": self.a.id, "to_branch": self.a.id,
                                                      "lines": [{"variant": self.variant.id, "quantity": 1}]},
                        format="json")
        self.assertEqual(r.status_code, 400)
