import io
import json
import urllib.error
from unittest import mock

from django.core.cache import cache
from django.test import TestCase, override_settings

from apps.accounts.models import Membership
from apps.assistant.services import system_prompt
from apps.common.testing import client_for, make_business, make_member


class FakeStream:
    """Gemini streamGenerateContent?alt=sse javobi."""

    def __init__(self, pieces):
        self.lines = [f"data: {json.dumps({'candidates': [{'content': {'parts': [{'text': p}]}}]})}\r\n".encode()
                      for p in pieces]

    def __iter__(self):
        return iter(self.lines)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def read(response) -> str:
    return b"".join(response.streaming_content).decode()


@override_settings(GEMINI_API_KEY="test-key", GEMINI_MODEL="tez-model,zaxira-model", ASSISTANT_HOURLY_LIMIT=30)
class AssistantTests(TestCase):
    def setUp(self):
        cache.clear()
        self.business, (self.branch,), self.owner, self.owner_m = make_business()
        self.cashier, self.cashier_m = make_member(self.business, Membership.Role.CASHIER, [self.branch])
        self.c = client_for(self.cashier)

    def ask(self, question="Qanday sotaman?", page="/", history=None, client=None):
        return (client or self.c).post("/api/assistant/ask/", {"question": question, "page": page,
                                                               "history": history or []}, format="json")

    def test_topics_depend_on_role(self):
        ids = lambda c: {t["id"] for t in c.get("/api/assistant/topics/").data["topics"]}  # noqa: E731
        cashier = ids(self.c)
        self.assertIn("sale", cashier)
        self.assertFalse({"receipt", "staff", "promotion", "return_approve"} & cashier)
        manager_user, _ = make_member(self.business, Membership.Role.MANAGER)
        manager = ids(client_for(manager_user))
        self.assertTrue({"receipt", "promotion", "return_approve"} <= manager)
        self.assertNotIn("staff", manager)  # xodim qo'shish faqat egasiga
        self.assertIn("staff", ids(client_for(self.owner)))
        self.cashier_m.can_approve_returns = True
        self.cashier_m.save()
        self.assertIn("return_approve", ids(self.c))

    def test_system_prompt_is_role_and_page_aware(self):
        prompt = system_prompt(self.cashier_m, "/stock")
        self.assertIn("«Qoldiq» sahifasida", prompt)
        self.assertIn("Savdo qilish", prompt)
        self.assertNotIn("«+ Yangi kirim»", prompt)  # menejer qo'llanmasi sotuvchiga berilmaydi
        self.assertIn("Kirim (tovar qabul qilish)", prompt)  # lekin bu ruxsat etilmagan ish ekani aytiladi
        self.assertIn("sotuvchi", prompt)

    def test_streams_answer_and_sends_no_business_data(self):
        with mock.patch("urllib.request.urlopen", return_value=FakeStream(["1. «Kassa»ni ", "oching."])) as m:
            r = self.ask()
        self.assertEqual(r.status_code, 200)
        self.assertEqual(read(r), "1. «Kassa»ni oching.")
        req = m.call_args[0][0]
        self.assertIn("tez-model:streamGenerateContent?alt=sse", req.full_url)
        sent = req.data.decode()
        self.assertIn("Savdo qilish", sent)
        self.assertNotIn(self.business.name, sent)
        self.assertNotIn(self.cashier.phone, sent)

    def test_same_question_is_answered_from_cache(self):
        with mock.patch("urllib.request.urlopen", return_value=FakeStream(["Javob"])) as m:
            self.assertEqual(read(self.ask("Qanday sotaman?")), "Javob")
            self.assertEqual(read(self.ask("qanday   sotaman")), "Javob")
        self.assertEqual(m.call_count, 1)

    def test_history_is_sent_and_not_cached(self):
        history = [{"role": "user", "text": "Salom"}, {"role": "assistant", "text": "Assalomu alaykum"}]
        with mock.patch("urllib.request.urlopen", side_effect=lambda *a, **k: FakeStream(["Ok"])) as m:
            read(self.ask(history=history))
            read(self.ask(history=history))
        self.assertEqual(m.call_count, 2)
        body = json.loads(m.call_args[0][0].data)
        self.assertEqual([x["role"] for x in body["contents"]], ["user", "model", "user"])

    def test_falls_back_when_first_model_busy(self):
        busy = urllib.error.HTTPError("u", 503, "busy", {}, io.BytesIO(b"{}"))
        with mock.patch("urllib.request.urlopen", side_effect=[busy, FakeStream(["Zaxira javob"])]) as m:
            r = self.ask()
        self.assertEqual(read(r), "Zaxira javob")
        self.assertIn("zaxira-model", m.call_args[0][0].full_url)

    def test_all_busy_returns_json_error(self):
        busy = urllib.error.HTTPError("u", 503, "busy", {}, io.BytesIO(b"{}"))
        with mock.patch("urllib.request.urlopen", side_effect=[busy, busy]):
            r = self.ask()
        self.assertEqual((r.status_code, r.data["code"]), (503, "ai_busy"))

    @override_settings(GEMINI_API_KEY="")
    def test_not_configured_but_topics_work(self):
        r = self.ask()
        self.assertEqual((r.status_code, r.data["code"]), (503, "ai_not_configured"))
        r = self.c.get("/api/assistant/topics/")
        self.assertEqual((r.status_code, r.data["ai_configured"]), (200, False))

    @override_settings(ASSISTANT_HOURLY_LIMIT=2)
    def test_hourly_limit(self):
        with mock.patch("urllib.request.urlopen", side_effect=lambda *a, **k: FakeStream(["Ok"])):
            self.assertEqual(self.ask("1").status_code, 200)
            self.assertEqual(self.ask("2").status_code, 200)
            r = self.ask("3")
        self.assertEqual((r.status_code, r.data["code"]), (429, "assistant_limit"))
        # Boshqa xodimning chegarasi alohida.
        with mock.patch("urllib.request.urlopen", return_value=FakeStream(["Ok"])):
            self.assertEqual(self.ask("1", client=client_for(self.owner)).status_code, 200)

    def test_validation(self):
        self.assertEqual(self.ask("x" * 501).status_code, 400)
        self.assertEqual(self.ask("").status_code, 400)

    def test_requires_login(self):
        from rest_framework.test import APIClient
        self.assertEqual(APIClient().post("/api/assistant/ask/", {"question": "x"}, format="json").status_code, 401)
