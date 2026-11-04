import uuid
from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import Membership
from apps.common.testing import client_for, make_business, make_member, make_variant, put_stock
from apps.customers.bonus import allocate, balances
from apps.customers.models import BonusTransaction, Customer
from apps.pricing.models import PricingSettings
from apps.sales.models import Sale


def payload(branch, lines, customer=None, bonus=0, key=None):
    return {"idempotency_key": str(key or uuid.uuid4()), "branch": branch.id, "payment_type": "cash",
            "customer": customer.id if customer else None, "bonus_to_use": bonus,
            "lines": [{"variant": v.id, "quantity": q} for v, q in lines]}


def give_bonus(customer, amount):
    """Mijozga darhol ishlatish mumkin bo'lgan bonus beradi."""
    BonusTransaction.objects.create(business=customer.business, customer=customer, kind=BonusTransaction.Kind.EARN,
                                    amount=Decimal(amount), available_at=timezone.now() - timedelta(minutes=1))


class BonusTests(TestCase):
    def setUp(self):
        self.business, (self.branch,), self.owner, _ = make_business()
        # Tannarx 50 000, narx 100 000.
        self.variant = make_variant(self.business, purchase="50000", sale="100000")
        put_stock(self.branch, self.variant, 20)
        self.cashier, _ = make_member(self.business, Membership.Role.CASHIER, [self.branch])
        self.c = client_for(self.cashier)
        self.customer = Customer.objects.create(business=self.business, phone="+998901112233")

    def sell(self, qty=1, bonus=0, customer="default", variant=None, key=None):
        cust = self.customer if customer == "default" else customer
        return self.c.post("/api/sales/", payload(self.branch, [(variant or self.variant, qty)], cust, bonus, key),
                           format="json")

    def test_earn_three_percent_available_after_24h(self):
        r = self.sell(qty=2)
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data["bonus_earned"], "6000.00")
        self.assertEqual(balances(self.customer), (Decimal("0"), Decimal("6000")))
        later = timezone.now() + timedelta(hours=24, minutes=1)
        self.assertEqual(balances(self.customer, later), (Decimal("6000"), Decimal("0")))
        # Yangi bonus darhol ishlatilmaydi.
        self.assertEqual(self.sell(bonus=1).data["code"], "bonus_limit")

    def test_no_customer_no_bonus(self):
        r = self.sell(customer=None)
        self.assertEqual((r.status_code, r.data["bonus_earned"]), (201, "0.00"))
        r = self.sell(customer=None, bonus=100)
        self.assertEqual((r.status_code, r.data["code"]), (400, "invalid_bonus"))

    def test_spend_limited_by_35_percent(self):
        give_bonus(self.customer, 100000)
        q = self.c.post("/api/sales/quote/", payload(self.branch, [(self.variant, 1)], self.customer), format="json")
        self.assertEqual((q.data["bonus"]["available"], q.data["bonus"]["max"]), ("100000.00", "35000.00"))
        self.assertEqual(self.sell(bonus=35001).data["code"], "bonus_limit")

        r = self.sell(bonus=35000)
        self.assertEqual(r.status_code, 201, r.data)
        # Pul bilan 65 000 to'landi, bonus shu summadan: 65 000 * 3% = 1 950.
        self.assertEqual((r.data["total"], r.data["bonus_spent"], r.data["bonus_earned"]),
                         ("65000.00", "35000.00", "1950.00"))
        self.assertEqual(r.data["lines"][0]["bonus_amount"], "35000.00")
        self.assertFalse(r.data["lines"][0]["below_cost"])
        self.assertEqual(balances(self.customer)[0], Decimal("65000"))

    def test_spend_limited_by_balance(self):
        give_bonus(self.customer, 12000)
        self.assertEqual(self.sell(bonus=12001).data["code"], "bonus_limit")
        self.assertEqual(self.sell(bonus=12000).status_code, 201)
        self.assertEqual(balances(self.customer)[0], Decimal("0"))

    def test_bonus_never_below_cost(self):
        give_bonus(self.customer, 100000)
        cheap = make_variant(self.business, purchase="90000", sale="100000", article="CHEAP")
        put_stock(self.branch, cheap, 1)
        q = self.c.post("/api/sales/quote/", payload(self.branch, [(cheap, 1)], self.customer), format="json")
        self.assertEqual(q.data["bonus"]["max"], "10000.00")  # 35% emas, faqat narx − tannarx

    def test_allocation_across_lines(self):
        heads = [Decimal("50"), Decimal("50"), Decimal("1")]
        parts = allocate(Decimal("100"), heads)
        self.assertEqual(sum(parts), Decimal("100"))
        self.assertTrue(all(p <= h for p, h in zip(parts, heads)))
        parts = allocate(Decimal("1000"), [Decimal("333"), Decimal("667"), Decimal("0")])
        self.assertEqual((sum(parts), parts[2]), (Decimal("1000"), Decimal("0")))

        give_bonus(self.customer, 100000)
        other = make_variant(self.business, purchase="10000", sale="30000", article="OTHER")
        put_stock(self.branch, other, 5)
        r = self.c.post("/api/sales/", payload(self.branch, [(self.variant, 1), (other, 1)], self.customer, 40000),
                        format="json")
        self.assertEqual(r.status_code, 201, r.data)
        lines = r.data["lines"]
        self.assertEqual(sum(Decimal(ln["bonus_amount"]) for ln in lines), Decimal("40000"))
        self.assertTrue(all(not ln["below_cost"] for ln in lines))

    def test_idempotent_replay_does_not_double_bonus(self):
        give_bonus(self.customer, 50000)
        key = uuid.uuid4()
        self.assertEqual(self.sell(bonus=10000, key=key).status_code, 201)
        self.assertEqual(self.sell(bonus=10000, key=key).status_code, 200)
        self.assertEqual(BonusTransaction.objects.filter(kind="spend").count(), 1)
        self.assertEqual(balances(self.customer)[0], Decimal("40000"))

    def test_disabled_bonus(self):
        PricingSettings.objects.update_or_create(business=self.business, defaults={"bonus_enabled": False})
        give_bonus(self.customer, 50000)
        r = self.sell()
        self.assertEqual(r.data["bonus_earned"], "0.00")
        self.assertEqual(self.sell(bonus=100).data["code"], "invalid_bonus")

    def test_return_refunds_spent_bonus_and_revokes_earned(self):
        give_bonus(self.customer, 50000)
        r = self.sell(qty=2, bonus=20000)  # 200 000: bonus 20 000, pul 180 000, yangi bonus 5 400
        self.assertEqual((r.data["total"], r.data["bonus_earned"]), ("180000.00", "5400.00"))
        sale = Sale.objects.get(pk=r.data["id"])
        line = sale.lines.get()
        owner = client_for(self.owner)
        rr = owner.post("/api/sales/returns/", {"sale": sale.id, "reason": "Yirtiq",
                                                "lines": [{"sale_line": line.id, "quantity": 1}]}, format="json")
        self.assertEqual(rr.status_code, 201, rr.data)
        # Pul bilan to'langanining yarmi pul bo'lib, bonus bilan to'langanining yarmi bonus bo'lib qaytadi.
        self.assertEqual((rr.data["refund_total"], rr.data["bonus_refund"], rr.data["bonus_revoked"]),
                         ("90000.00", "10000.00", "2700.00"))
        available, pending = balances(self.customer)
        self.assertEqual((available, pending), (Decimal("40000"), Decimal("2700")))

    def test_pending_return_applies_bonus_only_on_approval(self):
        give_bonus(self.customer, 50000)
        r = self.sell(qty=1, bonus=10000)
        line = Sale.objects.get(pk=r.data["id"]).lines.get()
        rr = self.c.post("/api/sales/returns/", {"sale": r.data["id"], "reason": "Dog'",
                                                 "lines": [{"sale_line": line.id, "quantity": 1}]}, format="json")
        self.assertEqual(rr.data["status"], "pending")
        self.assertEqual(balances(self.customer)[0], Decimal("40000"))
        client_for(self.owner).post(f"/api/sales/returns/{rr.data['id']}/reject/", {}, format="json")
        self.assertEqual(balances(self.customer)[0], Decimal("40000"))

        r = self.sell(qty=1, bonus=10000)
        line = Sale.objects.get(pk=r.data["id"]).lines.get()
        rr = self.c.post("/api/sales/returns/", {"sale": r.data["id"], "reason": "Dog'",
                                                 "lines": [{"sale_line": line.id, "quantity": 1}]}, format="json")
        client_for(self.owner).post(f"/api/sales/returns/{rr.data['id']}/approve/", {}, format="json")
        available, pending = balances(self.customer)
        self.assertEqual(available, Decimal("40000"))  # 30 000 + qaytgan 10 000
        self.assertEqual(pending, Decimal("2700"))  # birinchi savdo 2 700, ikkinchisiniki to'liq bekor qilindi

    def test_revoke_never_makes_balance_negative(self):
        r = self.sell(qty=1)  # 3 000 bonus
        # Bonus muddatidan oldin ishlatib bo'lingan holat: earn allaqachon "available", balans 0.
        BonusTransaction.objects.filter(kind="earn").update(available_at=timezone.now() - timedelta(minutes=1))
        BonusTransaction.objects.create(business=self.business, customer=self.customer, kind="spend",
                                        amount=Decimal("-3000"), available_at=timezone.now())
        line = Sale.objects.get(pk=r.data["id"]).lines.get()
        rr = client_for(self.owner).post("/api/sales/returns/", {"sale": r.data["id"], "reason": "x",
                                                                 "lines": [{"sale_line": line.id, "quantity": 1}]},
                                         format="json")
        self.assertEqual(rr.data["bonus_revoked"], "0.00")
        self.assertEqual(balances(self.customer)[0], Decimal("0"))

    def test_customer_api_shows_balance_and_history(self):
        give_bonus(self.customer, 5000)
        self.sell(qty=1, bonus=1000)
        r = self.c.get(f"/api/customers/{self.customer.id}/")
        self.assertEqual((r.data["bonus_available"], r.data["bonus_pending"]), ("4000.00", "2970.00"))
        h = self.c.get(f"/api/customers/{self.customer.id}/bonus/")
        self.assertEqual([t["kind"] for t in h.data], ["earn", "spend", "earn"])

    def test_settings_validation(self):
        owner = client_for(self.owner)
        self.assertEqual(owner.patch("/api/pricing/settings/", {"bonus_percent": 21}, format="json").status_code, 400)
        r = owner.patch("/api/pricing/settings/", {"bonus_percent": 5, "bonus_max_share_percent": 50}, format="json")
        self.assertEqual((r.data["bonus_percent"], r.data["bonus_max_share_percent"]), (5, 50))
