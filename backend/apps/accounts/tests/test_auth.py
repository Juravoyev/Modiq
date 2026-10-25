from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import Membership, User


class RegisterLoginTests(TestCase):
    def test_register_creates_owner_business_and_branch_then_login_by_phone(self):
        c = APIClient()
        r = c.post("/api/auth/register/", {"phone": "90 123-45-67", "password": "Kuchli-parol-9",
                                           "business_name": "Moda Uz"}, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        user = User.objects.get(phone="+998901234567")
        self.assertNotEqual(user.password, "Kuchli-parol-9")  # parol hash ko'rinishida
        self.assertEqual(user.membership.role, Membership.Role.OWNER)
        self.assertEqual(user.membership.business.branches.count(), 1)

        r = c.post("/api/auth/login/", {"phone": "+998 90 123 45 67", "password": "Kuchli-parol-9"}, format="json")
        self.assertEqual(r.status_code, 200, r.data)
        self.assertIn("access", r.data)

        c.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")
        me = c.get("/api/auth/me/")
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.data["business"]["name"], "Moda Uz")

    def test_duplicate_phone_rejected(self):
        User.objects.create_user(phone="+998901112233", password="x-Parol-123")
        r = APIClient().post("/api/auth/register/", {"phone": "901112233", "password": "Kuchli-parol-9",
                                                     "business_name": "B"}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("phone", r.data)

    def test_wrong_password_rejected(self):
        User.objects.create_user(phone="+998901112233", password="x-Parol-123")
        r = APIClient().post("/api/auth/login/", {"phone": "+998901112233", "password": "wrong"}, format="json")
        self.assertEqual(r.status_code, 401)
