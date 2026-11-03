"""Sotilmay qolish xavfi va qayta to'ldirish tavsiyalari.

Hamma narsa qoidalarga va haqiqiy savdo ma'lumotiga asoslangan. Ma'lumot yetarli bo'lmasa (masalan, sotuvlar
juda kam), sotuv sur'ati va "necha kunga yetadi" hisoblanmaydi: soxta aniqlik ko'rsatilmaydi.
Har bir tavsiyada "reason" (nega berildi) va "action" (nima qilish mumkin) matni bor.
"""
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import timedelta

from django.db.models import Max, Min, Q, Sum
from django.utils import timezone

from apps.inventory.models import Stock, StockMovement
from apps.sales.models import SaleLine, SaleReturn, SaleReturnLine

from .models import RiskSettings
from .seasons import season_state

LEVEL_ORDER = {"high": 3, "medium": 2, "low": 1}

NO_SALE = "no_sale"
OVERSTOCK = "overstock"
SEASONAL = "seasonal"
RESTOCK = "restock"

TITLES = {
    NO_SALE: "Sotilmay qolish xavfi",
    OVERSTOCK: "Ortiqcha zaxira",
    SEASONAL: "Mavsumiy xavf",
    RESTOCK: "Qayta to'ldirish kerak",
}


@dataclass
class Risk:
    type: str
    level: str
    title: str
    reason: str
    action: str


@dataclass
class VariantInsight:
    stock_id: int
    branch: int
    branch_name: str
    variant: int
    sku: str
    variant_name: str
    product: int
    product_name: str
    quantity: int
    min_stock: int
    last_sale_at: str | None
    days_since_last_sale: int | None
    days_in_stock: int | None
    sold_in_window: int
    window_days: int
    velocity_per_day: float | None
    days_of_cover: int | None
    season: str | None
    risks: list[Risk] = field(default_factory=list)

    @property
    def top_level(self) -> int:
        return max((LEVEL_ORDER[r.level] for r in self.risks), default=0)

    def as_dict(self):
        d = asdict(self)
        d["top_level"] = {3: "high", 2: "medium", 1: "low", 0: None}[self.top_level]
        return d


def _fmt(n: float) -> str:
    return f"{n:.1f}".replace(".", ",")


def compute_insights(business, branches, today=None, donor_branches=None) -> list[VariantInsight]:
    """branches: tahlil qilinadigan filiallar. donor_branches: ko'chirish tavsiyasi uchun qaraladigan filiallar."""
    settings = RiskSettings.for_business(business)
    now = timezone.now()
    today = today or timezone.localdate()
    window_start = now - timedelta(days=settings.sales_window_days)
    branch_ids = [b.id for b in branches]

    stocks = list(
        Stock.objects.filter(business=business, branch_id__in=branch_ids, variant__is_active=True,
                             variant__product__is_active=True)
        .select_related("branch", "variant__product__season", "variant__color", "variant__size")
    )
    if not stocks:
        return []

    sales = {
        (r["sale__branch_id"], r["variant_id"]): r
        for r in SaleLine.objects.filter(sale__business=business, sale__branch_id__in=branch_ids)
        .values("sale__branch_id", "variant_id")
        .annotate(last=Max("sale__created_at"), sold=Sum("quantity", filter=Q(sale__created_at__gte=window_start)))
    }
    returned = {
        (r["sale_return__branch_id"], r["sale_line__variant_id"]): r["q"] or 0
        for r in SaleReturnLine.objects.filter(sale_return__business=business, sale_return__branch_id__in=branch_ids,
                                               sale_return__created_at__gte=window_start)
        .exclude(sale_return__status=SaleReturn.Status.REJECTED)
        .values("sale_return__branch_id", "sale_line__variant_id").annotate(q=Sum("quantity"))
    }
    first_in = {
        (r["branch_id"], r["variant_id"]): r["first"]
        for r in StockMovement.objects.filter(business=business, branch_id__in=branch_ids, quantity_delta__gt=0)
        .values("branch_id", "variant_id").annotate(first=Min("created_at"))
    }
    # Boshqa (ruxsat etilgan) filiallardagi qoldiq: ko'chirish tavsiyasi uchun.
    donor_ids = [b.id for b in donor_branches] if donor_branches is not None else branch_ids
    by_variant = defaultdict(list)
    for s in Stock.objects.filter(business=business, branch_id__in=donor_ids, quantity__gt=0).select_related(
            "branch", "variant__product"):
        by_variant[s.variant_id].append(s)

    result = []
    for s in stocks:
        if s.branch.kind == s.branch.Kind.WAREHOUSE:
            continue  # omborda savdo bo'lmaydi; ombor qoldig'i faqat ko'chirish tavsiyasida ishlatiladi
        v = s.variant
        key = (s.branch_id, v.id)
        sale = sales.get(key, {})
        last = sale.get("last")
        sold = max(0, (sale.get("sold") or 0) - returned.get(key, 0))
        arrived = first_in.get(key)
        days_since_sale = (now - last).days if last else None
        days_in_stock = (now - arrived).days if arrived else None
        velocity = sold / settings.sales_window_days if sold >= settings.min_sales_for_velocity else None
        cover = int(s.quantity / velocity) if velocity else None
        min_stock = v.effective_min_stock
        season = v.product.season

        item = VariantInsight(
            stock_id=s.id, branch=s.branch_id, branch_name=s.branch.name, variant=v.id, sku=v.sku,
            variant_name=f"{v.color.name} / {v.size.name}", product=v.product_id, product_name=v.product.name,
            quantity=s.quantity, min_stock=min_stock, last_sale_at=last.isoformat() if last else None,
            days_since_last_sale=days_since_sale, days_in_stock=days_in_stock, sold_in_window=sold,
            window_days=settings.sales_window_days,
            velocity_per_day=round(velocity, 2) if velocity else None, days_of_cover=cover,
            season=None,
        )
        state = season_state(season.start_month, season.end_month, today) if season else None
        if season:
            item.season = state.label(season.name)

        if s.quantity > 0:
            # 1. Uzoq vaqt sotilmagan
            idle = days_since_sale if last else days_in_stock
            if idle is not None and idle >= settings.no_sale_days:
                if last:
                    reason = (f"Oxirgi sotuv {idle} kun oldin bo'lgan. Qoldiqda {s.quantity} dona bor. "
                              f"Belgilangan chegara: {settings.no_sale_days} kun.")
                else:
                    reason = (f"Tovar kelganiga {idle} kun bo'ldi, lekin bu filialda bir marta ham sotilmadi. "
                              f"Qoldiqda {s.quantity} dona. Chegara: {settings.no_sale_days} kun.")
                item.risks.append(Risk(
                    NO_SALE, "high" if idle >= 2 * settings.no_sale_days else "medium", TITLES[NO_SALE], reason,
                    "Chegirma berishni yoki sotuvi yaxshiroq filialga ko'chirishni ko'rib chiqing. "
                    "Tovar vitrinada ko'rinadigan joyda turganini tekshiring.",
                ))

            # 2. Ortiqcha zaxira (faqat sur'at ishonchli hisoblanganda)
            if cover is not None and cover > settings.overstock_cover_days:
                item.risks.append(Risk(
                    OVERSTOCK, "high" if cover > 2 * settings.overstock_cover_days else "medium", TITLES[OVERSTOCK],
                    f"Qoldiq {s.quantity} dona. Oxirgi {settings.sales_window_days} kunda {sold} dona sotilgan "
                    f"(kuniga taxminan {_fmt(velocity)} dona). Shu sur'atda qoldiq taxminan {cover} kunga yetadi, "
                    f"chegara {settings.overstock_cover_days} kun.",
                    "Bu variantdan yangi xaridni to'xtatib turing. Boshqa filialga ko'chirish yoki chegirmani "
                    "ko'rib chiqing.",
                ))

            # 3. Mavsumiy xavf
            if state and state.in_season and state.days_to_end <= settings.season_warning_days:
                expected = int(velocity * state.days_to_end) if velocity else 0
                leftover = s.quantity - expected
                if leftover > 0:
                    basis = (f"shu sur'atda mavsum oxirigacha taxminan {expected} dona sotiladi"
                             if velocity else "sotuv sur'atini hisoblash uchun ma'lumot yetarli emas")
                    item.risks.append(Risk(
                        SEASONAL, "high" if leftover * 2 >= s.quantity else "medium", TITLES[SEASONAL],
                        f"'{season.name}' mavsumi tugashiga {state.days_to_end} kun qoldi. Qoldiqda {s.quantity} dona, "
                        f"{basis}. Mavsum oxirida taxminan {leftover} dona qolishi mumkin.",
                        "Mavsum tugashidan oldin bosqichma-bosqich chegirma berishni yoki tovar talab yuqori "
                        "bo'lgan filialga ko'chirishni ko'rib chiqing.",
                    ))
            elif state and not state.in_season and days_since_sale is not None and days_since_sale >= 14:
                item.risks.append(Risk(
                    SEASONAL, "low", TITLES[SEASONAL],
                    f"'{season.name}' mavsumi tugagan, keyingi mavsumgacha {state.days_to_start} kun. "
                    f"Qoldiqda {s.quantity} dona.",
                    "Keyingi mavsumgacha saqlash xarajatini hisobga olib, chegirma yoki saqlashni tanlang.",
                ))

        # 4. Qayta to'ldirish: kam qolgan va sotilayotgan variant
        if min_stock > 0 and s.quantity <= min_stock and sold > 0:
            parts = [f"Qoldiq {s.quantity} dona, minimal chegara {min_stock} dona. "
                     f"Oxirgi {settings.sales_window_days} kunda {sold} dona sotilgan."]
            if velocity and s.quantity > 0:
                parts.append(f"Shu sur'atda taxminan {max(1, int(s.quantity / velocity))} kunda tugashi mumkin.")
            donors = [o for o in by_variant[v.id] if o.branch_id != s.branch_id
                      and o.quantity > o.variant.effective_min_stock]
            action = "Yetkazib beruvchiga buyurtma bering."
            if donors:
                best = max(donors, key=lambda o: o.quantity)
                action = f"'{best.branch.name}' filialida {best.quantity} dona bor: ko'chirishni yoki yangi buyurtmani ko'rib chiqing."
            item.risks.append(Risk(RESTOCK, "high" if s.quantity == 0 else "medium", TITLES[RESTOCK],
                                   " ".join(parts), action))

        if item.risks:
            result.append(item)

    result.sort(key=lambda i: (-i.top_level, -i.quantity))
    return result
