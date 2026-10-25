from dataclasses import dataclass
from decimal import Decimal

from django.db import IntegrityError, transaction
from rest_framework.exceptions import ValidationError

from apps.inventory.models import StockMovement
from apps.inventory.services import change_stock

from .models import Sale, SaleLine

ZERO = Decimal("0.00")


@dataclass
class LineInput:
    variant: object
    quantity: int
    discount_amount: Decimal = ZERO


def calculate_line(variant, quantity: int, discount_amount: Decimal):
    unit_price = variant.effective_sale_price
    unit_cost = variant.effective_purchase_price
    gross = unit_price * quantity
    if discount_amount < 0 or discount_amount > gross:
        raise ValidationError({"detail": f"{variant.sku}: chegirma 0 va {gross} oralig'ida bo'lishi kerak."})
    line_total = gross - discount_amount
    return {
        "unit_price": unit_price,
        "unit_cost": unit_cost,
        "discount_amount": discount_amount,
        "line_total": line_total,
        "below_cost": line_total < unit_cost * quantity,
    }


def create_sale(*, business, branch, user, membership, lines, payment_type, idempotency_key,
                allow_below_cost=False, note=""):
    """Savdoni yakunlaydi. (sale, created) qaytaradi. created=False — bu takroriy so'rov edi."""
    existing = Sale.objects.filter(business=business, idempotency_key=idempotency_key).first()
    if existing is not None:
        return existing, False
    try:
        return _create_sale(business, branch, user, membership, lines, payment_type, idempotency_key,
                            allow_below_cost, note), True
    except IntegrityError:
        # Xuddi shu kalit bilan parallel so'rov bizdan oldin yakunlandi.
        existing = Sale.objects.filter(business=business, idempotency_key=idempotency_key).first()
        if existing is None:
            raise
        return existing, False


@transaction.atomic
def _create_sale(business, branch, user, membership, lines, payment_type, idempotency_key, allow_below_cost, note):
    if not lines:
        raise ValidationError({"detail": "Savat bo'sh."})
    ids = [line.variant.id for line in lines]
    if len(ids) != len(set(ids)):
        raise ValidationError({"detail": "Bir variant savatda faqat bir marta bo'lishi kerak."})

    computed = [(line, calculate_line(line.variant, line.quantity, line.discount_amount)) for line in lines]
    below = [line.variant.sku for line, c in computed if c["below_cost"]]
    if below:
        if not membership.is_manager:
            raise ValidationError({"detail": f"Narx xarid narxidan past: {', '.join(below)}. "
                                             "Buning uchun menejer yoki do'kon egasi kerak.",
                                   "code": "below_cost"})
        if not allow_below_cost:
            raise ValidationError({"detail": f"Narx xarid narxidan past: {', '.join(below)}. "
                                             "Davom etish uchun buni tasdiqlang.", "code": "below_cost"})

    subtotal = sum((line.variant.effective_sale_price * line.quantity for line, _ in computed), ZERO)
    discount_total = sum((c["discount_amount"] for _, c in computed), ZERO)
    cost_total = sum((c["unit_cost"] * line.quantity for line, c in computed), ZERO)
    # Savdo qatori birinchi yaratiladi: bir xil idempotency_key bilan parallel so'rov shu yerda kutib turadi.
    sale = Sale.objects.create(
        business=business, branch=branch, cashier=user, idempotency_key=idempotency_key, payment_type=payment_type,
        subtotal=subtotal, discount_total=discount_total, total=subtotal - discount_total, cost_total=cost_total,
        note=note,
    )
    for line, c in sorted(computed, key=lambda item: item[0].variant.id):
        change_stock(business=business, branch=branch, variant=line.variant, delta=-line.quantity,
                     kind=StockMovement.Kind.SALE, user=user, ref=sale)
        SaleLine.objects.create(sale=sale, variant=line.variant, quantity=line.quantity, **c)
    return sale
