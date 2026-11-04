import uuid
from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import Membership
from apps.catalog.models import Category, Season
from apps.common.testing import client_for, make_business, make_member, make_variant, put_stock, stock_of
from apps.pricing.models import PricingSettings, Promotion
from apps.sales.models import Sale, SaleLine


def sale_payload(branch, lines, key=None, **extra):
    return {"idempotency_key": str(key or uuid.uuid4()), "branch": branch.id, "payment_type": "cash",
            "lines": [{"variant": v.id, "quantity": q, "discount_amount": d} for v, q, d in lines], **extra}


def make_promo(business, value="20", kind="percent", scope="all", days=(-1, 5), **kw):
    today = timezone.localdate()
    products = kw.pop("products", [])
    p = Promotion.objects.create(business=business, name=kw.pop("name", "Aksiya"), kind=kind, value=Decimal(value),
                                 scope=scope, starts_on=today + timedelta(days=days[0]),
                                 ends_on=today + timedelta(days=days[1]), **kw)
    p.products.set(products)
    return p


class PromotionPricingTests(TestCase):
    def setUp(self):
        self.business, (self.branch,), self.owner, _ = make_business()
        # Tannarx 50 000, narx 100 000.
        self.variant = make_variant(self.business, purchase="50000", sale="100000")
        put_stock(self.branch, self.variant, 10)
        self.cashier, _ = make_member(self.business, Membership.Role.CASHIER, [self.branch])
        self.c = client_for(self.cashier)

    def sell(self, qty=1, discount="0", client=None, **extra):
        return (client or self.c).post("/api/sales/", sale_payload(self.branch, [(self.variant, qty, discount)], **extra),
                                       format="json")

    def test_active_promotion_applied_automatically_and_snapshotted(self):
        promo = make_promo(self.business, "20", name="Kuzgi")
        r = self.sell(qty=2)
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual((r.data["subtotal"], r.data["discount_total"], r.data["total"]),
                         ("200000.00", "40000.00", "160000.00"))
        line = r.data["lines"][0]
        self.assertEqual((line["auto_discount"], line["discount_source"], line["promotion"]),
                         ("40000.00", "promotion", promo.id))
        self.assertIn("Kuzgi", line["discount_label"])
        # Aksiya keyin o'zgartirilsa ham eski chek o'zgarmaydi.
        promo.value = Decimal("50")
        promo.save()
        self.assertEqual(SaleLine.objects.get().line_total, Decimal("160000.00"))

    def test_best_promotion_wins_and_promotions_do_not_stack(self):
        make_promo(self.business, "10")
        best = make_promo(self.business, "30")
        make_promo(self.business, "15000", kind="amount")
        r = self.sell()
        self.assertEqual(r.data["total"], "70000.00")
        self.assertEqual(r.data["lines"][0]["promotion"], best.id)

    def test_promotion_never_goes_below_cost(self):
        make_promo(self.business, "80")
        r = self.sell()
        self.assertEqual(r.status_code, 201, r.data)
        # 80% => 20 000 bo'lardi, lekin tannarx 50 000: chegirma 50 000 bilan cheklanadi.
        self.assertEqual(r.data["total"], "50000.00")
        self.assertFalse(r.data["lines"][0]["below_cost"])

    def test_inactive_scheduled_and_ended_promotions_ignored(self):
        make_promo(self.business, "20", days=(1, 5))
        make_promo(self.business, "20", days=(-10, -1))
        make_promo(self.business, "20", is_active=False)
        self.assertEqual(self.sell().data["total"], "100000.00")

    def test_promotion_last_day_inclusive(self):
        make_promo(self.business, "20", days=(-3, 0))
        self.assertEqual(self.sell().data["total"], "80000.00")

    def test_scope_season_category_and_products(self):
        winter = Season.objects.create(business=self.business, name="Qish", start_month=12, end_month=2)
        summer = Season.objects.create(business=self.business, name="Yoz", start_month=6, end_month=8)
        shoes = Category.objects.create(business=self.business, name="Poyabzal")
        product = self.variant.product
        product.season, product.category = winter, shoes
        product.save()
        other = make_variant(self.business, purchase="10000", sale="100000", article="OTHER")
        put_stock(self.branch, other, 5)

        make_promo(self.business, "10", scope="season", season=summer)  # boshqa mavsum: qo'llanmaydi
        make_promo(self.business, "25", scope="season", season=winter)
        make_promo(self.business, "15", scope="category", category=shoes)
        make_promo(self.business, "40", scope="products", products=[other.product])

        r = self.c.post("/api/sales/quote/", sale_payload(self.branch, [(self.variant, 1, "0"), (other, 1, "0")]),
                        format="json")
        self.assertEqual(r.status_code, 200, r.data)
        by_variant = {ln["variant"]: ln for ln in r.data["lines"]}
        self.assertEqual(by_variant[self.variant.id]["line_total"], "75000.00")  # qishki 25%
        self.assertEqual(by_variant[other.id]["line_total"], "60000.00")  # tanlangan tovar 40%

    def test_quote_matches_sale_and_changes_nothing(self):
        make_promo(self.business, "20")
        payload = sale_payload(self.branch, [(self.variant, 3, "10000")])
        q = self.c.post("/api/sales/quote/", payload, format="json")
        self.assertEqual(q.status_code, 200, q.data)
        self.assertEqual((stock_of(self.branch, self.variant), Sale.objects.count()), (10, 0))
        self.assertNotIn("cost_total", q.data)
        s = self.c.post("/api/sales/", payload, format="json")
        self.assertEqual((q.data["total"], q.data["discount_total"]), (s.data["total"], s.data["discount_total"]))
        self.assertEqual(q.data["total"], "230000.00")

    def test_cashier_manual_discount_limited(self):
        # Standart chegara 10%: 100 000 dan 10 000 mumkin, 10 001 mumkin emas.
        self.assertEqual(self.sell(discount="10000").status_code, 201)
        r = self.sell(discount="10001")
        self.assertEqual((r.status_code, r.data["code"]), (400, "discount_limit"))
        PricingSettings.objects.filter(business=self.business).update(cashier_max_discount_percent=0)
        self.assertEqual(self.sell(discount="1").data["code"], "discount_limit")

    def test_manager_has_no_manual_limit(self):
        r = self.sell(discount="40000", client=client_for(self.owner))
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data["total"], "60000.00")

    def test_manual_discount_on_top_of_promotion_bounded(self):
        make_promo(self.business, "20")
        r = self.sell(discount="80001", client=client_for(self.owner))
        self.assertEqual((r.status_code, r.data["code"]), (400, "invalid_discount"))
        self.assertEqual(stock_of(self.branch, self.variant), 10)


class PromotionApiTests(TestCase):
    def setUp(self):
        self.business, (self.branch,), self.owner, _ = make_business()
        self.c = client_for(self.owner)
        today = timezone.localdate()
        self.base = {"name": "Kuzgi aksiya", "kind": "percent", "value": "20", "scope": "all",
                     "starts_on": str(today), "ends_on": str(today + timedelta(days=7))}

    def test_create_and_status(self):
        r = self.c.post("/api/pricing/promotions/", self.base, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual((r.data["status"], r.data["sales_count"]), ("active", 0))
        r = self.c.post(f"/api/pricing/promotions/{r.data['id']}/stop/")
        self.assertEqual(r.data["status"], "stopped")
        self.assertEqual(self.c.get("/api/pricing/promotions/?status=active").data["count"], 0)

    def test_cashier_cannot_create(self):
        cashier, _ = make_member(self.business, Membership.Role.CASHIER, [self.branch])
        r = client_for(cashier).post("/api/pricing/promotions/", self.base, format="json")
        self.assertEqual(r.status_code, 403)

    def test_validation(self):
        bad = [
            {"value": "95"},
            {"value": "0"},
            {"value": "12.5"},
            {"scope": "category"},
            {"scope": "season"},
            {"scope": "products", "products": []},
            {"ends_on": str(timezone.localdate() - timedelta(days=1))},
        ]
        for extra in bad:
            r = self.c.post("/api/pricing/promotions/", {**self.base, **extra}, format="json")
            self.assertEqual(r.status_code, 400, extra)

    def test_other_tenant_category_rejected(self):
        other, *_ = make_business()
        cat = Category.objects.create(business=other, name="Begona")
        r = self.c.post("/api/pricing/promotions/", {**self.base, "scope": "category", "category": cat.id},
                        format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("category", r.data)

    def test_used_promotion_cannot_be_deleted_and_shows_results(self):
        variant = make_variant(self.business)
        put_stock(self.branch, variant, 5)
        promo = make_promo(self.business, "20")
        self.c.post("/api/sales/", sale_payload(self.branch, [(variant, 2, "0")]), format="json")
        r = self.c.get(f"/api/pricing/promotions/{promo.id}/")
        self.assertEqual((r.data["sales_count"], r.data["units_sold"], r.data["discount_given"]),
                         (1, 2, "40000.00"))
        r = self.c.delete(f"/api/pricing/promotions/{promo.id}/")
        self.assertEqual((r.status_code, r.data["code"]), (400, "protected"))

    def test_settings(self):
        self.assertEqual(self.c.get("/api/pricing/settings/").data["cashier_max_discount_percent"], 10)
        r = self.c.patch("/api/pricing/settings/", {"cashier_max_discount_percent": 101}, format="json")
        self.assertEqual(r.status_code, 400)
        r = self.c.patch("/api/pricing/settings/", {"cashier_max_discount_percent": 5}, format="json")
        self.assertEqual(r.data["cashier_max_discount_percent"], 5)
