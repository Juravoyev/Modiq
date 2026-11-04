import json
import uuid
from datetime import date, timedelta
from unittest import mock

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.accounts.models import Membership
from apps.catalog.models import Season
from apps.common.testing import client_for, make_business, make_member, make_variant, put_stock
from apps.insights.models import InsightSettings
from apps.insights.services import evaluate, in_season, season_end_date
from apps.inventory.models import StockMovement
from apps.pricing.tests.test_promotions import make_promo
from apps.sales.models import Sale


def age(variant, days):
    """Tovar omborga `days` kun oldin kelgandek qiladi."""
    StockMovement.objects.filter(variant=variant).update(created_at=timezone.now() - timedelta(days=days))


class RecommendationTests(TestCase):
    def setUp(self):
        self.business, (self.branch,), self.owner, _ = make_business()
        self.c = client_for(self.owner)
        self.cashier, _ = make_member(self.business, Membership.Role.CASHIER, [self.branch])

    def sell(self, variant, qty, days_ago=1):
        r = client_for(self.cashier).post("/api/sales/", {
            "idempotency_key": str(uuid.uuid4()), "branch": self.branch.id, "payment_type": "cash",
            "lines": [{"variant": variant.id, "quantity": qty}]}, format="json")
        assert r.status_code == 201, r.data
        Sale.objects.filter(pk=r.data["id"]).update(created_at=timezone.now() - timedelta(days=days_ago))

    def recs(self):
        r = self.c.get("/api/insights/recommendations/")
        self.assertEqual(r.status_code, 200, r.data)
        return {x["article"]: x for x in r.data["results"]}

    def test_never_sold_for_60_days_is_high_risk_30_percent(self):
        v = make_variant(self.business, purchase="50000", sale="100000", article="OLD")
        put_stock(self.branch, v, 10)
        age(v, 65)
        rec = self.recs()["OLD"]
        self.assertEqual((rec["level"], rec["discount"], rec["can_promote"]), ("high", 30, True))
        self.assertIn("65 kun", rec["reasons"][0])

    def test_new_arrivals_are_not_judged(self):
        v = make_variant(self.business, article="NEW")
        put_stock(self.branch, v, 10)
        age(v, 5)
        self.assertNotIn("NEW", self.recs())

    def test_slow_cover_levels(self):
        slow = make_variant(self.business, article="SLOW")  # 30 kunda 3 dona, qoldiq 30 -> 300 kun
        put_stock(self.branch, slow, 33)
        age(slow, 40)
        self.sell(slow, 3, days_ago=2)
        fine = make_variant(self.business, article="FINE")  # 30 kunda 30 dona, qoldiq 10 -> 10 kun
        put_stock(self.branch, fine, 40)
        age(fine, 40)
        self.sell(fine, 30, days_ago=2)
        recs = self.recs()
        self.assertEqual((recs["SLOW"]["level"], recs["SLOW"]["discount"], recs["SLOW"]["cover_days"]),
                         ("medium", 20, 300))
        self.assertNotIn("FINE", recs)

    def test_discount_capped_so_price_stays_above_cost(self):
        v = make_variant(self.business, purchase="85000", sale="100000", article="THIN")
        put_stock(self.branch, v, 10)
        age(v, 90)
        rec = self.recs()["THIN"]
        self.assertEqual((rec["discount"], rec["wanted_discount"]), (15, 30))
        self.assertTrue(any("15%" in t for t in rec["reasons"]))

    def test_out_of_season_and_season_ending(self):
        today = date(2026, 11, 4)
        summer = Season.objects.create(business=self.business, name="Yoz", start_month=6, end_month=8)
        autumn = Season.objects.create(business=self.business, name="Kuz", start_month=9, end_month=11)
        winter = Season.objects.create(business=self.business, name="Qish", start_month=12, end_month=2)
        self.assertEqual((in_season(summer, today), in_season(winter, date(2027, 1, 10))), (False, True))
        self.assertEqual(season_end_date(winter, date(2026, 12, 5)), date(2027, 2, 28))
        settings = InsightSettings.for_business(self.business)

        def stats(season, sold=30, units=100):
            product = make_variant(self.business).product
            product.season = season
            return {"product": product, "units": units, "sold_30": sold, "days_since_sale": 1, "age_days": 90}

        rules, _ = evaluate(stats(summer), settings, today)
        self.assertTrue(any("tugagan" in r[2] for r in rules))
        rules, _ = evaluate(stats(autumn), settings, today)  # 26 kun qoldi, qoldiq 100 kunga yetadi
        self.assertTrue(any("26 kundan keyin tugaydi" in r[2] for r in rules))
        rules, _ = evaluate(stats(autumn, sold=300, units=10), settings, today)  # 1 kunda sotiladi
        self.assertEqual(rules, [])

    def test_active_promotion_blocks_new_one_and_dismiss_hides(self):
        v = make_variant(self.business, article="OLD")
        put_stock(self.branch, v, 10)
        age(v, 65)
        promo = make_promo(self.business, "10", scope="products", products=[v.product])
        rec = self.recs()["OLD"]
        self.assertEqual((rec["can_promote"], rec["active_promotion"]["id"]), (False, promo.id))
        r = self.c.post("/api/insights/recommendations/dismiss/", {"product": v.product.id}, format="json")
        self.assertEqual(r.status_code, 200, r.data)
        self.assertNotIn("OLD", self.recs())

    def test_cashier_forbidden_and_tenant_isolation(self):
        self.assertEqual(client_for(self.cashier).get("/api/insights/recommendations/").status_code, 403)
        other, (ob,), oowner, _ = make_business()
        v = make_variant(other, article="FOREIGN")
        put_stock(ob, v, 10)
        age(v, 90)
        self.assertNotIn("FOREIGN", self.recs())
        r = self.c.post("/api/insights/recommendations/dismiss/", {"product": v.product.id}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_settings_validation(self):
        r = self.c.patch("/api/insights/settings/", {"cover_days_low": 120}, format="json")
        self.assertEqual(r.status_code, 400)
        r = self.c.patch("/api/insights/settings/", {"no_sale_days": 45, "high_discount": 25}, format="json")
        self.assertEqual((r.data["no_sale_days"], r.data["high_discount"]), (45, 25))


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def read(self):
        return json.dumps(self.payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class AISummaryTests(TestCase):
    def setUp(self):
        cache.clear()
        self.business, (self.branch,), self.owner, _ = make_business()
        self.c = client_for(self.owner)
        v = make_variant(self.business, article="OLD")
        put_stock(self.branch, v, 10)
        age(v, 65)

    @override_settings(GEMINI_API_KEY="")
    def test_not_configured(self):
        r = self.c.post("/api/insights/recommendations/summary/")
        self.assertEqual((r.status_code, r.data["code"]), (503, "ai_not_configured"))
        # Tavsiyalar AI'siz ham ishlaydi.
        self.assertEqual(self.c.get("/api/insights/recommendations/").status_code, 200)

    @override_settings(GEMINI_API_KEY="test-key")
    def test_summary_sends_only_aggregates_and_is_cached(self):
        answer = {"candidates": [{"content": {"parts": [{"text": "Bitta tovar xavf ostida."}]}}]}
        with mock.patch("urllib.request.urlopen", return_value=FakeResponse(answer)) as m:
            r1 = self.c.post("/api/insights/recommendations/summary/")
            r2 = self.c.post("/api/insights/recommendations/summary/")
        self.assertEqual((r1.status_code, r1.data["text"], r1.data["cached"], r2.data["cached"]),
                         (200, "Bitta tovar xavf ostida.", False, True))
        self.assertEqual(m.call_count, 1)
        request = m.call_args[0][0]
        self.assertEqual(request.get_header("X-goog-api-key"), "test-key")
        sent = request.data.decode()
        self.assertIn("Futbolka OLD", sent)
        self.assertNotIn(self.business.name, sent)  # do'kon nomi yuborilmaydi

    @override_settings(GEMINI_API_KEY="test-key")
    def test_network_error_is_friendly(self):
        import urllib.error
        with mock.patch("urllib.request.urlopen", side_effect=urllib.error.URLError("offline")):
            r = self.c.post("/api/insights/recommendations/summary/")
        self.assertEqual((r.status_code, r.data["code"]), (503, "ai_unavailable"))

    @override_settings(GEMINI_API_KEY="test-key", GEMINI_MODEL="band-model, zaxira-model")
    def test_falls_back_to_next_model_when_busy_or_retired(self):
        import io
        import urllib.error

        def err(code):
            return urllib.error.HTTPError("u", code, "x", {}, io.BytesIO(b"{}"))

        answer = {"candidates": [{"content": {"parts": [{"text": "Xulosa"}]}}]}
        for first in (err(503), err(404), TimeoutError("sekin")):
            cache.clear()
            with mock.patch("urllib.request.urlopen", side_effect=[first, FakeResponse(answer)]) as m:
                r = self.c.post("/api/insights/recommendations/summary/")
            self.assertEqual((r.status_code, r.data["text"], r.data["model"]), (200, "Xulosa", "zaxira-model"))
            self.assertIn("zaxira-model", m.call_args[0][0].full_url)

        cache.clear()
        with mock.patch("urllib.request.urlopen", side_effect=[err(503), err(503)]):
            r = self.c.post("/api/insights/recommendations/summary/")
        self.assertEqual((r.status_code, r.data["code"]), (503, "ai_busy"))

    @override_settings(GEMINI_API_KEY="test-key", GEMINI_MODEL="eski-model")
    def test_unknown_model_explains_what_to_change(self):
        import io
        import urllib.error
        err = urllib.error.HTTPError("u", 404, "nf", {}, io.BytesIO(b"{}"))
        with mock.patch("urllib.request.urlopen", side_effect=err):
            r = self.c.post("/api/insights/recommendations/summary/")
        self.assertEqual((r.status_code, r.data["code"]), (503, "ai_model"))
        self.assertIn("GEMINI_MODEL", r.data["detail"])
