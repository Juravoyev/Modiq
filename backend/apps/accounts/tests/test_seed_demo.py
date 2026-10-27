import io

from django.core.management import call_command
from django.db.models import Sum
from django.test import TestCase

from apps.accounts.models import Business
from apps.discounts.models import Discount
from apps.inventory.models import Stock, StockMovement


class SeedDemoTests(TestCase):
    def test_seed_creates_consistent_data_and_reset_works(self):
        call_command("seed_demo", stdout=io.StringIO())
        call_command("seed_demo", "--reset", stdout=io.StringIO())
        self.assertEqual(Business.objects.count(), 1)
        biz = Business.objects.get()
        # Har bir qoldiq jurnal yig'indisiga teng bo'lishi kerak
        for stock in Stock.objects.filter(business=biz):
            total = StockMovement.objects.filter(branch=stock.branch, variant=stock.variant).aggregate(
                s=Sum("quantity_delta"))["s"]
            self.assertEqual(stock.quantity, total, stock)
        # Bitta tasdiqlangan va bitta tannarxdan past qoralama chegirma
        self.assertEqual(Discount.objects.filter(business=biz, status="approved").count(), 1)
        self.assertTrue(Discount.objects.get(business=biz, status="draft").below_cost)
