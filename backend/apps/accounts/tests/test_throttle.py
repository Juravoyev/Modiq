from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient


class LoginThrottleTests(TestCase):
    def setUp(self):
        cache.clear()

    def tearDown(self):
        cache.clear()

    def test_too_many_login_attempts_are_blocked(self):
        c = APIClient()
        codes = [c.post("/api/auth/login/", {"phone": "+998901112233", "password": "xato"}, format="json").status_code
                 for _ in range(11)]
        self.assertNotIn(429, codes[:10])
        self.assertEqual(codes[10], 429)
