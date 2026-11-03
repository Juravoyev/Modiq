from django.test import TestCase

from apps.accounts.models import Branch, Membership
from apps.common.testing import client_for, make_business, make_member


class StaffTests(TestCase):
    def setUp(self):
        self.business, self.branches, self.owner, self.owner_m = make_business(branches=("Markaz", "Chilonzor"))

    def test_owner_adds_and_edits_cashier(self):
        c = client_for(self.owner)
        r = c.post("/api/auth/members/", {"phone": "901234500", "password": "Kassir-parol-1", "full_name": "Ali",
                                          "role": "cashier", "branch_ids": [self.branches[0].id]}, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        member_id = r.data["id"]

        r = c.patch(f"/api/auth/members/{member_id}/", {"role": "manager", "branch_ids": [self.branches[1].id],
                                                         "password": "Yangi-parol-22"}, format="json")
        self.assertEqual(r.status_code, 200, r.data)
        m = Membership.objects.get(pk=member_id)
        self.assertEqual(m.role, Membership.Role.MANAGER)
        self.assertEqual(list(m.branches.all()), [self.branches[1]])
        self.assertTrue(m.user.check_password("Yangi-parol-22"))

    def test_manager_can_list_but_not_edit_staff(self):
        manager, _ = make_member(self.business, Membership.Role.MANAGER)
        c = client_for(manager)
        self.assertEqual(c.get("/api/auth/members/").status_code, 200)
        r = c.post("/api/auth/members/", {"phone": "901234501", "password": "Kassir-parol-1", "role": "cashier"},
                   format="json")
        self.assertEqual(r.status_code, 403)

    def test_cashier_cannot_see_staff(self):
        cashier, _ = make_member(self.business, Membership.Role.CASHIER, self.branches[:1])
        self.assertEqual(client_for(cashier).get("/api/auth/members/").status_code, 403)

    def test_owner_role_cannot_be_changed(self):
        r = client_for(self.owner).patch(f"/api/auth/members/{self.owner_m.id}/", {"role": "cashier"}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_other_business_member_not_visible(self):
        other_business, *_ = make_business()
        _, other_m = make_member(other_business, Membership.Role.CASHIER)
        r = client_for(self.owner).patch(f"/api/auth/members/{other_m.id}/", {"is_active": False}, format="json")
        self.assertEqual(r.status_code, 404)


class BranchTests(TestCase):
    def setUp(self):
        self.business, self.branches, self.owner, _ = make_business(branches=("Markaz", "Chilonzor"))

    def test_create_and_deactivate_branch(self):
        c = client_for(self.owner)
        r = c.post("/api/auth/branches/", {"name": "Ombor", "kind": "warehouse"}, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        r = c.patch(f"/api/auth/branches/{r.data['id']}/", {"is_active": False}, format="json")
        self.assertEqual(r.status_code, 200, r.data)
        # Nofaol filial ro'yxatda qoladi, aks holda uni qayta yoqib bo'lmaydi.
        names = [b["name"] for b in c.get("/api/auth/branches/").data["results"]]
        self.assertIn("Ombor", names)

    def test_duplicate_name_rejected(self):
        r = client_for(self.owner).post("/api/auth/branches/", {"name": "markaz"}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("name", r.data)

    def test_last_active_branch_cannot_be_closed(self):
        c = client_for(self.owner)
        self.assertEqual(c.patch(f"/api/auth/branches/{self.branches[1].id}/", {"is_active": False},
                                 format="json").status_code, 200)
        r = c.patch(f"/api/auth/branches/{self.branches[0].id}/", {"is_active": False}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertTrue(Branch.objects.get(pk=self.branches[0].id).is_active)

    def test_cashier_sees_only_own_branch_and_cannot_create(self):
        cashier, _ = make_member(self.business, Membership.Role.CASHIER, self.branches[:1])
        c = client_for(cashier)
        r = c.get("/api/auth/branches/")
        self.assertEqual([b["id"] for b in r.data["results"]], [self.branches[0].id])
        self.assertEqual(c.post("/api/auth/branches/", {"name": "X"}, format="json").status_code, 403)
