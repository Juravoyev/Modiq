from django.core.validators import MaxValueValidator
from django.db import models
from django.db.models import Q

from apps.common.models import BusinessOwnedModel


class CustomerGroup(BusinessOwnedModel):
    """Imtiyoz toifasi (masalan, "Doimiy mijoz 5%", "VIP 10%"). Chegirma mijozga doimiy beriladi.

    Aksiya bilan ustma-ust qo'shilmaydi: kassada ikkisidan mijoz uchun foydalirog'i olinadi.
    """

    name = models.CharField("Nomi", max_length=100)
    discount_percent = models.PositiveSmallIntegerField("Chegirma, %", validators=[MaxValueValidator(50)])

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["business", "name"], name="uniq_customer_group_name_per_business"),
            models.CheckConstraint(condition=Q(discount_percent__lte=50), name="customer_group_percent_max_50"),
        ]
        ordering = ["discount_percent", "name"]

    def __str__(self):
        return f"{self.name} ({self.discount_percent}%)"


class Customer(BusinessOwnedModel):
    """Do'kon mijozi. Kassada telefon raqami bilan topiladi."""

    phone = models.CharField("Telefon", max_length=13)
    full_name = models.CharField("Ismi", max_length=150, blank=True)
    # Bo'sh — oddiy mijoz (imtiyozsiz). Toifani faqat egasi yoki menejer o'zgartiradi.
    group = models.ForeignKey(CustomerGroup, null=True, blank=True, on_delete=models.PROTECT, related_name="customers")
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["business", "phone"], name="uniq_customer_phone_per_business"),
        ]
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.full_name or self.phone}"

    @property
    def discount_percent(self) -> int:
        return self.group.discount_percent if self.group_id else 0
