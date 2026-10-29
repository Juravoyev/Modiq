from dataclasses import dataclass
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.db import IntegrityError, transaction
from django.db.models import Sum
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.inventory.models import StockMovement
from apps.inventory.services import change_stock

from .models import Sale, SaleLine, SaleReturn, SaleReturnLine

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


# Yaroqsiz tovar sotuvdan keyin shu muddat ichida qaytariladi.
RETURN_WINDOW = timedelta(hours=24)


def return_deadline(sale):
    return sale.created_at + RETURN_WINDOW


def returned_quantities(sale_line_ids):
    """Har bir savdo qatoridan qaytarilgan yoki qaytarish kutilayotgan miqdor (rad etilganlar hisobga olinmaydi)."""
    rows = (SaleReturnLine.objects.filter(sale_line_id__in=sale_line_ids)
            .exclude(sale_return__status=SaleReturn.Status.REJECTED)
            .values("sale_line_id").annotate(q=Sum("quantity")))
    return {r["sale_line_id"]: r["q"] for r in rows}


@dataclass
class ReturnLineInput:
    sale_line: object
    quantity: int


@transaction.atomic
def create_return(*, sale, user, membership, lines, reason) -> SaleReturn:
    """Qaytarish hujjatini yaratadi. Huquqi bor xodimda darhol tasdiqlanadi, aks holda tasdiq kutadi."""
    # Savdo qulflanadi: bir vaqtda ikki qaytarish bir xil tovarni ikki marta qaytara olmaydi.
    sale = Sale.objects.select_for_update().get(pk=sale.pk)
    if timezone.now() > return_deadline(sale):
        raise ValidationError({"detail": "Qaytarish muddati (24 soat) o'tib ketgan.", "code": "return_expired"})
    if not reason.strip():
        raise ValidationError({"reason": "Yaroqsizlik sababini yozing."})
    if not lines:
        raise ValidationError({"detail": "Kamida bitta tovarni tanlang."})
    ids = [line.sale_line.id for line in lines]
    if len(ids) != len(set(ids)):
        raise ValidationError({"detail": "Bir tovar qaytarishda faqat bir marta bo'lishi kerak."})

    already = returned_quantities(ids)
    rows = []
    for line in lines:
        sl = line.sale_line
        if sl.sale_id != sale.id:
            raise ValidationError({"detail": "Tovar bu savdoga tegishli emas."})
        left = sl.quantity - already.get(sl.id, 0)
        if line.quantity > left:
            raise ValidationError({"detail": f"{sl.variant.sku}: ko'pi bilan {left} dona qaytarish mumkin.",
                                   "code": "return_quantity_exceeded"})
        # Mijozga chegirma bilan to'lagan narxi qaytariladi (qator summasining ulushi).
        refund = (sl.line_total * line.quantity / sl.quantity).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        rows.append((sl, line.quantity, refund))

    approved = membership.may_approve_returns
    sale_return = SaleReturn.objects.create(
        business=sale.business, sale=sale, branch=sale.branch, reason=reason.strip(), requested_by=user,
        status=SaleReturn.Status.APPROVED if approved else SaleReturn.Status.PENDING,
        decided_by=user if approved else None, decided_at=timezone.now() if approved else None,
        refund_total=sum((r for _, _, r in rows), ZERO),
        cost_total=sum((sl.unit_cost * q for sl, q, _ in rows), ZERO),
    )
    SaleReturnLine.objects.bulk_create([
        SaleReturnLine(sale_return=sale_return, sale_line=sl, quantity=q, refund_amount=r, unit_cost=sl.unit_cost)
        for sl, q, r in rows
    ])
    return sale_return


@transaction.atomic
def decide_return(return_id: int, *, user, membership, approve: bool, note="") -> SaleReturn:
    if not membership.may_approve_returns:
        raise PermissionDenied("Qaytarishni tasdiqlash huquqingiz yo'q.")
    sale_return = SaleReturn.objects.select_for_update().get(pk=return_id)
    if sale_return.status != SaleReturn.Status.PENDING:
        raise ValidationError({"detail": "Bu qaytarish allaqachon ko'rib chiqilgan.", "code": "invalid_status"})
    sale_return.status = SaleReturn.Status.APPROVED if approve else SaleReturn.Status.REJECTED
    sale_return.decided_by = user
    sale_return.decided_at = timezone.now()
    sale_return.decision_note = note
    sale_return.save(update_fields=["status", "decided_by", "decided_at", "decision_note", "updated_at"])
    return sale_return
