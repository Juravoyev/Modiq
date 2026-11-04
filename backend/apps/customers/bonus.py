"""Bonus (keshbek) hisobi. Balans har doim BonusTransaction jurnalidan hisoblanadi."""
from datetime import timedelta
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal

from django.db.models import DecimalField, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone

from .models import BonusTransaction, Customer

ZERO = Decimal("0.00")
SOUM = Decimal("1")
# Yangi bonus qaytarish muddati (24 soat) o'tgandan keyin ishlatiladi.
BONUS_HOLD = timedelta(hours=24)


def floor_soum(value: Decimal) -> Decimal:
    return value.quantize(SOUM, rounding=ROUND_DOWN)


def round_soum(value: Decimal) -> Decimal:
    return value.quantize(SOUM, rounding=ROUND_HALF_UP)


def _sum(condition):
    return Coalesce(Sum("amount", filter=condition), Value(ZERO), output_field=DecimalField(max_digits=16, decimal_places=2))


def balances(customer, now=None) -> tuple[Decimal, Decimal]:
    """(ishlatish mumkin, kutilayotgan) bonus."""
    now = now or timezone.now()
    agg = BonusTransaction.objects.filter(customer=customer).aggregate(
        available=_sum(Q(available_at__lte=now)), pending=_sum(Q(available_at__gt=now)),
    )
    return agg["available"], agg["pending"]


def lock_customer(customer):
    """Mijoz qatorini qulflaydi: bir vaqtda ikki kassada bitta bonusni ikki marta ishlatib bo'lmaydi."""
    return Customer.objects.select_related("group").select_for_update(of=("self",)).get(pk=customer.pk)


def allocate(amount: Decimal, headrooms: list[Decimal]) -> list[Decimal]:
    """Bonusni qatorlarga bo'sh joyi (narx − tannarx) ulushiga qarab taqsimlaydi, butun so'mda.

    Hech bir qator o'z bo'sh joyidan oshmaydi, yig'indi aynan `amount` ga teng (amount <= sum(headrooms)).
    """
    total = sum(headrooms, ZERO)
    if amount <= 0 or total <= 0:
        return [ZERO for _ in headrooms]
    parts = [floor_soum(amount * h / total) for h in headrooms]
    rest = amount - sum(parts, ZERO)
    for i, h in enumerate(headrooms):
        if rest <= 0:
            break
        add = min(rest, h - parts[i])
        if add > 0:
            parts[i] += add
            rest -= add
    return parts


def record_sale(sale, *, user):
    """Savdodagi bonus harakatlarini jurnalga yozadi (savdo tranzaksiyasi ichida chaqiriladi)."""
    now = timezone.now()
    if sale.bonus_spent > 0:
        BonusTransaction.objects.create(business=sale.business, customer=sale.customer, kind=BonusTransaction.Kind.SPEND,
                                        amount=-sale.bonus_spent, sale=sale, available_at=now, created_by=user)
    if sale.bonus_earned > 0:
        BonusTransaction.objects.create(business=sale.business, customer=sale.customer, kind=BonusTransaction.Kind.EARN,
                                        amount=sale.bonus_earned, sale=sale, available_at=now + BONUS_HOLD,
                                        created_by=user)


def record_return(sale_return, *, user):
    """Tasdiqlangan qaytarish: bonus bilan to'langan qism mijozga qaytadi, yig'ilgan bonus ulushi bekor qilinadi.

    Bekor qilinadigan bonus hali kutilayotgan bo'lsa, o'sha vaqtga yoziladi (kutilayotganidan ayiriladi).
    Allaqachon ishlatish mumkin bo'lib qolgan bo'lsa, balans manfiyga tushmasligi uchun mavjud qoldiq bilan cheklanadi.
    """
    sale = sale_return.sale
    if sale.customer_id is None:
        return
    customer = lock_customer(sale.customer)
    now = timezone.now()
    if sale_return.bonus_refund > 0:
        BonusTransaction.objects.create(business=sale.business, customer=customer, kind=BonusTransaction.Kind.REFUND,
                                        amount=sale_return.bonus_refund, sale=sale, sale_return=sale_return,
                                        available_at=now, created_by=user)

    revoke = ZERO
    if sale.bonus_earned > 0 and sale.total > 0:
        already = -(BonusTransaction.objects.filter(sale=sale, kind=BonusTransaction.Kind.REVOKE)
                    .aggregate(s=_sum(Q()))["s"])
        revoke = min(round_soum(sale.bonus_earned * sale_return.refund_total / sale.total), sale.bonus_earned - already)
    if revoke > 0:
        earn = BonusTransaction.objects.filter(sale=sale, kind=BonusTransaction.Kind.EARN).first()
        when = earn.available_at if earn and earn.available_at > now else now
        if when == now:
            available, _ = balances(customer, now)
            revoke = min(revoke, max(ZERO, available))
        if revoke > 0:
            BonusTransaction.objects.create(business=sale.business, customer=customer, kind=BonusTransaction.Kind.REVOKE,
                                            amount=-revoke, sale=sale, sale_return=sale_return, available_at=when,
                                            created_by=user)
    sale_return.bonus_revoked = max(revoke, ZERO)
    sale_return.save(update_fields=["bonus_revoked", "updated_at"])
