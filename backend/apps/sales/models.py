from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.common.models import BusinessOwnedModel, TimeStampedModel

MONEY = {"max_digits": 14, "decimal_places": 2}


class Sale(BusinessOwnedModel):
    """Yakunlangan savdo. Narx va tannarx savdo paytidagi qiymatda saqlanadi (keyin o'zgarmaydi)."""

    class PaymentType(models.TextChoices):
        CASH = "cash", "Naqd"
        CARD = "card", "Karta"
        ONLINE = "online", "Onlayn o'tkazma"

    branch = models.ForeignKey("accounts.Branch", on_delete=models.PROTECT, related_name="sales")
    cashier = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    # Kassa har bir savdo uchun yangi UUID yuboradi. Tarmoq uzilib so'rov qayta yuborilsa,
    # xuddi shu kalit bilan yangi savdo yaratilmaydi va qoldiq ikki marta kamaymaydi.
    idempotency_key = models.UUIDField()
    payment_type = models.CharField(max_length=16, choices=PaymentType.choices, default=PaymentType.CASH)
    subtotal = models.DecimalField("Chegirmasiz summa", **MONEY)
    discount_total = models.DecimalField("Chegirma", **MONEY)
    total = models.DecimalField("Yakuniy summa (tushum)", **MONEY)
    cost_total = models.DecimalField("Tannarx", **MONEY)
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["business", "idempotency_key"], name="uniq_sale_idempotency_key"),
            models.CheckConstraint(condition=Q(total__gte=0, discount_total__gte=0), name="sale_amounts_non_negative"),
        ]
        indexes = [models.Index(fields=["business", "branch", "-created_at"])]
        ordering = ["-created_at", "-id"]

    @property
    def gross_profit(self):
        """Taxminiy yalpi foyda = tushum - tannarx. Boshqa xarajatlar hisobga olinmagan, bu sof foyda emas."""
        return self.total - self.cost_total


class SaleLine(TimeStampedModel):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name="lines")
    variant = models.ForeignKey("catalog.ProductVariant", on_delete=models.PROTECT, related_name="sale_lines")
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(**MONEY)
    discount_amount = models.DecimalField(default=0, **MONEY)
    line_total = models.DecimalField(**MONEY)
    unit_cost = models.DecimalField(**MONEY)
    below_cost = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(quantity__gt=0), name="sale_line_quantity_positive"),
            models.CheckConstraint(condition=Q(discount_amount__gte=0, line_total__gte=0),
                                   name="sale_line_amounts_non_negative"),
        ]
