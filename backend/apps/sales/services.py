from dataclasses import dataclass
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.db.models import Sum
from rest_framework.exceptions import ValidationError

from apps.discounts.services import active_discounts
from apps.inventory.models import StockMovement
from apps.inventory.services import change_stock

from .models import Sale, SaleLine, SaleReturn, SaleReturnLine

ZERO = Decimal("0.00")


@dataclass
class LineInput:
    variant: object
    quantity: int
    discount_amount: Decimal = ZERO


def calculate_line(variant, quantity: int, discount_amount: Decimal, promo=None):
    """promo: shu kuni amal qilayotgan tasdiqlangan chegirma (bo'lsa), narx undan olinadi."""
    unit_price = promo.price_after if promo else variant.effective_sale_price
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
        "discount": promo,
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

    promos = {d.variant_id: d for d in active_discounts(business).filter(variant_id__in=ids)}
    computed = [(line, calculate_line(line.variant, line.quantity, line.discount_amount, promos.get(line.variant.id)))
                for line in lines]
    # Menejer tannarxdan past chegirmani oldindan tasdiqlagan bo'lsa, kassir qo'shimcha chegirmasiz sota oladi.
    below = [line.variant.sku for line, c in computed
             if c["below_cost"] and not (c["discount"] and c["discount"].below_cost and not c["discount_amount"])]
    if below:
        if not membership.is_manager:
            raise ValidationError({"detail": f"Narx xarid narxidan past: {', '.join(below)}. "
                                             "Buning uchun menejer yoki do'kon egasi kerak.",
                                   "code": "below_cost"})
        if not allow_below_cost:
            raise ValidationError({"detail": f"Narx xarid narxidan past: {', '.join(below)}. "
                                             "Davom etish uchun buni tasdiqlang.", "code": "below_cost"})

    subtotal = sum((c["unit_price"] * line.quantity for line, c in computed), ZERO)
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


@transaction.atomic
def return_sale_items(*, sale_id, user, items, reason=""):
    """Savdodagi tovarlarni qaytaradi. items: [(sale_line_id, quantity), ...].

    Savdo qatori qulflanadi, shuning uchun bir tovarni parallel so'rovlar bilan sotilganidan ko'p qaytarib bo'lmaydi.
    Qaytariladigan summa qator bo'yicha proporsional: line_total / quantity * qaytgan miqdor.
    """
    sale = Sale.objects.select_for_update().select_related("branch").get(pk=sale_id)
    if not items:
        raise ValidationError({"detail": "Qaytariladigan tovarni tanlang."})
    ids = [line_id for line_id, _ in items]
    if len(ids) != len(set(ids)):
        raise ValidationError({"detail": "Bir qator faqat bir marta ko'rsatilishi kerak."})
    lines = {line.id: line for line in sale.lines.select_related("variant__product", "variant__color", "variant__size")}
    returned = dict(
        SaleReturnLine.objects.filter(sale_line__sale=sale).values("sale_line").annotate(q=Sum("quantity"))
        .values_list("sale_line", "q")
    )
    plan = []
    for line_id, qty in items:
        line = lines.get(line_id)
        if line is None:
            raise ValidationError({"detail": "Qator bu savdoga tegishli emas."})
        available = line.quantity - returned.get(line_id, 0)
        if qty <= 0 or qty > available:
            raise ValidationError({"detail": f"{line.variant.sku}: ko'pi bilan {available} dona qaytarish mumkin."})
        refund = (line.line_total / line.quantity * qty).quantize(Decimal("0.01"))
        plan.append((line, qty, refund))

    sale_return = SaleReturn.objects.create(
        business=sale.business, sale=sale, branch=sale.branch, user=user, reason=reason,
        refund_total=sum((r for _, _, r in plan), ZERO),
        cost_total=sum((line.unit_cost * qty for line, qty, _ in plan), ZERO),
    )
    for line, qty, refund in sorted(plan, key=lambda p: p[0].variant_id):
        change_stock(business=sale.business, branch=sale.branch, variant=line.variant, delta=qty,
                     kind=StockMovement.Kind.SALE_RETURN, user=user, ref=sale_return)
        SaleReturnLine.objects.create(sale_return=sale_return, sale_line=line, quantity=qty, refund_amount=refund)
    return sale_return
