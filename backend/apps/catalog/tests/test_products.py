from django.test import TestCase

from apps.catalog.models import Color, Size
from apps.common.testing import client_for, make_business, put_stock


class ProductVariantTests(TestCase):
    def setUp(self):
        self.business, (self.branch,), self.owner, _ = make_business()
        self.c = client_for(self.owner)
        self.black = Color.objects.create(business=self.business, name="Qora", code="BLK")
        self.white = Color.objects.create(business=self.business, name="Oq", code="WHT")
        self.m = Size.objects.create(business=self.business, name="M", sort_order=2)
        self.l = Size.objects.create(business=self.business, name="L", sort_order=3)

    def _create(self):
        r = self.c.post("/api/catalog/products/", {
            "name": "Futbolka Basic", "article": "FB01", "purchase_price": "60000", "sale_price": "120000",
            "min_stock": 2, "color_ids": [self.black.id, self.white.id], "size_ids": [self.m.id, self.l.id],
        }, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        return r.data["id"]

    def test_color_size_matrix_creates_separate_skus(self):
        pid = self._create()
        r = self.c.get(f"/api/catalog/products/{pid}/")
        skus = sorted(v["sku"] for v in r.data["variants"])
        self.assertEqual(skus, ["FB01-BLK-L", "FB01-BLK-M", "FB01-WHT-L", "FB01-WHT-M"])

    def test_product_total_stock_is_sum_of_variants(self):
        pid = self._create()
        variants = {v["sku"]: v["id"] for v in self.c.get(f"/api/catalog/products/{pid}/").data["variants"]}
        from apps.catalog.models import ProductVariant

        for sku, qty in {"FB01-BLK-M": 5, "FB01-BLK-L": 2, "FB01-WHT-M": 8, "FB01-WHT-L": 0}.items():
            put_stock(self.branch, ProductVariant.objects.get(pk=variants[sku]), qty)
        data = self.c.get(f"/api/catalog/products/{pid}/").data
        self.assertEqual(data["total_stock"], 15)
        by_sku = {v["sku"]: v["stock"] for v in data["variants"]}
        self.assertEqual(by_sku["FB01-BLK-L"], 2)
        self.assertEqual(by_sku["FB01-WHT-L"], 0)

    def test_duplicate_article_rejected(self):
        self._create()
        r = self.c.post("/api/catalog/products/", {"name": "X", "article": "fb01", "purchase_price": "1",
                                                   "sale_price": "2"}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("article", r.data)

    def test_cannot_use_other_business_color(self):
        other, *_ = make_business()
        foreign = Color.objects.create(business=other, name="Qizil")
        r = self.c.post("/api/catalog/products/", {
            "name": "X", "article": "X1", "purchase_price": "1", "sale_price": "2",
            "color_ids": [foreign.id], "size_ids": [self.m.id]}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("color_ids", r.data)
