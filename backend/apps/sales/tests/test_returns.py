import uuid
from decimal import Decimal

from django.test import TestCase

from apps.accounts.models import Membership
from apps.common.testing import client_for, make_business, make_member, make_variant, put_stock, stock_of
from apps.sales.models import SaleReturn


class SaleReturnTests(TestCase):
    def setUp(self):
        self.business, (self.branch,), self.owner, _ = make_business()
        self.variant = make_variant(self.business, purchase="50000", sale="100000")
        put_stock(self.branch, self.variant, 5)
        self.cashier, _ = make_member(self.business, Membership.Role.CASHIER, [self.branch])
        self.c = client_for(self.cashier)
        r = self.c.post("/api/sales/", {
            "idempotency_key": str(uuid.uuid4()), "branch": self.branch.id,
            "lines": [{"variant": self.variant.id, "quantity": 3, "discount_amount": "30000"}]}, format="json")
        self.sale = r.data
        self.line_id = r.data["lines"][0]["id"]

    def _return(self, qty):
        return self.c.post(f"/api/sales/{self.sale['id']}/return/",
                           {"lines": [{"sale_line": self.line_id, "quantity": qty}], "reason": "O'lcham to'g'ri kelmadi"},
                           format="json")

    def test_return_restores_stock_and_refunds_proportionally(self):
        self.assertEqual(stock_of(self.branch, self.variant), 2)
        r = self._return(1)
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(stock_of(self.branch, self.variant), 3)
        # 3 dona 270 000 so'mga sotilgan (30 000 chegirma bilan): 1 dona uchun 90 000 qaytariladi
        self.assertEqual(r.data["refund_total"], "90000.00")
        sale = self.c.get(f"/api/sales/{self.sale['id']}/").data
        self.assertEqual(sale["returned_total"], "90000.00")
        self.assertEqual(sale["lines"][0]["returned_quantity"], 1)

    def test_cannot_return_more_than_sold_in_total(self):
        self.assertEqual(self._return(2).status_code, 201)
        r = self._return(2)
        self.assertEqual(r.status_code, 400)
        self.assertEqual(stock_of(self.branch, self.variant), 4)
        self.assertEqual(SaleReturn.objects.count(), 1)
        self.assertEqual(SaleReturn.objects.get().cost_total, Decimal("100000.00"))

    def test_other_business_cannot_return(self):
        _, _, stranger, _ = make_business()
        r = client_for(stranger).post(f"/api/sales/{self.sale['id']}/return/",
                                      {"lines": [{"sale_line": self.line_id, "quantity": 1}]}, format="json")
        self.assertEqual(r.status_code, 404)
        self.assertEqual(stock_of(self.branch, self.variant), 2)
