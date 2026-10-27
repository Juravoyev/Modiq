import io
import json
import urllib.error
import uuid
from unittest import mock

from django.core.cache import cache
from django.test import TestCase, override_settings

from apps.accounts.models import Membership
from apps.common.testing import client_for, make_business, make_member, make_variant, put_stock


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def gemini_reply(text):
    return FakeResponse(json.dumps({"candidates": [{"content": {"parts": [{"text": text}]}}]}).encode())


class WeeklySummaryTests(TestCase):
    def setUp(self):
        cache.clear()
        self.business, (self.branch,), self.owner, _ = make_business()
        variant = make_variant(self.business, purchase="50000", sale="100000")
        put_stock(self.branch, variant, 10)
        self.c = client_for(self.owner)
        self.c.post("/api/sales/", {"idempotency_key": str(uuid.uuid4()), "branch": self.branch.id,
                                    "lines": [{"variant": variant.id, "quantity": 3}]}, format="json")

    def test_facts_come_from_real_sales(self):
        r = self.c.get("/api/reports/weekly-summary/")
        self.assertEqual(r.status_code, 200)
        week = r.data["facts"]["shu_hafta"]
        self.assertEqual((week["sales_count"], week["items"], week["revenue"], week["gross_profit"]),
                         ("1", "3", "300000.00", "150000.00"))
        self.assertEqual(r.data["facts"]["oldingi_hafta"]["revenue"], "0.00")

    @override_settings(GEMINI_API_KEY="")
    def test_without_key_returns_clear_error_and_facts(self):
        r = self.c.post("/api/reports/weekly-summary/")
        self.assertEqual(r.status_code, 503)
        self.assertEqual(r.data["code"], "not_configured")
        self.assertIn("shu_hafta", r.data["facts"])

    @override_settings(GEMINI_API_KEY="test-key", GEMINI_MODEL="test-model")
    def test_sends_only_facts_and_caches_text(self):
        with mock.patch("urllib.request.urlopen", return_value=gemini_reply("Hafta yaxshi o'tdi.")) as m:
            r1 = self.c.post("/api/reports/weekly-summary/")
            r2 = self.c.post("/api/reports/weekly-summary/")
        self.assertEqual(r1.status_code, 200, r1.data)
        self.assertEqual(r1.data["text"], "Hafta yaxshi o'tdi.")
        self.assertTrue(r2.data["cached"])
        self.assertEqual(m.call_count, 1)
        req = m.call_args.args[0]
        self.assertIn("test-model:generateContent", req.full_url)
        self.assertNotIn("test-key", req.full_url)  # kalit URL da emas, sarlavhada
        sent = json.loads(json.loads(req.data)["contents"][0]["parts"][0]["text"])
        self.assertEqual(sent["shu_hafta"]["revenue"], "300000.00")

    @override_settings(GEMINI_API_KEY="bad")
    def test_provider_error_is_reported(self):
        err = urllib.error.HTTPError("u", 403, "Forbidden", {}, io.BytesIO(b"{}"))
        with mock.patch("urllib.request.urlopen", side_effect=err):
            r = self.c.post("/api/reports/weekly-summary/")
        self.assertEqual(r.status_code, 503)
        self.assertIn("kaliti", r.data["detail"])

    def test_cashier_cannot_use_summary(self):
        cashier, _ = make_member(self.business, Membership.Role.CASHIER, [self.branch])
        self.assertEqual(client_for(cashier).get("/api/reports/weekly-summary/").status_code, 403)

    @override_settings(GEMINI_API_KEY="k")
    def test_busy_service_is_retried_once(self):
        busy = urllib.error.HTTPError("u", 503, "Unavailable", {}, io.BytesIO(b"{}"))
        with mock.patch("urllib.request.urlopen", side_effect=[busy, gemini_reply("Matn.")]) as m, \
                mock.patch("apps.reports.summary.time.sleep"):
            r = self.c.post("/api/reports/weekly-summary/")
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(m.call_count, 2)
