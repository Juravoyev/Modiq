from django.conf import settings
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


class BonusTransaction(BusinessOwnedModel):
    """Bonus jurnali (StockMovement kabi): balans har doim shu yozuvlar yig'indisi, alohida saqlanmaydi.

    Yangi yig'ilgan bonus qaytarish muddati (24 soat) o'tgach ishlatiladi (available_at).
    Shunda tovar qaytarilsa, bonus hali sarflanmagan bo'ladi va balans manfiyga tushmaydi.
    """

    class Kind(models.TextChoices):
        EARN = "earn", "Xariddan yig'ildi"
        SPEND = "spend", "Xaridda ishlatildi"
        REFUND = "refund", "Qaytarishda qaytarildi"
        REVOKE = "revoke", "Qaytarish sababli bekor qilindi"

    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="bonus_transactions")
    kind = models.CharField(max_length=16, choices=Kind.choices)
    # Musbat — balansga qo'shiladi, manfiy — ayiriladi. Butun so'm.
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    sale = models.ForeignKey("sales.Sale", null=True, blank=True, on_delete=models.PROTECT, related_name="bonus_transactions")
    sale_return = models.ForeignKey("sales.SaleReturn", null=True, blank=True, on_delete=models.PROTECT,
                                    related_name="bonus_transactions")
    available_at = models.DateTimeField("Ishlatish mumkin bo'lgan vaqt")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")

    class Meta:
        constraints = [models.CheckConstraint(condition=~Q(amount=0), name="bonus_amount_non_zero")]
        indexes = [models.Index(fields=["customer", "available_at"])]
        ordering = ["-created_at", "-id"]
