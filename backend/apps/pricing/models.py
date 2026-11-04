from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator
from django.db import models
from django.db.models import Q

from apps.common.models import BusinessOwnedModel, TimeStampedModel

MONEY = {"max_digits": 14, "decimal_places": 2}
ZERO = Decimal("0.00")
# Foizli chegirma butun so'mgacha yaxlitlanadi (chekda tiyin chiqmaydi).
SOUM = Decimal("1")


class PricingSettings(TimeStampedModel):
    """Biznesning chegirma sozlamalari. Birinchi murojaatda standart qiymatlar bilan yaratiladi."""

    business = models.OneToOneField("accounts.Business", on_delete=models.CASCADE, related_name="pricing_settings")
    # Sotuvchi qo'lda beradigan chegirmaning yuqori chegarasi (qator summasidan foiz).
    # Undan kattasini faqat egasi yoki menejer bera oladi.
    cashier_max_discount_percent = models.PositiveSmallIntegerField(
        "Sotuvchining qo'lda chegirma chegarasi, %", default=10, validators=[MaxValueValidator(100)])
    # Bonus (keshbek): mijoz pul bilan to'lagan summaning foizi bonus bo'lib yig'iladi, 1 ball = 1 so'm.
    bonus_enabled = models.BooleanField("Bonus tizimi yoqilgan", default=True)
    bonus_percent = models.PositiveSmallIntegerField("Bonus, %", default=3, validators=[MaxValueValidator(20)])
    # Chekning ko'pi bilan shuncha foizini bonus bilan to'lash mumkin.
    bonus_max_share_percent = models.PositiveSmallIntegerField(
        "Bonus bilan to'lash chegarasi, %", default=35, validators=[MaxValueValidator(100)])

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(cashier_max_discount_percent__lte=100),
                                   name="pricing_cashier_discount_percent_valid"),
            models.CheckConstraint(condition=Q(bonus_percent__lte=20, bonus_max_share_percent__lte=100),
                                   name="pricing_bonus_settings_valid"),
        ]

    @classmethod
    def for_business(cls, business):
        obj, _ = cls.objects.get_or_create(business=business)
        return obj


class Promotion(BusinessOwnedModel):
    """Muddatli aksiya. Muddat ichida kassada avtomatik qo'llanadi.

    Bir tovarga bir nechta aksiya to'g'ri kelsa, mijoz uchun eng foydalisi tanlanadi (ustma-ust qo'shilmaydi).
    Aksiya narxni hech qachon tannarxdan pastga tushirmaydi.
    """

    class Kind(models.TextChoices):
        PERCENT = "percent", "Foiz"
        AMOUNT = "amount", "Summa"

    class Scope(models.TextChoices):
        ALL = "all", "Barcha tovarlar"
        CATEGORY = "category", "Kategoriya"
        SEASON = "season", "Mavsum"
        PRODUCTS = "products", "Tanlangan tovarlar"

    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Boshlanmagan"
        ACTIVE = "active", "Faol"
        ENDED = "ended", "Tugagan"
        STOPPED = "stopped", "To'xtatilgan"

    name = models.CharField("Nomi", max_length=150)
    kind = models.CharField(max_length=16, choices=Kind.choices, default=Kind.PERCENT)
    # Foiz (1-90) yoki bitta dona uchun summa.
    value = models.DecimalField(**MONEY)
    scope = models.CharField(max_length=16, choices=Scope.choices, default=Scope.ALL)
    category = models.ForeignKey("catalog.Category", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    season = models.ForeignKey("catalog.Season", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    products = models.ManyToManyField("catalog.Product", blank=True, related_name="promotions")
    starts_on = models.DateField("Boshlanish sanasi")
    ends_on = models.DateField("Tugash sanasi (shu kun ham kiradi)")
    # False — muddatidan oldin qo'lda to'xtatilgan.
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(value__gt=0), name="promotion_value_positive"),
            models.CheckConstraint(condition=Q(kind="amount") | Q(value__lte=90), name="promotion_percent_max_90"),
            models.CheckConstraint(condition=Q(ends_on__gte=models.F("starts_on")), name="promotion_dates_valid"),
        ]
        indexes = [models.Index(fields=["business", "starts_on", "ends_on"])]
        ordering = ["-starts_on", "-id"]

    def __str__(self):
        return self.name

    def status_on(self, today) -> str:
        if not self.is_active:
            return self.Status.STOPPED
        if today < self.starts_on:
            return self.Status.SCHEDULED
        if today > self.ends_on:
            return self.Status.ENDED
        return self.Status.ACTIVE

    def applies_to(self, product, product_ids_cache=None) -> bool:
        if self.scope == self.Scope.ALL:
            return True
        if self.scope == self.Scope.CATEGORY:
            return product.category_id is not None and product.category_id == self.category_id
        if self.scope == self.Scope.SEASON:
            return product.season_id is not None and product.season_id == self.season_id
        ids = product_ids_cache if product_ids_cache is not None else {p.id for p in self.products.all()}
        return product.id in ids

    def unit_discount(self, price: Decimal) -> Decimal:
        """Bitta dona uchun chegirma (tannarx chegarasi hisobga olinmagan)."""
        if self.kind == self.Kind.PERCENT:
            d = (price * self.value / 100).quantize(SOUM, rounding=ROUND_HALF_UP)
        else:
            d = self.value
        return min(d, price)

    @property
    def label(self) -> str:
        if self.kind == self.Kind.PERCENT:
            return f"{self.name} (−{self.value.normalize():f}%)"
        return f"{self.name} (−{int(self.value):,} so'm)".replace(",", " ")
