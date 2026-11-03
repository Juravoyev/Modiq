import uuid

from django.test import TestCase

from apps.accounts.models import Membership
from apps.catalog.models import Product, ProductVariant
from apps.common.testing import client_for, make_business, make_member, make_variant, put_stock


class CashierCostVisibilityTests(TestCase):
    def setUp(self):
        self.business, (self.branch,), self.owner, _ = make_business()
        self.variant = make_variant(self.business)
        cashier, _ = make_member(self.business, Membership.Role.CASHIER, [self.branch])
        self.cashier = client_for(cashier)

    def test_cashier_does_not_see_purchase_price(self):
        product = self.cashier.get(f"/api/catalog/products/{self.variant.product_id}/").data
        self.assertNotIn("purchase_price", product)
        self.assertNotIn("purchase_price", product["variants"][0])
        self.assertNotIn("effective_purchase_price", product["variants"][0])
        variant = self.cashier.get("/api/catalog/variants/").data["results"][0]
        self.assertNotIn("effective_purchase_price", variant)
        self.assertIn("effective_sale_price", variant)

    def test_manager_sees_purchase_price(self):
        variant = client_for(self.owner).get("/api/catalog/variants/").data["results"][0]
        self.assertEqual(variant["effective_purchase_price"], "50000.00")

    def test_cashier_cannot_list_receipts(self):
        self.assertEqual(self.cashier.get("/api/inventory/receipts/").status_code, 403)


class DeleteOrArchiveTests(TestCase):
    def setUp(self):
        self.business, (self.branch,), self.owner, _ = make_business()
        self.c = client_for(self.owner)

    def _sell(self, variant):
        return self.c.post("/api/sales/", {
            "branch": self.branch.id, "payment_type": "cash", "idempotency_key": str(uuid.uuid4()),
            "lines": [{"variant": variant.id, "quantity": 1}],
        }, format="json")

    def test_variant_without_history_is_deleted(self):
        v = make_variant(self.business)
        self.assertEqual(self.c.delete(f"/api/catalog/variants/{v.id}/").status_code, 204)
        self.assertFalse(ProductVariant.objects.filter(pk=v.id).exists())

    def test_variant_with_stock_history_is_archived_not_deleted(self):
        v = make_variant(self.business)
        put_stock(self.branch, v, 3)
        r = self.c.delete(f"/api/catalog/variants/{v.id}/")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.data["archived"])
        v.refresh_from_db()
        self.assertFalse(v.is_active)
        self.assertTrue(v.movements.exists())

    def test_archived_product_is_hidden_from_pos_and_cannot_be_sold(self):
        v = make_variant(self.business)
        put_stock(self.branch, v, 3)
        self.assertEqual(self._sell(v).status_code, 201)
        r = self.c.delete(f"/api/catalog/products/{v.product_id}/")
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Product.objects.get(pk=v.product_id).is_active)
        self.assertEqual(self.c.get("/api/catalog/variants/?is_active=true").data["count"], 0)
        self.assertEqual(self._sell(v).status_code, 400)

    def test_product_without_history_is_deleted(self):
        v = make_variant(self.business)
        self.assertEqual(self.c.delete(f"/api/catalog/products/{v.product_id}/").status_code, 204)
        self.assertFalse(Product.objects.filter(pk=v.product_id).exists())

    def test_deleting_color_in_use_returns_400_not_500(self):
        v = make_variant(self.business)
        r = self.c.delete(f"/api/catalog/colors/{v.color_id}/")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.data["code"], "protected")
