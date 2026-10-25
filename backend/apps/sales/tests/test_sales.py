import threading
import uuid
from decimal import Decimal

from django.db import connection
from django.test import TestCase, TransactionTestCase

from apps.accounts.models import Membership
from apps.common.testing import client_for, make_business, make_member, make_variant, put_stock, stock_of
from apps.sales.models import Sale


def sale_payload(branch, variant, qty=1, discount="0", key=None, **extra):
    return {"idempotency_key": str(key or uuid.uuid4()), "branch": branch.id, "payment_type": "cash",
            "lines": [{"variant": variant.id, "quantity": qty, "discount_amount": discount}], **extra}


class SaleTests(TestCase):
    def setUp(self):
        self.business, (self.branch,), self.owner, _ = make_business()
        self.variant = make_variant(self.business, purchase="50000", sale="100000")
        put_stock(self.branch, self.variant, 5)
        self.cashier, _ = make_member(self.business, Membership.Role.CASHIER, [self.branch])
        self.c = client_for(self.cashier)

    def test_sale_decreases_stock(self):
        r = self.c.post("/api/sales/", sale_payload(self.branch, self.variant, qty=2), format="json")
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(stock_of(self.branch, self.variant), 3)
        self.assertEqual(r.data["total"], "200000.00")

    def test_repeated_request_with_same_key_does_not_decrease_twice(self):
        key = uuid.uuid4()
        r1 = self.c.post("/api/sales/", sale_payload(self.branch, self.variant, qty=2, key=key), format="json")
        r2 = self.c.post("/api/sales/", sale_payload(self.branch, self.variant, qty=2, key=key), format="json")
        self.assertEqual((r1.status_code, r2.status_code), (201, 200))
        self.assertEqual(r1.data["id"], r2.data["id"])
        self.assertEqual(stock_of(self.branch, self.variant), 3)
        self.assertEqual(Sale.objects.count(), 1)

    def test_insufficient_stock_blocks_sale_and_changes_nothing(self):
        r = self.c.post("/api/sales/", sale_payload(self.branch, self.variant, qty=6), format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(stock_of(self.branch, self.variant), 5)
        self.assertEqual(Sale.objects.count(), 0)

    def test_failed_second_line_rolls_back_first_line(self):
        other = make_variant(self.business, article="OTHER")
        put_stock(self.branch, other, 1)
        payload = sale_payload(self.branch, self.variant, qty=1)
        payload["lines"].append({"variant": other.id, "quantity": 2})
        r = self.c.post("/api/sales/", payload, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual((stock_of(self.branch, self.variant), stock_of(self.branch, other)), (5, 1))

    def test_discount_calculation(self):
        r = self.c.post("/api/sales/", sale_payload(self.branch, self.variant, qty=2, discount="30000"),
                        format="json")
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual((r.data["subtotal"], r.data["discount_total"], r.data["total"]),
                         ("200000.00", "30000.00", "170000.00"))
        self.assertNotIn("cost_total", r.data)  # sotuvchiga tannarx ko'rsatilmaydi
        sale = Sale.objects.get()
        self.assertEqual(sale.cost_total, Decimal("100000.00"))
        self.assertEqual(sale.gross_profit, Decimal("70000.00"))

    def test_discount_bigger_than_price_rejected(self):
        r = self.c.post("/api/sales/", sale_payload(self.branch, self.variant, qty=1, discount="100001"),
                        format="json")
        self.assertEqual(r.status_code, 400)

    def test_below_cost_needs_manager_and_explicit_confirmation(self):
        payload = sale_payload(self.branch, self.variant, qty=1, discount="60000")  # 40 000 < 50 000 tannarx
        self.assertEqual(self.c.post("/api/sales/", payload, format="json").status_code, 400)
        owner = client_for(self.owner)
        self.assertEqual(owner.post("/api/sales/", payload, format="json").status_code, 400)
        payload["allow_below_cost"] = True
        r = owner.post("/api/sales/", payload, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        self.assertTrue(r.data["lines"][0]["below_cost"])

    def test_cashier_cannot_sell_in_unassigned_branch(self):
        from apps.accounts.models import Branch

        other_branch = Branch.objects.create(business=self.business, name="Boshqa")
        put_stock(other_branch, self.variant, 5)
        r = self.c.post("/api/sales/", sale_payload(other_branch, self.variant), format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("branch", r.data)
        self.assertEqual(stock_of(other_branch, self.variant), 5)


class TenantIsolationTests(TestCase):
    def test_business_cannot_see_or_use_other_business_data(self):
        b1, (br1,), owner1, _ = make_business()
        b2, (br2,), owner2, _ = make_business()
        v2 = make_variant(b2)
        put_stock(br2, v2, 3)
        client_for(owner2).post("/api/sales/", sale_payload(br2, v2), format="json")
        c1 = client_for(owner1)

        self.assertEqual(c1.get("/api/catalog/products/").data["count"], 0)
        self.assertEqual(c1.get("/api/inventory/stock/").data["count"], 0)
        self.assertEqual(c1.get("/api/sales/").data["count"], 0)
        self.assertEqual(c1.get(f"/api/catalog/variants/{v2.id}/").status_code, 404)
        # Boshqa biznes variantini o'z filialida sotishga urinish
        r = c1.post("/api/sales/", sale_payload(br1, v2), format="json")
        self.assertEqual(r.status_code, 400)
        # Boshqa biznes filialida sotish
        r = c1.post("/api/sales/", sale_payload(br2, v2), format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(stock_of(br2, v2), 2)


class ConcurrentSaleTests(TransactionTestCase):
    """Ikki kassa oxirgi 1 dona tovarni bir vaqtda sotmoqchi: faqat bittasi muvaffaqiyatli bo'lishi kerak."""

    def test_last_item_sold_only_once(self):
        business, (branch,), owner, _ = make_business()
        variant = make_variant(business)
        put_stock(branch, variant, 1)
        results = []
        barrier = threading.Barrier(2)

        def sell():
            try:
                c = client_for(owner)
                barrier.wait()
                results.append(c.post("/api/sales/", sale_payload(branch, variant), format="json").status_code)
            finally:
                connection.close()

        threads = [threading.Thread(target=sell) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(sorted(results), [201, 400])
        self.assertEqual(stock_of(branch, variant), 0)
