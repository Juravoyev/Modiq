from django.test import TestCase

from apps.accounts.models import Membership
from apps.common.testing import client_for, make_business, make_member, make_variant, put_stock, stock_of
from apps.inventory.models import StockMovement


class StockCountTests(TestCase):
    def setUp(self):
        self.business, (self.branch,), self.owner, _ = make_business()
        self.a = make_variant(self.business, article="A")
        self.b = make_variant(self.business, article="B")
        put_stock(self.branch, self.a, 10)
        put_stock(self.branch, self.b, 3)
        self.c = client_for(self.owner)

    def _draft(self):
        r = self.c.post("/api/inventory/counts/", {"branch": self.branch.id, "lines": [
            {"variant": self.a.id, "counted_quantity": 8}, {"variant": self.b.id, "counted_quantity": 4}]},
            format="json")
        self.assertEqual(r.status_code, 201, r.data)
        return r.data["id"]

    def test_apply_sets_stock_to_counted_and_records_difference(self):
        cid = self._draft()
        r = self.c.post(f"/api/inventory/counts/{cid}/apply/")
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual((stock_of(self.branch, self.a), stock_of(self.branch, self.b)), (8, 4))
        self.assertEqual((r.data["shortage"], r.data["surplus"]), (2, 1))
        diffs = {line["sku"]: line["difference"] for line in r.data["lines"]}
        self.assertEqual(diffs[self.a.sku], -2)
        self.assertEqual(StockMovement.objects.filter(kind="stock_count").count(), 2)

    def test_apply_twice_is_blocked(self):
        cid = self._draft()
        self.c.post(f"/api/inventory/counts/{cid}/apply/")
        self.assertEqual(self.c.post(f"/api/inventory/counts/{cid}/apply/").status_code, 400)
        self.assertEqual(stock_of(self.branch, self.a), 8)

    def test_cashier_cannot_create_count(self):
        cashier, _ = make_member(self.business, Membership.Role.CASHIER, [self.branch])
        r = client_for(cashier).post("/api/inventory/counts/", {}, format="json")
        self.assertEqual(r.status_code, 403)
