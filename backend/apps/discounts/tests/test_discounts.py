import uuid
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import Membership
from apps.common.testing import client_for, make_business, make_member, make_variant, put_stock
from apps.discounts.models import Discount
from apps.sales.models import SaleLine


def discount_payload(variant, kind="percent", value="20", start=0, end=7):
    today = timezone.localdate()
    return {"variant": variant.id, "kind": kind, "value": value,
            "starts_on": (today + timedelta(days=start)).isoformat(),
            "ends_on": (today + timedelta(days=end)).isoformat()}


class DiscountTests(TestCase):
    def setUp(self):
        self.business, (self.branch,), self.owner, _ = make_business()
        self.variant = make_variant(self.business, purchase="50000", sale="100000")
        put_stock(self.branch, self.variant, 10)
        self.c = client_for(self.owner)

    def create(self, **kw):
        r = self.c.post("/api/discounts/", discount_payload(self.variant, **kw), format="json")
        self.assertEqual(r.status_code, 201, r.data)
        return r.data

    def test_percent_discount_computes_prices_and_starts_as_draft(self):
        d = self.create(value="20")
        self.assertEqual((d["price_before"], d["price_after"], d["status"]), ("100000.00", "80000.00", "draft"))
        self.assertFalse(d["below_cost"])

    def test_draft_discount_is_not_applied_at_checkout(self):
        self.create(value="20")
        self.sell()
        self.assertEqual(SaleLine.objects.get().unit_price, 100000)

    def test_approved_discount_is_applied_at_checkout_and_linked(self):
        d = self.create(value="20")
        self.assertEqual(self.c.post(f"/api/discounts/{d['id']}/approve/", {}, format="json").status_code, 200)
        r = self.sell(qty=2)
        self.assertEqual(r.data["total"], "160000.00")
        line = SaleLine.objects.get()
        self.assertEqual((line.unit_price, line.discount_id), (80000, d["id"]))

    def test_future_discount_is_not_applied_today(self):
        d = self.create(value="20", start=3, end=10)
        self.c.post(f"/api/discounts/{d['id']}/approve/", {}, format="json")
        self.sell()
        self.assertEqual(SaleLine.objects.get().unit_price, 100000)

    def test_below_cost_discount_needs_explicit_confirmation(self):
        d = self.create(kind="fixed_price", value="40000")
        self.assertTrue(d["below_cost"])
        r = self.c.post(f"/api/discounts/{d['id']}/approve/", {}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.data["code"], "below_cost")
        r = self.c.post(f"/api/discounts/{d['id']}/approve/", {"allow_below_cost": True}, format="json")
        self.assertEqual(r.status_code, 200, r.data)

    def test_cashier_can_sell_at_approved_below_cost_price(self):
        d = self.create(kind="fixed_price", value="40000")
        self.c.post(f"/api/discounts/{d['id']}/approve/", {"allow_below_cost": True}, format="json")
        cashier, _ = make_member(self.business, Membership.Role.CASHIER, [self.branch])
        r = self.sell(client=client_for(cashier))
        self.assertEqual(r.status_code, 201, r.data)
        self.assertTrue(SaleLine.objects.get().below_cost)

    def test_overlapping_discounts_cannot_both_be_approved(self):
        d1 = self.create(value="10", start=0, end=7)
        d2 = self.create(value="30", start=5, end=12)
        self.c.post(f"/api/discounts/{d1['id']}/approve/", {}, format="json")
        r = self.c.post(f"/api/discounts/{d2['id']}/approve/", {}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.data["code"], "overlap")

    def test_cashier_cannot_create_discount_but_sees_active_prices(self):
        d = self.create(value="20")
        self.c.post(f"/api/discounts/{d['id']}/approve/", {}, format="json")
        cashier, _ = make_member(self.business, Membership.Role.CASHIER, [self.branch])
        cc = client_for(cashier)
        self.assertEqual(cc.post("/api/discounts/", discount_payload(self.variant), format="json").status_code, 403)
        r = cc.get("/api/discounts/active/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data[0]["price_after"], "80000.00")
        self.assertNotIn("unit_cost", r.data[0])

    def test_cancelled_discount_stops_applying_and_stays_in_history(self):
        d = self.create(value="20")
        self.c.post(f"/api/discounts/{d['id']}/approve/", {}, format="json")
        self.c.post(f"/api/discounts/{d['id']}/cancel/", {}, format="json")
        self.sell()
        self.assertEqual(SaleLine.objects.get().unit_price, 100000)
        self.assertEqual(Discount.objects.get().status, "cancelled")

    def test_other_business_cannot_see_discount(self):
        d = self.create(value="20")
        _, _, other_owner, _ = make_business()
        r = client_for(other_owner).get(f"/api/discounts/{d['id']}/")
        self.assertEqual(r.status_code, 404)

    def test_results_compare_sales_with_previous_period(self):
        d = self.create(value="20")
        self.c.post(f"/api/discounts/{d['id']}/approve/", {}, format="json")
        self.sell(qty=3)
        r = self.c.get(f"/api/reports/discounts/{d['id']}/results/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["during"]["quantity"], 3)
        self.assertEqual(r.data["during"]["revenue"], 240000)
        self.assertEqual(r.data["before"]["quantity"], 0)

    def sell(self, qty=1, client=None):
        payload = {"idempotency_key": str(uuid.uuid4()), "branch": self.branch.id, "payment_type": "cash",
                   "lines": [{"variant": self.variant.id, "quantity": qty}]}
        return (client or self.c).post("/api/sales/", payload, format="json")
