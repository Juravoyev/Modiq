from django.conf import settings
from django.db import models
from django.db.models import F, Q

from apps.common.models import BusinessOwnedModel, TimeStampedModel

MONEY = {"max_digits": 14, "decimal_places": 2}


class Stock(BusinessOwnedModel):
    """Bitta filialdagi bitta variant qoldig'i. Faqat services.change_stock orqali o'zgartiriladi."""

    branch = models.ForeignKey("accounts.Branch", on_delete=models.CASCADE, related_name="stocks")
    variant = models.ForeignKey("catalog.ProductVariant", on_delete=models.CASCADE, related_name="stocks")
    quantity = models.IntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["branch", "variant"], name="uniq_stock_branch_variant"),
            # Manfiy qoldiq ma'lumotlar bazasi darajasida ham taqiqlangan.
            models.CheckConstraint(condition=Q(quantity__gte=0), name="stock_quantity_non_negative"),
        ]

    def __str__(self):
        return f"{self.variant} @ {self.branch}: {self.quantity}"


class StockMovement(BusinessOwnedModel):
    """Qoldiqning har bir o'zgarishi yoziladigan o'zgarmas jurnal (audit trail)."""

    class Kind(models.TextChoices):
        RECEIPT = "receipt", "Kirim"
        SALE = "sale", "Savdo"
        TRANSFER_OUT = "transfer_out", "Ko'chirish (chiqim)"
        TRANSFER_IN = "transfer_in", "Ko'chirish (kirim)"
        TRANSFER_RETURN = "transfer_return", "Ko'chirish bekor qilindi"
        ADJUSTMENT = "adjustment", "Tuzatish"

    branch = models.ForeignKey("accounts.Branch", on_delete=models.CASCADE, related_name="+")
    variant = models.ForeignKey("catalog.ProductVariant", on_delete=models.CASCADE, related_name="movements")
    kind = models.CharField(max_length=20, choices=Kind.choices)
    quantity_delta = models.IntegerField()
    balance_after = models.IntegerField()
    ref_type = models.CharField(max_length=20, blank=True)
    ref_id = models.BigIntegerField(null=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["business", "variant", "-created_at"]),
            models.Index(fields=["business", "kind", "-created_at"]),
            models.Index(fields=["ref_type", "ref_id"]),
        ]
        ordering = ["-created_at", "-id"]


class Receipt(BusinessOwnedModel):
    """Kirim hujjati (yetkazib beruvchidan kelgan tovar)."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Qoralama"
        CONFIRMED = "confirmed", "Tasdiqlangan"
        CANCELLED = "cancelled", "Bekor qilingan"

    branch = models.ForeignKey("accounts.Branch", on_delete=models.PROTECT, related_name="receipts")
    supplier_name = models.CharField("Yetkazib beruvchi", max_length=200, blank=True)
    document_number = models.CharField("Hujjat raqami", max_length=50, blank=True)
    document_date = models.DateField("Sana")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    note = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    confirmed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                     related_name="+")
    confirmed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-document_date", "-id"]
        indexes = [models.Index(fields=["business", "status", "-document_date"])]


class ReceiptLine(TimeStampedModel):
    receipt = models.ForeignKey(Receipt, on_delete=models.CASCADE, related_name="lines")
    variant = models.ForeignKey("catalog.ProductVariant", on_delete=models.PROTECT, related_name="+")
    quantity = models.PositiveIntegerField()
    purchase_price = models.DecimalField(**MONEY)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["receipt", "variant"], name="uniq_receipt_line_variant"),
            models.CheckConstraint(condition=Q(quantity__gt=0), name="receipt_line_quantity_positive"),
            models.CheckConstraint(condition=Q(purchase_price__gte=0), name="receipt_line_price_non_negative"),
        ]


class Transfer(BusinessOwnedModel):
    """Filiallar o'rtasida ko'chirish: draft -> sent -> received, yoki cancelled."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Qoralama"
        SENT = "sent", "Jo'natilgan"
        RECEIVED = "received", "Qabul qilingan"
        CANCELLED = "cancelled", "Bekor qilingan"

    from_branch = models.ForeignKey("accounts.Branch", on_delete=models.PROTECT, related_name="transfers_out")
    to_branch = models.ForeignKey("accounts.Branch", on_delete=models.PROTECT, related_name="transfers_in")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    note = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    sent_at = models.DateTimeField(null=True, blank=True)
    received_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=~Q(from_branch=F("to_branch")), name="transfer_branches_differ"),
        ]
        ordering = ["-created_at", "-id"]


class TransferLine(TimeStampedModel):
    transfer = models.ForeignKey(Transfer, on_delete=models.CASCADE, related_name="lines")
    variant = models.ForeignKey("catalog.ProductVariant", on_delete=models.PROTECT, related_name="+")
    quantity = models.PositiveIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["transfer", "variant"], name="uniq_transfer_line_variant"),
            models.CheckConstraint(condition=Q(quantity__gt=0), name="transfer_line_quantity_positive"),
        ]
