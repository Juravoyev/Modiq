import uuid

from django.test import TestCase

from apps.accounts.models import Membership
from apps.common.testing import client_for, make_business, make_member, make_variant, put_stock
from apps.customers.models import Customer, CustomerGroup
from apps.pricing.tests.test_promotions import make_promo


def sale_payload(branch, variant, qty=1, customer=None, discount="0", **extra):
    return {"idempotency_key": str(uuid.uuid4()), "branch": branch.id, "payment_type": "cash",
            "customer": customer.id if customer else None,
            "lines": [{"variant": variant.id, "quantity": qty, "discount_amount": discount}], **extra}


class PrivilegeTests(TestCase):
    def setUp(self):
        self.business, (self.branch,), self.owner, _ = make_business()
        self.variant = make_variant(self.business, purchase="50000", sale="100000")
        put_stock(self.branch, self.variant, 10)
        self.cashier, _ = make_member(self.business, Membership.Role.CASHIER, [self.branch])
        self.c = client_for(self.cashier)
        self.vip = CustomerGroup.objects.create(business=self.business, name="VIP", discount_percent=10)
        self.customer = Customer.objects.create(business=self.business, phone="+998901112233", full_name="Ali",
                                                group=self.vip)

    def test_privilege_applied_and_customer_saved(self):
        r = self.c.post("/api/sales/", sale_payload(self.branch, self.variant, 2, self.customer), format="json")
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data["total"], "180000.00")
        line = r.data["lines"][0]
        self.assertEqual((line["discount_source"], line["auto_discount"]), ("privilege", "20000.00"))
        self.assertIn("VIP", line["discount_label"])
        self.assertEqual((r.data["customer"], r.data["customer_info"]["full_name"]), (self.customer.id, "Ali"))

    def test_promotion_and_privilege_do_not_stack_best_wins(self):
        make_promo(self.business, "20")
        r = self.c.post("/api/sales/quote/", sale_payload(self.branch, self.variant, 1, self.customer), format="json")
        self.assertEqual((r.data["total"], r.data["lines"][0]["discount_source"]), ("80000.00", "promotion"))

        self.vip.discount_percent = 30
        self.vip.save()
        r = self.c.post("/api/sales/quote/", sale_payload(self.branch, self.variant, 1, self.customer), format="json")
        self.assertEqual((r.data["total"], r.data["lines"][0]["discount_source"]), ("70000.00", "privilege"))

    def test_privilege_never_below_cost(self):
        CustomerGroup.objects.filter(pk=self.vip.pk).update(discount_percent=50)
        cheap = make_variant(self.business, purchase="90000", sale="100000", article="CHEAP")
        put_stock(self.branch, cheap, 1)
        r = self.c.post("/api/sales/", sale_payload(self.branch, cheap, 1, self.customer), format="json")
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data["total"], "90000.00")

    def test_customer_without_group_gets_no_discount(self):
        plain = Customer.objects.create(business=self.business, phone="+998901112244")
        r = self.c.post("/api/sales/", sale_payload(self.branch, self.variant, 1, plain), format="json")
        self.assertEqual(r.data["total"], "100000.00")

    def test_other_tenant_customer_rejected(self):
        other, *_ = make_business()
        stranger = Customer.objects.create(business=other, phone="+998901112255")
        r = self.c.post("/api/sales/", sale_payload(self.branch, self.variant, 1, stranger), format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("customer", r.data)


class CustomerApiTests(TestCase):
    def setUp(self):
        self.business, (self.branch,), self.owner, _ = make_business()
        self.cashier, _ = make_member(self.business, Membership.Role.CASHIER, [self.branch])
        self.c = client_for(self.cashier)
        self.owner_c = client_for(self.owner)
        self.vip = CustomerGroup.objects.create(business=self.business, name="VIP", discount_percent=10)

    def test_cashier_creates_customer_and_finds_by_phone(self):
        r = self.c.post("/api/customers/", {"phone": "90 111 22 33", "full_name": "Ali"}, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data["phone"], "+998901112233")
        r = self.c.get("/api/customers/?phone=998901112233")
        self.assertEqual(r.data["count"], 1)
        self.assertEqual(self.c.get("/api/customers/?phone=abc").data["count"], 0)

    def test_duplicate_phone_rejected(self):
        self.c.post("/api/customers/", {"phone": "901112233"}, format="json")
        r = self.c.post("/api/customers/", {"phone": "+998901112233"}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("phone", r.data)

    def test_only_manager_sets_group(self):
        r = self.c.post("/api/customers/", {"phone": "901112233", "group": self.vip.id}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("group", r.data)
        r = self.c.post("/api/customers/", {"phone": "901112233"}, format="json")
        cid = r.data["id"]
        self.assertEqual(self.c.patch(f"/api/customers/{cid}/", {"group": self.vip.id}, format="json").status_code, 400)
        # Sotuvchi ismni o'zgartira oladi, toifa joyida qoladi.
        r = self.owner_c.patch(f"/api/customers/{cid}/", {"group": self.vip.id}, format="json")
        self.assertEqual(r.data["discount_percent"], 10)
        r = self.c.patch(f"/api/customers/{cid}/", {"full_name": "Vali", "group": self.vip.id}, format="json")
        self.assertEqual(r.status_code, 200, r.data)

    def test_groups_manager_only_and_limits(self):
        self.assertEqual(self.c.post("/api/customers/groups/", {"name": "X", "discount_percent": 5},
                                     format="json").status_code, 403)
        self.assertEqual(self.owner_c.post("/api/customers/groups/", {"name": "X", "discount_percent": 51},
                                           format="json").status_code, 400)
        r = self.owner_c.post("/api/customers/groups/", {"name": "Doimiy", "discount_percent": 5}, format="json")
        self.assertEqual(r.status_code, 201, r.data)

    def test_group_with_customers_cannot_be_deleted(self):
        Customer.objects.create(business=self.business, phone="+998901112233", group=self.vip)
        r = self.owner_c.delete(f"/api/customers/groups/{self.vip.id}/")
        self.assertEqual((r.status_code, r.data["code"]), (400, "protected"))

    def test_cashier_cannot_delete_customer(self):
        cust = Customer.objects.create(business=self.business, phone="+998901112233")
        self.assertEqual(self.c.delete(f"/api/customers/{cust.id}/").status_code, 403)
        self.assertEqual(self.owner_c.delete(f"/api/customers/{cust.id}/").status_code, 204)

    def test_purchase_stats(self):
        cust = Customer.objects.create(business=self.business, phone="+998901112233")
        variant = make_variant(self.business)
        put_stock(self.branch, variant, 5)
        self.c.post("/api/sales/", sale_payload(self.branch, variant, 2, cust), format="json")
        r = self.owner_c.get(f"/api/customers/{cust.id}/")
        self.assertEqual((r.data["purchases_count"], r.data["total_spent"]), (1, "200000.00"))

    def test_tenant_isolation(self):
        other, (ob,), oowner, _ = make_business()
        Customer.objects.create(business=other, phone="+998901112233")
        self.assertEqual(self.c.get("/api/customers/").data["count"], 0)
