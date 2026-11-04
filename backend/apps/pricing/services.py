"""Narx hisoblash: aksiya, mijoz imtiyozi, qo'lda chegirma va bonus bilan to'lov.

Kassadagi "oldindan hisob" (quote) ham, savdoni yakunlash ham shu bitta funksiyadan foydalanadi.
Shu sababli ekranda ko'rsatilgan summa bilan bazaga yozilgan summa bir xil qoidalar bo'yicha hisoblanadi.

Qoidalar:
- Bir tovarga bir nechta aksiya to'g'ri kelsa, mijoz uchun eng foydalisi olinadi (ustma-ust qo'shilmaydi).
- Mijoz imtiyozi (toifa foizi) ham aksiya bilan qo'shilmaydi: ikkisidan foydalirog'i olinadi.
- Avtomatik chegirma narxni tannarxdan pastga tushirmaydi.
- Sotuvchining qo'lda beradigan chegirmasi sozlamadagi foiz bilan cheklangan. Egasi va menejerda chegara yo'q,
  lekin tannarxdan past sotish uchun alohida tasdiq kerak (sales.services.create_sale).
- Bonus bilan chekning ko'pi bilan `bonus_max_share_percent` foizi to'lanadi va bonus ham narxni tannarxdan
  pastga tushirmaydi. Yangi bonus mijoz pul bilan to'lagan summadan hisoblanadi.
"""
from dataclasses import dataclass, field
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal

from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.customers.bonus import allocate, balances, floor_soum

from .models import PricingSettings, Promotion

ZERO = Decimal("0.00")
CENT = Decimal("0.01")
SOUM = Decimal("1")

PROMOTION = "promotion"
PRIVILEGE = "privilege"


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
    discount_source: str = ""  # "promotion", "privilege" yoki bo'sh
    promotion: object = None
    discount_label: str = ""
    manual_discount: Decimal = ZERO
    bonus_amount: Decimal = ZERO  # shu qatorga to'g'ri kelgan bonus to'lovi

    @property
    def gross(self) -> Decimal:
        return self.unit_price * self.quantity

    @property
    def cost(self) -> Decimal:
        return self.unit_cost * self.quantity

    @property
    def after_discounts(self) -> Decimal:
        return self.gross - self.auto_discount - self.manual_discount

    @property
    def line_total(self) -> Decimal:
        """Mijoz pul bilan to'laydigan qism."""
        return self.after_discounts - self.bonus_amount

    @property
    def below_cost(self) -> bool:
        # Bonus qatorning bo'sh joyidan (narx − tannarx) oshmaydi, shuning uchun bu chegirmalar bo'yicha tekshiriladi.
        return self.after_discounts < self.cost


@dataclass
class Quote:
    lines: list
    settings: PricingSettings
    customer: object = None
    today: object = None
    below_cost_skus: list = field(default_factory=list)
    bonus_available: Decimal = ZERO
    bonus_pending: Decimal = ZERO
    bonus_max: Decimal = ZERO  # shu chekda bonus bilan ko'pi bilan qancha to'lash mumkin
    bonus_earned: Decimal = ZERO  # shu xariddan yig'iladigan bonus

    @property
    def bonus_used(self) -> Decimal:
        return sum((ln.bonus_amount for ln in self.lines), ZERO)

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


def privilege_discount(customer, unit_price: Decimal, unit_cost: Decimal) -> Decimal:
    """Mijoz toifasi bo'yicha bitta dona uchun chegirma (tannarx chegarasi bilan)."""
    percent = customer.discount_percent if customer is not None else 0
    if not percent:
        return ZERO
    d = (unit_price * percent / 100).quantize(SOUM, rounding=ROUND_HALF_UP)
    return min(d, max(ZERO, unit_price - unit_cost))


def price_cart(*, business, membership, lines, customer=None, bonus_to_use=ZERO, today=None) -> Quote:
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
        priv_d = privilege_discount(customer, pl.unit_price, pl.unit_cost)
        # Teng bo'lsa aksiya ko'rsatiladi (mijoz uchun farqi yo'q).
        if promo is not None and unit_d >= priv_d:
            pl.auto_discount = unit_d * line.quantity
            pl.discount_source = PROMOTION
            pl.promotion = promo
            pl.discount_label = f"Aksiya: {promo.label}"
        elif priv_d > 0:
            pl.auto_discount = priv_d * line.quantity
            pl.discount_source = PRIVILEGE
            pl.discount_label = f"Imtiyoz: {customer.group.name} (−{customer.discount_percent}%)"
        _apply_manual_discount(pl, line.manual_discount, membership, settings)
        priced.append(pl)

    quote = Quote(lines=priced, settings=settings, customer=customer, today=today)
    quote.below_cost_skus = [ln.variant.sku for ln in priced if ln.below_cost]
    _apply_bonus(quote, customer, bonus_to_use or ZERO, settings)
    return quote


def _apply_bonus(quote: Quote, customer, bonus_to_use: Decimal, settings: PricingSettings):
    if bonus_to_use < 0 or bonus_to_use != floor_soum(bonus_to_use):
        raise ValidationError({"detail": "Bonus summasi butun musbat son bo'lishi kerak.", "code": "invalid_bonus"})
    if customer is None or not settings.bonus_enabled:
        if bonus_to_use > 0:
            raise ValidationError({"detail": "Bonusdan foydalanish uchun mijozni tanlang.", "code": "invalid_bonus"})
        return
    quote.bonus_available, quote.bonus_pending = balances(customer)
    headrooms = [floor_soum(max(ZERO, ln.after_discounts - ln.cost)) for ln in quote.lines]
    share_cap = floor_soum(quote.total * settings.bonus_max_share_percent / 100)
    quote.bonus_max = max(ZERO, min(floor_soum(quote.bonus_available), share_cap, sum(headrooms, ZERO)))
    if bonus_to_use > quote.bonus_max:
        raise ValidationError({"detail": f"Bonusdan ko'pi bilan {quote.bonus_max:.0f} so'm ishlatish mumkin.",
                               "code": "bonus_limit"})
    for ln, part in zip(quote.lines, allocate(bonus_to_use, headrooms)):
        ln.bonus_amount = part
    quote.bonus_earned = floor_soum(quote.total * settings.bonus_percent / 100)


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
