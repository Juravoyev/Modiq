from django.conf import settings
from django.db import models
from django.db.models import F, Q

from apps.common.models import BusinessOwnedModel

MONEY = {"max_digits": 14, "decimal_places": 2}


class Discount(BusinessOwnedModel):
    """Bitta variant uchun muddatli chegirma. Faqat tasdiqlangan va muddati kelgan chegirma kassada qo'llanadi."""

    class Kind(models.TextChoices):
        PERCENT = "percent", "Foiz"
        FIXED_PRICE = "fixed_price", "Yangi narx"

    class Status(models.TextChoices):
        DRAFT = "draft", "Qoralama"
        APPROVED = "approved", "Tasdiqlangan"
        CANCELLED = "cancelled", "Bekor qilingan"

    variant = models.ForeignKey("catalog.ProductVariant", on_delete=models.PROTECT, related_name="discounts")
    kind = models.CharField(max_length=16, choices=Kind.choices)
    value = models.DecimalField("Foiz yoki yangi narx", **MONEY)
    # Yaratilgan paytdagi narxlar nusxasi: keyin tovar narxi o'zgarsa ham tarix to'g'ri qoladi.
    price_before = models.DecimalField("Chegirmagacha narx", **MONEY)
    price_after = models.DecimalField("Chegirmadan keyingi narx", **MONEY)
    unit_cost = models.DecimalField("Xarid narxi", **MONEY)
    below_cost = models.BooleanField(default=False)
    starts_on = models.DateField("Boshlanish sanasi")
    ends_on = models.DateField("Tugash sanasi")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    note = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                    related_name="+")
    approved_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-starts_on", "-id"]
        constraints = [
            models.CheckConstraint(condition=Q(ends_on__gte=F("starts_on")), name="discount_dates_ordered"),
            models.CheckConstraint(condition=Q(value__gt=0, price_after__gte=0), name="discount_amounts_valid"),
        ]
        indexes = [models.Index(fields=["business", "variant", "status", "starts_on"])]

    def __str__(self):
        return f"{self.variant_id}: {self.price_before} -> {self.price_after}"

    def is_active_on(self, day) -> bool:
        return self.status == self.Status.APPROVED and self.starts_on <= day <= self.ends_on
