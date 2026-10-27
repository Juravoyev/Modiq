"""Chegirma qoidalari.

* Chegirma qoralama sifatida yaratiladi va menejer tasdiqlagandan keyingina kassada qo'llanadi.
* Xarid narxidan past narx xavfli holat: uni faqat menejer, alohida tasdiq bilan tasdiqlay oladi.
* Bir variantda bir vaqtda faqat bitta tasdiqlangan chegirma bo'lishi mumkin.
"""
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import Discount

CENT = Decimal("0.01")


def calculate_price(price_before: Decimal, kind: str, value: Decimal) -> Decimal:
    if kind == Discount.Kind.PERCENT:
        if not (Decimal("0") < value < Decimal("100")):
            raise ValidationError({"value": "Foiz 0 dan katta va 100 dan kichik bo'lishi kerak."})
        return (price_before * (Decimal("100") - value) / Decimal("100")).quantize(CENT, ROUND_HALF_UP)
    if value >= price_before:
        raise ValidationError({"value": "Yangi narx hozirgi narxdan past bo'lishi kerak."})
    return value.quantize(CENT, ROUND_HALF_UP)


def create_discount(*, business, user, variant, kind, value, starts_on, ends_on, note=""):
    if ends_on < starts_on:
        raise ValidationError({"ends_on": "Tugash sanasi boshlanish sanasidan oldin bo'lmasligi kerak."})
    if ends_on < timezone.localdate():
        raise ValidationError({"ends_on": "Muddati o'tib bo'lgan chegirmani yaratib bo'lmaydi."})
    price_before = variant.effective_sale_price
    price_after = calculate_price(price_before, kind, value)
    unit_cost = variant.effective_purchase_price
    return Discount.objects.create(
        business=business, variant=variant, kind=kind, value=value, price_before=price_before,
        price_after=price_after, unit_cost=unit_cost, below_cost=price_after < unit_cost,
        starts_on=starts_on, ends_on=ends_on, note=note, created_by=user,
    )


@transaction.atomic
def approve_discount(discount_id, *, user, membership, allow_below_cost=False):
    discount = Discount.objects.select_for_update().get(pk=discount_id)
    if discount.status != Discount.Status.DRAFT:
        raise ValidationError({"detail": "Faqat qoralama chegirmani tasdiqlash mumkin.", "code": "invalid_status"})
    if discount.ends_on < timezone.localdate():
        raise ValidationError({"detail": "Chegirma muddati o'tib ketgan.", "code": "expired"})
    if discount.below_cost:
        if not membership.is_manager:
            raise ValidationError({"detail": "Xarid narxidan past chegirmani faqat menejer tasdiqlaydi.",
                                   "code": "below_cost"})
        if not allow_below_cost:
            raise ValidationError({"detail": f"Yangi narx ({discount.price_after}) xarid narxidan "
                                             f"({discount.unit_cost}) past. Har bir sotuv zarar keltiradi. "
                                             "Davom etish uchun buni alohida tasdiqlang.", "code": "below_cost"})
    # Variant bo'yicha qatorlarni qulflaymiz: ikki chegirma parallel tasdiqlanib, bir-birini qoplab qolmasin.
    overlapping = (
        Discount.objects.select_for_update()
        .filter(business=discount.business, variant=discount.variant, status=Discount.Status.APPROVED,
                starts_on__lte=discount.ends_on, ends_on__gte=discount.starts_on)
        .exclude(pk=discount.pk)
    )
    if overlapping.exists():
        other = overlapping.first()
        raise ValidationError({"detail": f"Bu variantda {other.starts_on} – {other.ends_on} oralig'ida boshqa "
                                         "chegirma bor. Muddatlar ustma-ust tushmasligi kerak.", "code": "overlap"})
    discount.status = Discount.Status.APPROVED
    discount.approved_by = user
    discount.approved_at = timezone.now()
    discount.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])
    return discount


@transaction.atomic
def cancel_discount(discount_id, *, user):
    discount = Discount.objects.select_for_update().get(pk=discount_id)
    if discount.status == Discount.Status.CANCELLED:
        raise ValidationError({"detail": "Chegirma allaqachon bekor qilingan.", "code": "invalid_status"})
    discount.status = Discount.Status.CANCELLED
    discount.cancelled_at = timezone.now()
    discount.save(update_fields=["status", "cancelled_at", "updated_at"])
    return discount


def active_discounts(business, day=None):
    day = day or timezone.localdate()
    return Discount.objects.filter(business=business, status=Discount.Status.APPROVED,
                                   starts_on__lte=day, ends_on__gte=day)
