"""Sotilmay qolish xavfi: qaysi tovarga, necha foiz chegirma berish kerak.

Qarorni qoidalar chiqaradi (har safar bir xil, tekshirsa bo'ladi), har bir tavsiyaning sababi matn bilan beriladi.
Sun'iy intellekt (Gemini) faqat tayyor ro'yxatdan qisqa xulosa yozadi, qarorga ta'sir qilmaydi (ai.py).

Ko'rsatkichlar (har bir tovar bo'yicha, tanlangan filiallarda):
- oxirgi sotuvdan beri kunlar;
- qoldiq necha kunga yetadi: qoldiq / (oxirgi 30 kunda sotilgan / 30);
- omborda turgan pul: qoldiq × tannarx;
- mavsum: tugashiga qancha qolgan yoki tugaganmi.
"""
import calendar
from collections import defaultdict
from datetime import date, timedelta
from decimal import ROUND_DOWN, Decimal

from django.db.models import Max, Min, Sum
from django.utils import timezone

from apps.inventory.models import Stock, StockMovement
from apps.pricing.services import active_promotions
from apps.sales.models import SaleLine

from .models import Dismissal, InsightSettings

VELOCITY_DAYS = 30
LEVELS = {"high": (3, "Yuqori xavf"), "medium": (2, "O'rta xavf"), "low": (1, "Past xavf")}
MONTHS = ["yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul", "avgust", "sentabr", "oktabr", "noyabr",
          "dekabr"]


def _soum(value) -> str:
    return f"{int(value):,}".replace(",", " ") + " so'm"


# --- Mavsum ---------------------------------------------------------------------------------------

def season_months(season) -> set[int]:
    s, e = season.start_month, season.end_month
    return set(range(s, e + 1)) if s <= e else set(range(s, 13)) | set(range(1, e + 1))


def in_season(season, today: date) -> bool:
    return today.month in season_months(season)


def season_end_date(season, today: date) -> date:
    """Joriy mavsumning oxirgi kuni (bugun mavsum ichida bo'lsa)."""
    year = today.year if today.month <= season.end_month else today.year + 1
    return date(year, season.end_month, calendar.monthrange(year, season.end_month)[1])


def months_until_start(season, today: date) -> int:
    return (season.start_month - today.month) % 12


# --- Hisob ----------------------------------------------------------------------------------------

def _product_stats(business, branches, today):
    """Qoldig'i bor faol tovarlar bo'yicha xom ko'rsatkichlar."""
    stock_rows = (Stock.objects.filter(business=business, branch__in=branches, quantity__gt=0,
                                       variant__is_active=True, variant__product__is_active=True)
                  .select_related("variant__product__season", "variant__product__category"))
    products = {}
    for row in stock_rows:
        v = row.variant
        p = products.setdefault(v.product_id, {
            "product": v.product, "units": 0, "value_cost": Decimal(0), "value_retail": Decimal(0), "variants": {},
        })
        p["units"] += row.quantity
        p["value_cost"] += row.quantity * v.effective_purchase_price
        p["value_retail"] += row.quantity * v.effective_sale_price
        p["variants"][v.id] = (v.effective_sale_price, v.effective_purchase_price)
    if not products:
        return products

    ids = list(products)
    since = timezone.now() - timedelta(days=VELOCITY_DAYS)
    lines = SaleLine.objects.filter(sale__business=business, sale__branch__in=branches, variant__product_id__in=ids)
    sold = dict(lines.filter(sale__created_at__gte=since).values_list("variant__product_id")
                .annotate(q=Sum("quantity")).values_list("variant__product_id", "q"))
    last_sale = dict(lines.values("variant__product_id").annotate(t=Max("sale__created_at"))
                     .values_list("variant__product_id", "t"))
    first_in = dict(StockMovement.objects.filter(business=business, branch__in=branches, quantity_delta__gt=0,
                                                 variant__product_id__in=ids)
                    .values("variant__product_id").annotate(t=Min("created_at"))
                    .values_list("variant__product_id", "t"))
    for pid, p in products.items():
        p["sold_30"] = sold.get(pid, 0) or 0
        ls = last_sale.get(pid)
        fi = first_in.get(pid)
        p["last_sale_at"] = ls
        p["age_days"] = (today - timezone.localtime(fi).date()).days if fi else 0
        p["days_since_sale"] = (today - timezone.localtime(ls).date()).days if ls else None
    return products


def safe_discount(variants: dict) -> int:
    """Narx tannarxdan pastga tushmaydigan eng katta butun foiz (eng kam foydali variant bo'yicha)."""
    worst = None
    for price, cost in variants.values():
        if price <= 0:
            return 0
        pct = int(((price - cost) / price * 100).to_integral_value(rounding=ROUND_DOWN))
        worst = pct if worst is None else min(worst, pct)
    return max(0, min(worst or 0, 90))


def margin_after(variants: dict, discount: int) -> int:
    """Chegirmadan keyin narx tannarxdan necha foiz yuqori qoladi (eng kam foydali variant)."""
    worst = None
    for price, cost in variants.values():
        if cost <= 0:
            continue
        new_price = price * (100 - discount) / 100
        pct = int(((new_price - cost) / cost * 100).to_integral_value(rounding=ROUND_DOWN))
        worst = pct if worst is None else min(worst, pct)
    return worst if worst is not None else 100


def evaluate(p: dict, settings: InsightSettings, today: date):
    """Qoidalarni qo'llaydi: [(daraja, chegirma, sabab)]. Bo'sh — xavf yo'q."""
    rules = []
    units, sold = p["units"], p["sold_30"]
    since_sale = p["days_since_sale"]
    daily = Decimal(sold) / VELOCITY_DAYS
    cover = int(units / daily) if daily > 0 else None

    # 1. Uzoq vaqt sotilmagan.
    idle = since_sale if since_sale is not None else p["age_days"]
    if idle >= settings.no_sale_days:
        text = (f"Oxirgi {idle} kun ichida bitta ham sotilmadi." if since_sale is not None
                else f"Omborga kelganiga {idle} kun bo'ldi, bitta ham sotilmadi.")
        rules.append(("high", settings.high_discount, text))
    # 2-3. Sekin sotilmoqda: qoldiq uzoq muddatga yetadi.
    elif cover is None:
        rules.append(("medium", settings.medium_discount,
                      f"Oxirgi {VELOCITY_DAYS} kunda bitta ham sotilmadi, omborda {units} dona turibdi."))
    elif cover >= settings.cover_days_medium:
        rules.append(("medium", settings.medium_discount,
                      f"Hozirgi tezlikda ({VELOCITY_DAYS} kunda {sold} dona) qoldiq {cover} kunga yetadi."))
    elif cover >= settings.cover_days_low:
        rules.append(("low", settings.low_discount,
                      f"Hozirgi tezlikda ({VELOCITY_DAYS} kunda {sold} dona) qoldiq {cover} kunga yetadi."))

    # 4. Mavsum.
    season = p["product"].season
    if season is not None and len(season_months(season)) < 12:
        if in_season(season, today):
            left = (season_end_date(season, today) - today).days
            if left <= settings.season_end_days and (cover is None or cover > left):
                rules.append(("medium", settings.season_discount,
                              f"«{season.name}» mavsumi {left} kundan keyin tugaydi, qoldiq bu muddatda sotilib "
                              "ulgurmaydi."))
        else:
            wait = months_until_start(season, today)
            rules.append(("medium", settings.season_discount,
                          f"«{season.name}» mavsumi tugagan, {units} dona qolgan. Keyingi mavsum "
                          f"{MONTHS[season.start_month - 1]}da ({wait} oydan keyin) boshlanadi."))
    return rules, cover


def build_recommendations(*, business, branches, today=None) -> list[dict]:
    today = today or timezone.localdate()
    settings = InsightSettings.for_business(business)
    stats = _product_stats(business, branches, today)
    dismissed = set(Dismissal.objects.filter(business=business, until__gte=today).values_list("product_id", flat=True))
    promotions = active_promotions(business, today)

    result = []
    for pid, p in stats.items():
        if pid in dismissed or p["age_days"] < settings.min_age_days:
            continue
        rules, cover = evaluate(p, settings, today)
        if not rules:
            continue
        level = max(rules, key=lambda r: LEVELS[r[0]][0])[0]
        wanted = max(r[1] for r in rules)
        reasons = [r[2] for r in rules]
        reasons.append(f"Omborda {p['units']} dona turibdi, tannarxda {_soum(p['value_cost'])}.")
        safe = safe_discount(p["variants"])
        discount = min(wanted, safe)
        if safe <= 0:
            reasons.append("Narx tannarxga teng yoki undan past: chegirma berib bo'lmaydi.")
        elif discount < wanted:
            reasons.append(f"Narx tannarxdan pastga tushmasligi uchun chegirma {wanted}% emas, {discount}% qilib olindi.")
        if discount > 0:
            reasons.append(f"{discount}% chegirmada ham narx tannarxdan kamida {margin_after(p['variants'], discount)}% "
                           "yuqori qoladi.")

        product = p["product"]
        # Tovarga allaqachon faol aksiya to'g'ri kelsa, yangisini yaratish taklif qilinmaydi.
        promo = next((pr for pr in promotions if pr.applies_to(product, pr.product_ids)), None)
        result.append({
            "product_id": pid, "name": product.name, "article": product.article,
            "image": product.image.url if product.image else None,
            "category_name": product.category.name if product.category_id else None,
            "season_name": product.season.name if product.season_id else None,
            "level": level, "level_display": LEVELS[level][1],
            "discount": discount, "wanted_discount": wanted, "safe_discount": safe,
            "reasons": reasons,
            "units": p["units"], "value_cost": p["value_cost"], "value_retail": p["value_retail"],
            "sold_30": p["sold_30"], "days_since_sale": p["days_since_sale"], "cover_days": cover,
            "age_days": p["age_days"],
            "last_sale_at": p["last_sale_at"].isoformat() if p["last_sale_at"] else None,
            "active_promotion": {"id": promo.id, "label": promo.label} if promo else None,
            "can_promote": discount > 0 and promo is None,
        })
    result.sort(key=lambda r: (-LEVELS[r["level"]][0], -r["value_cost"]))
    return result


def dismiss(*, business, product, user, days=30):
    until = timezone.localdate() + timedelta(days=days)
    Dismissal.objects.update_or_create(business=business, product=product, defaults={"until": until, "user": user})
    return until


def summary_totals(recs: list[dict]) -> dict:
    by_level = defaultdict(int)
    for r in recs:
        by_level[r["level"]] += 1
    return {
        "count": len(recs),
        "high": by_level["high"], "medium": by_level["medium"], "low": by_level["low"],
        "frozen_value": sum((r["value_cost"] for r in recs), Decimal(0)),
    }

