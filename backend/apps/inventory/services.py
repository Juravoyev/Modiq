"""Qoldiqni o'zgartiradigan barcha amallar shu yerda.

Qoidalar:
* Har bir amal transaction.atomic ichida bajariladi: xato bo'lsa, hammasi orqaga qaytadi.
* Hujjat qatori select_for_update bilan qulflanadi, keyin holati tekshiriladi.
  Shu sababli bir hujjatni ikki marta tasdiqlash qoldiqni ikki marta o'zgartirmaydi.
* Qoldiq qatorlari variant id bo'yicha tartibda qulflanadi (deadlockdan saqlanish uchun).
"""
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import Receipt, Stock, StockMovement, Transfer


class StockError(ValidationError):
    pass


def _locked_stock(business, branch, variant) -> Stock:
    try:
        return Stock.objects.select_for_update().get(branch=branch, variant=variant)
    except Stock.DoesNotExist:
        try:
            with transaction.atomic():
                return Stock.objects.create(business=business, branch=branch, variant=variant, quantity=0)
        except IntegrityError:
            # Parallel so'rov qatorni biz bilan bir vaqtda yaratdi.
            return Stock.objects.select_for_update().get(branch=branch, variant=variant)


def change_stock(*, business, branch, variant, delta: int, kind: str, user=None, ref=None, note="") -> Stock:
    """Qoldiqni delta ga o'zgartiradi va jurnalga yozadi. Chaqiruvchi transaction ichida bo'lishi shart."""
    if not transaction.get_connection().in_atomic_block:
        raise RuntimeError("change_stock transaction.atomic ichida chaqirilishi kerak")
    stock = _locked_stock(business, branch, variant)
    new_qty = stock.quantity + delta
    if new_qty < 0:
        raise StockError({
            "detail": f"Qoldiq yetarli emas: {variant} ({branch.name}). Mavjud: {stock.quantity}, kerak: {-delta}.",
            "code": "insufficient_stock",
            "variant": variant.id,
            "available": stock.quantity,
        })
    stock.quantity = new_qty
    stock.save(update_fields=["quantity", "updated_at"])
    StockMovement.objects.create(
        business=business, branch=branch, variant=variant, kind=kind, quantity_delta=delta,
        balance_after=new_qty, user=user, note=note,
        ref_type=ref.__class__.__name__.lower() if ref is not None else "",
        ref_id=ref.pk if ref is not None else None,
    )
    return stock


def _sorted_lines(doc):
    return list(doc.lines.select_related("variant__product", "variant__color", "variant__size").order_by("variant_id"))


@transaction.atomic
def confirm_receipt(receipt_id: int, user) -> Receipt:
    receipt = Receipt.objects.select_for_update().select_related("branch").get(pk=receipt_id)
    if receipt.status != Receipt.Status.DRAFT:
        raise StockError({"detail": "Bu kirim allaqachon tasdiqlangan yoki bekor qilingan.", "code": "invalid_status"})
    lines = _sorted_lines(receipt)
    if not lines:
        raise StockError({"detail": "Kirimda birorta ham tovar yo'q.", "code": "empty_document"})
    for line in lines:
        change_stock(business=receipt.business, branch=receipt.branch, variant=line.variant, delta=line.quantity,
                     kind=StockMovement.Kind.RECEIPT, user=user, ref=receipt)
    receipt.status = Receipt.Status.CONFIRMED
    receipt.confirmed_by = user
    receipt.confirmed_at = timezone.now()
    receipt.save(update_fields=["status", "confirmed_by", "confirmed_at", "updated_at"])
    return receipt


@transaction.atomic
def cancel_receipt(receipt_id: int, user) -> Receipt:
    receipt = Receipt.objects.select_for_update().get(pk=receipt_id)
    if receipt.status != Receipt.Status.DRAFT:
        # Tasdiqlangan kirimni qaytarish keyingi bosqichda alohida "qaytarish" hujjati bilan qilinadi.
        raise StockError({"detail": "Faqat qoralama kirimni bekor qilish mumkin.", "code": "invalid_status"})
    receipt.status = Receipt.Status.CANCELLED
    receipt.save(update_fields=["status", "updated_at"])
    return receipt


def _lock_transfer(transfer_id, expected_status, action_name):
    transfer = Transfer.objects.select_for_update().select_related("from_branch", "to_branch").get(pk=transfer_id)
    if transfer.status != expected_status:
        expected_label = Transfer.Status(expected_status).label
        raise StockError({
            "detail": f"Ko'chirishni {action_name} uchun holati '{expected_label}' bo'lishi kerak. "
                      f"Hozirgi holat: '{transfer.get_status_display()}'.",
            "code": "invalid_status",
        })
    return transfer


@transaction.atomic
def send_transfer(transfer_id: int, user) -> Transfer:
    transfer = _lock_transfer(transfer_id, Transfer.Status.DRAFT, "jo'natish")
    lines = _sorted_lines(transfer)
    if not lines:
        raise StockError({"detail": "Ko'chirishda birorta ham tovar yo'q.", "code": "empty_document"})
    for line in lines:
        change_stock(business=transfer.business, branch=transfer.from_branch, variant=line.variant,
                     delta=-line.quantity, kind=StockMovement.Kind.TRANSFER_OUT, user=user, ref=transfer)
    transfer.status = Transfer.Status.SENT
    transfer.sent_at = timezone.now()
    transfer.save(update_fields=["status", "sent_at", "updated_at"])
    return transfer


@transaction.atomic
def receive_transfer(transfer_id: int, user) -> Transfer:
    transfer = _lock_transfer(transfer_id, Transfer.Status.SENT, "qabul qilish")
    for line in _sorted_lines(transfer):
        change_stock(business=transfer.business, branch=transfer.to_branch, variant=line.variant,
                     delta=line.quantity, kind=StockMovement.Kind.TRANSFER_IN, user=user, ref=transfer)
    transfer.status = Transfer.Status.RECEIVED
    transfer.received_at = timezone.now()
    transfer.save(update_fields=["status", "received_at", "updated_at"])
    return transfer


@transaction.atomic
def cancel_transfer(transfer_id: int, user) -> Transfer:
    transfer = Transfer.objects.select_for_update().select_related("from_branch").get(pk=transfer_id)
    if transfer.status == Transfer.Status.SENT:
        # Yo'ldagi tovar jo'natgan filialga qaytariladi.
        for line in _sorted_lines(transfer):
            change_stock(business=transfer.business, branch=transfer.from_branch, variant=line.variant,
                         delta=line.quantity, kind=StockMovement.Kind.TRANSFER_RETURN, user=user, ref=transfer)
    elif transfer.status != Transfer.Status.DRAFT:
        raise StockError({"detail": "Qabul qilingan yoki bekor qilingan ko'chirishni bekor qilib bo'lmaydi.",
                          "code": "invalid_status"})
    transfer.status = Transfer.Status.CANCELLED
    transfer.cancelled_at = timezone.now()
    transfer.save(update_fields=["status", "cancelled_at", "updated_at"])
    return transfer
