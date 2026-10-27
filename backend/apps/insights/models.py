from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.common.models import TimeStampedModel


class RiskSettings(TimeStampedModel):
    """Xavf qoidalari chegaralari. Har bir biznes o'zi sozlaydi: 30 kun hamma tovar uchun universal emas."""

    business = models.OneToOneField("accounts.Business", on_delete=models.CASCADE, related_name="risk_settings")
    no_sale_days = models.PositiveSmallIntegerField(
        "Sotuvsiz kunlar chegarasi", default=30, validators=[MinValueValidator(7), MaxValueValidator(365)])
    sales_window_days = models.PositiveSmallIntegerField(
        "Sotuv sur'ati hisoblanadigan davr (kun)", default=30, validators=[MinValueValidator(7), MaxValueValidator(180)])
    min_sales_for_velocity = models.PositiveSmallIntegerField(
        "Sur'at hisoblash uchun minimal sotuv (dona)", default=3, validators=[MinValueValidator(1), MaxValueValidator(100)])
    overstock_cover_days = models.PositiveSmallIntegerField(
        "Ortiqcha zaxira chegarasi (necha kunga yetadi)", default=90,
        validators=[MinValueValidator(14), MaxValueValidator(730)])
    season_warning_days = models.PositiveSmallIntegerField(
        "Mavsum tugashidan oldin ogohlantirish (kun)", default=21, validators=[MinValueValidator(7), MaxValueValidator(90)])

    @classmethod
    def for_business(cls, business):
        obj, _ = cls.objects.get_or_create(business=business)
        return obj
