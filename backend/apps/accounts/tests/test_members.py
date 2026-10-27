from django.test import TestCase

from apps.accounts.models import Branch, Membership
from apps.common.testing import client_for, make_business, make_member


class MemberTests(TestCase):
    def setUp(self):
        self.business, (self.a, self.b), self.owner, self.owner_m = make_business(branches=("A", "B"))
        self.c = client_for(self.owner)

    def test_owner_adds_cashier_and_assigns_branch(self):
        r = self.c.post("/api/auth/members/", {"phone": "+998935550000", "password": "Sotuvchi-123", "role": "cashier",
                                               "branch_ids": [self.a.id]}, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        mid = r.data["id"]
        r = self.c.patch(f"/api/auth/members/{mid}/", {"branch_ids": [self.b.id], "is_active": False}, format="json")
        self.assertEqual(r.status_code, 200, r.data)
        m = Membership.objects.get(pk=mid)
        self.assertEqual(list(m.branches.all()), [self.b])
        self.assertFalse(m.user.is_active)

    def test_cannot_edit_owner_or_assign_foreign_branch(self):
        self.assertEqual(self.c.patch(f"/api/auth/members/{self.owner_m.id}/", {"role": "cashier"},
                                      format="json").status_code, 400)
        other, *_ = make_business()
        foreign = Branch.objects.create(business=other, name="X")
        _, m = make_member(self.business, Membership.Role.CASHIER, [self.a])
        r = self.c.patch(f"/api/auth/members/{m.id}/", {"branch_ids": [foreign.id]}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_cashier_cannot_manage_members(self):
        cashier, _ = make_member(self.business, Membership.Role.CASHIER, [self.a])
        self.assertEqual(client_for(cashier).get("/api/auth/members/").status_code, 403)
