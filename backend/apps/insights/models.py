from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.common.models import BusinessOwnedModel, TimeStampedModel

PERCENT = [MinValueValidator(1), MaxValueValidator(90)]
DAYS = [MinValueValidator(1), MaxValueValidator(730)]


class InsightSettings(TimeStampedModel):
    """Sotilmay qolish xavfi qoidalarining chegaralari. Egasi yoki menejer o'zgartiradi."""

    business = models.OneToOneField("accounts.Business", on_delete=models.CASCADE, related_name="insight_settings")
    # Yuqori xavf: shuncha kun bitta ham sotilmagan.
    no_sale_days = models.PositiveSmallIntegerField(default=60, validators=DAYS)
    high_discount = models.PositiveSmallIntegerField(default=30, validators=PERCENT)
    # O'rta xavf: hozirgi sotilish tezligida qoldiq shuncha kundan ko'proqqa yetadi.
    cover_days_medium = models.PositiveSmallIntegerField(default=90, validators=DAYS)
    medium_discount = models.PositiveSmallIntegerField(default=20, validators=PERCENT)
    # Past xavf.
    cover_days_low = models.PositiveSmallIntegerField(default=60, validators=DAYS)
    low_discount = models.PositiveSmallIntegerField(default=10, validators=PERCENT)
    # Mavsum: tugashiga shuncha kun qolgan (yoki tugagan) bo'lsa va qoldiq sotilib ulgurmasa.
    season_end_days = models.PositiveSmallIntegerField(default=30, validators=DAYS)
    season_discount = models.PositiveSmallIntegerField(default=20, validators=PERCENT)
    # Yangi kelgan tovar baholanmaydi: unga sotilish uchun vaqt kerak.
    min_age_days = models.PositiveSmallIntegerField(default=14, validators=[MaxValueValidator(365)])

    @classmethod
    def for_business(cls, business):
        obj, _ = cls.objects.get_or_create(business=business)
        return obj


class Dismissal(BusinessOwnedModel):
    """Menejer tavsiyani rad etgan: tovar shu sanagacha tavsiyalarda ko'rsatilmaydi."""

    product = models.ForeignKey("catalog.Product", on_delete=models.CASCADE, related_name="+")
    until = models.DateField()
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["business", "product"], name="uniq_dismissal_product")]
