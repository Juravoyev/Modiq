"""Narx hisoblash: aksiya va qo'lda chegirma.

Kassadagi "oldindan hisob" (quote) ham, savdoni yakunlash ham shu bitta funksiyadan foydalanadi.
Shu sababli ekranda ko'rsatilgan summa bilan bazaga yozilgan summa bir xil qoidalar bo'yicha hisoblanadi.

Qoidalar:
- Bir tovarga bir nechta aksiya to'g'ri kelsa, mijoz uchun eng foydalisi olinadi (ustma-ust qo'shilmaydi).
- Avtomatik chegirma narxni tannarxdan pastga tushirmaydi.
- Sotuvchining qo'lda beradigan chegirmasi sozlamadagi foiz bilan cheklangan. Egasi va menejerda chegara yo'q,
  lekin tannarxdan past sotish uchun alohida tasdiq kerak (sales.services.create_sale).
"""
from dataclasses import dataclass, field
from decimal import ROUND_DOWN, Decimal

from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import PricingSettings, Promotion

ZERO = Decimal("0.00")
CENT = Decimal("0.01")


@dataclass
class CartLine:
    variant: object
    quantity: int
    manual_discount: Decimal = ZERO


@dataclass
class PricedLine:
    variant: object
    quantity: int
    unit_price: Decimal
    unit_cost: Decimal
    auto_discount: Decimal = ZERO  # aksiya chegirmasi (qator bo'yicha jami)
    discount_source: str = ""  # "promotion" yoki bo'sh
    promotion: object = None
    discount_label: str = ""
    manual_discount: Decimal = ZERO

    @property
    def gross(self) -> Decimal:
        return self.unit_price * self.quantity

    @property
    def cost(self) -> Decimal:
        return self.unit_cost * self.quantity

    @property
    def line_total(self) -> Decimal:
        return self.gross - self.auto_discount - self.manual_discount

    @property
    def below_cost(self) -> bool:
        return self.line_total < self.cost


@dataclass
class Quote:
    lines: list
    settings: PricingSettings
    today: object = None
    below_cost_skus: list = field(default_factory=list)

    @property
    def subtotal(self) -> Decimal:
        return sum((ln.gross for ln in self.lines), ZERO)

    @property
    def auto_discount_total(self) -> Decimal:
        return sum((ln.auto_discount for ln in self.lines), ZERO)

    @property
    def manual_discount_total(self) -> Decimal:
        return sum((ln.manual_discount for ln in self.lines), ZERO)

    @property
    def discount_total(self) -> Decimal:
        return self.auto_discount_total + self.manual_discount_total

    @property
    def total(self) -> Decimal:
        return sum((ln.line_total for ln in self.lines), ZERO)

    @property
    def cost_total(self) -> Decimal:
        return sum((ln.cost for ln in self.lines), ZERO)


def active_promotions(business, today=None):
    """Bugun amal qilayotgan aksiyalar. Tanlangan tovarlar ro'yxati oldindan yuklanadi."""
    today = today or timezone.localdate()
    promos = list(Promotion.objects.filter(business=business, is_active=True, starts_on__lte=today,
                                           ends_on__gte=today).prefetch_related("products"))
    for p in promos:
        p.product_ids = {prod.id for prod in p.products.all()}
    return promos


def best_promotion(product, unit_price: Decimal, unit_cost: Decimal, promotions):
    """(bitta dona uchun chegirma, aksiya) — mijoz uchun eng foydalisi, tannarx chegarasi bilan."""
    headroom = max(ZERO, unit_price - unit_cost)
    best, best_promo = ZERO, None
    for promo in promotions:
        if not promo.applies_to(product, getattr(promo, "product_ids", None)):
            continue
        d = min(promo.unit_discount(unit_price), headroom)
        if d > best:
            best, best_promo = d, promo
    return best, best_promo


def price_cart(*, business, membership, lines, today=None) -> Quote:
    """Savat narxini hisoblaydi. Noto'g'ri chegirmada ValidationError ({"detail", "code"})."""
    if not lines:
        raise ValidationError({"detail": "Savat bo'sh."})
    ids = [line.variant.id for line in lines]
    if len(ids) != len(set(ids)):
        raise ValidationError({"detail": "Bir variant savatda faqat bir marta bo'lishi kerak."})

    settings = PricingSettings.for_business(business)
    today = today or timezone.localdate()
    promotions = active_promotions(business, today)

    priced = []
    for line in lines:
        v = line.variant
        pl = PricedLine(variant=v, quantity=line.quantity, unit_price=v.effective_sale_price,
                        unit_cost=v.effective_purchase_price)
        unit_d, promo = best_promotion(v.product, pl.unit_price, pl.unit_cost, promotions)
        if promo is not None:
            pl.auto_discount = unit_d * line.quantity
            pl.discount_source = "promotion"
            pl.promotion = promo
            pl.discount_label = f"Aksiya: {promo.label}"
        _apply_manual_discount(pl, line.manual_discount, membership, settings)
        priced.append(pl)

    quote = Quote(lines=priced, settings=settings, today=today)
    quote.below_cost_skus = [ln.variant.sku for ln in priced if ln.below_cost]
    return quote


def _apply_manual_discount(pl: PricedLine, amount: Decimal, membership, settings: PricingSettings):
    amount = amount or ZERO
    max_amount = pl.gross - pl.auto_discount
    if amount < 0 or amount > max_amount:
        raise ValidationError({"detail": f"{pl.variant.sku}: chegirma 0 va {max_amount} oralig'ida bo'lishi kerak.",
                               "code": "invalid_discount"})
    if amount and not membership.is_manager:
        percent = settings.cashier_max_discount_percent
        limit = (pl.gross * percent / 100).quantize(CENT, rounding=ROUND_DOWN)
        if amount > limit:
            raise ValidationError({
                "detail": f"{pl.variant.sku}: sotuvchi ko'pi bilan {percent}% ({limit:.0f} so'm) chegirma bera oladi. "
                          "Kattaroq chegirma uchun menejer yoki do'kon egasi kerak.",
                "code": "discount_limit",
            })
    pl.manual_discount = amount
