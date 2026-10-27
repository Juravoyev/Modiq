"""Hisobotlar. Har biri bir xil shaklda qaytadi: columns, rows, totals, formulas.

Shu shakl tufayli frontend barcha hisobotlarni bitta jadval bilan ko'rsatadi va CSV eksport ham umumiy.
Tushum, taxminiy yalpi foyda va tovar qiymati alohida ustunlar; sof foyda hisoblanmaydi (xarajatlar yo'q).
"""
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.db.models import Count, DecimalField, ExpressionWrapper, F, Sum
from django.db.models.functions import Coalesce, TruncDay, TruncMonth, TruncWeek
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.insights.engine import compute_insights
from apps.inventory.models import Stock
from apps.sales.models import Sale, SaleLine, SaleReturn, SaleReturnLine

ZERO = Decimal("0.00")
MONEY = DecimalField(max_digits=16, decimal_places=2)
MAX_DAYS = 400
GROUPS = {"day": (TruncDay, 30), "week": (TruncWeek, 84), "month": (TruncMonth, 365)}
GP_NOTE = "Taxminiy yalpi foyda = tushum − tannarx. Ijara, maosh va boshqa xarajatlar hisobga olinmagan, bu sof foyda emas."


def _col(key, label, kind="text"):
    return {"key": key, "label": label, "kind": kind}


def parse_range(params, default_days):
    today = timezone.localdate()
    try:
        date_to = date.fromisoformat(params["date_to"]) if params.get("date_to") else today
        date_from = (date.fromisoformat(params["date_from"]) if params.get("date_from")
                     else date_to - timedelta(days=default_days - 1))
    except ValueError:
        raise ValidationError({"detail": "Sana YYYY-MM-DD ko'rinishida bo'lishi kerak."})
    if date_from > date_to:
        raise ValidationError({"detail": "Boshlanish sanasi tugash sanasidan keyin bo'lmasligi kerak."})
    if (date_to - date_from).days > MAX_DAYS:
        raise ValidationError({"detail": f"Davr {MAX_DAYS} kundan oshmasligi kerak."})
    return date_from, date_to


def _bounds(date_from, date_to):
    tz = timezone.get_current_timezone()
    return (timezone.make_aware(datetime.combine(date_from, time.min), tz),
            timezone.make_aware(datetime.combine(date_to + timedelta(days=1), time.min), tz))


def _period_keys(group, date_from, date_to):
    keys, d = [], date_from
    while d <= date_to:
        if group == "day":
            k = d
        elif group == "week":
            k = d - timedelta(days=d.weekday())
        else:
            k = d.replace(day=1)
        if not keys or keys[-1] != k:
            keys.append(k)
        d += timedelta(days=1)
    return keys


def sales_report(business, branches, params):
    group = params.get("group", "day")
    if group not in GROUPS:
        raise ValidationError({"detail": "group: day, week yoki month."})
    trunc, default_days = GROUPS[group]
    date_from, date_to = parse_range(params, default_days)
    start, end = _bounds(date_from, date_to)
    sales = Sale.objects.filter(business=business, branch__in=branches, created_at__gte=start, created_at__lt=end)
    returns = SaleReturn.objects.filter(business=business, branch__in=branches, created_at__gte=start,
                                        created_at__lt=end)
    by_sale = {r["p"].date(): r for r in sales.annotate(p=trunc("created_at")).values("p").annotate(
        n=Count("id"), total=Sum("total"), cost=Sum("cost_total"))}
    by_items = {r["p"].date(): r["q"] for r in SaleLine.objects.filter(sale__in=sales)
                .annotate(p=trunc("sale__created_at")).values("p").annotate(q=Sum("quantity"))}
    by_ret = {r["p"].date(): r for r in returns.annotate(p=trunc("created_at")).values("p").annotate(
        refund=Sum("refund_total"), cost=Sum("cost_total"))}

    rows, totals = [], defaultdict(int)
    for k in _period_keys(group, date_from, date_to):
        s, r = by_sale.get(k, {}), by_ret.get(k, {})
        gross, refund = s.get("total") or ZERO, r.get("refund") or ZERO
        cost = (s.get("cost") or ZERO) - (r.get("cost") or ZERO)
        revenue = gross - refund
        n = s.get("n") or 0
        label = {"day": k.isoformat(), "week": f"{k.isoformat()} haftasi", "month": k.strftime("%Y-%m")}[group]
        row = {"period": label, "sales_count": n, "items": by_items.get(k) or 0, "gross_sales": gross,
               "returns": refund, "revenue": revenue, "cost": cost, "gross_profit": revenue - cost,
               "avg_check": (gross / n).quantize(Decimal("0.01")) if n else ZERO}
        rows.append(row)
        for key in ("sales_count", "items", "gross_sales", "returns", "revenue", "cost", "gross_profit"):
            totals[key] += row[key]
    n_all = totals["sales_count"]
    totals = dict(totals, period="Jami",
                  avg_check=(totals["gross_sales"] / n_all).quantize(Decimal("0.01")) if n_all else ZERO)
    return {
        "title": {"day": "Kunlik savdo", "week": "Haftalik savdo", "month": "Oylik savdo"}[group],
        "date_from": date_from, "date_to": date_to,
        "columns": [_col("period", "Davr"), _col("sales_count", "Cheklar", "int"), _col("items", "Dona", "int"),
                    _col("gross_sales", "Savdo summasi", "money"), _col("returns", "Qaytarilgan", "money"),
                    _col("revenue", "Tushum", "money"), _col("cost", "Tannarx", "money"),
                    _col("gross_profit", "Taxminiy yalpi foyda", "money"), _col("avg_check", "O'rtacha chek", "money")],
        "rows": rows, "totals": totals,
        "formulas": ["Tushum = savdo summasi (chegirmalardan keyin) − qaytarilgan summa", GP_NOTE],
    }


def products_report(business, branches, params):
    date_from, date_to = parse_range(params, 30)
    start, end = _bounds(date_from, date_to)
    lines = SaleLine.objects.filter(sale__business=business, sale__branch__in=branches,
                                    sale__created_at__gte=start, sale__created_at__lt=end)
    agg = (lines.values("variant", "variant__sku", "variant__product__name", "variant__color__name",
                        "variant__size__name")
           .annotate(qty=Sum("quantity"), revenue=Sum("line_total"),
                     cost=Sum(ExpressionWrapper(F("unit_cost") * F("quantity"), output_field=MONEY))))
    ret = {r["sale_line__variant"]: r for r in SaleReturnLine.objects.filter(sale_line__in=lines)
           .values("sale_line__variant").annotate(
               qty=Sum("quantity"), refund=Sum("refund_amount"),
               cost=Sum(ExpressionWrapper(F("sale_line__unit_cost") * F("quantity"), output_field=MONEY)))}
    rows = []
    for a in agg:
        r = ret.get(a["variant"], {})
        qty = a["qty"] - (r.get("qty") or 0)
        revenue = a["revenue"] - (r.get("refund") or ZERO)
        cost = a["cost"] - (r.get("cost") or ZERO)
        rows.append({"sku": a["variant__sku"], "product": a["variant__product__name"],
                     "variant": f"{a['variant__color__name']} / {a['variant__size__name']}",
                     "quantity": qty, "revenue": revenue, "gross_profit": revenue - cost})
    rows.sort(key=lambda x: x["revenue"], reverse=True)
    total_rev = sum((x["revenue"] for x in rows), ZERO)
    for x in rows:
        x["share"] = round(float(x["revenue"] / total_rev * 100), 1) if total_rev else 0.0
    return {
        "title": "Mahsulotlar bo'yicha sotuv", "date_from": date_from, "date_to": date_to,
        "columns": [_col("sku", "SKU"), _col("product", "Mahsulot"), _col("variant", "Rang / o'lcham"),
                    _col("quantity", "Sotildi (dona)", "int"), _col("revenue", "Tushum", "money"),
                    _col("gross_profit", "Taxminiy yalpi foyda", "money"), _col("share", "Tushumdagi ulush, %", "pct")],
        "rows": rows,
        "totals": {"sku": "Jami", "quantity": sum(x["quantity"] for x in rows), "revenue": total_rev,
                   "gross_profit": sum((x["gross_profit"] for x in rows), ZERO)},
        "formulas": ["Qaytarilgan tovarlar miqdor, tushum va tannarxdan chiqarilgan", GP_NOTE],
    }


def stock_report(business, branches, params):
    unit_cost = Coalesce(F("variant__purchase_price"), F("variant__product__purchase_price"))
    unit_price = Coalesce(F("variant__sale_price"), F("variant__product__sale_price"))
    stocks = (Stock.objects.filter(business=business, branch__in=branches, quantity__gt=0)
              .select_related("branch", "variant__product", "variant__color", "variant__size")
              .annotate(cost=unit_cost, price=unit_price)
              .order_by("variant__product__name", "variant__sku", "branch__name"))
    rows = [{"branch": s.branch.name, "sku": s.variant.sku, "product": s.variant.product.name,
             "variant": f"{s.variant.color.name} / {s.variant.size.name}", "quantity": s.quantity,
             "unit_cost": s.cost, "cost_value": s.cost * s.quantity, "sale_value": s.price * s.quantity}
            for s in stocks]
    return {
        "title": "Qoldiq hisoboti", "date_from": None, "date_to": timezone.localdate(),
        "columns": [_col("branch", "Filial"), _col("sku", "SKU"), _col("product", "Mahsulot"),
                    _col("variant", "Rang / o'lcham"), _col("quantity", "Qoldiq (dona)", "int"),
                    _col("unit_cost", "Xarid narxi", "money"), _col("cost_value", "Tovar qiymati (xarid narxida)", "money"),
                    _col("sale_value", "Sotuv narxida qiymati", "money")],
        "rows": rows,
        "totals": {"branch": "Jami", "quantity": sum(r["quantity"] for r in rows),
                   "cost_value": sum((r["cost_value"] for r in rows), ZERO),
                   "sale_value": sum((r["sale_value"] for r in rows), ZERO)},
        "formulas": ["Tovar qiymati = qoldiq × xarid narxi. Bu tushum ham, foyda ham emas",
                     "Sotuv narxidagi qiymat faqat taxmin: hammasi shu narxda sotilishi kafolatlanmaydi"],
    }


def _risk_rows(business, branches, donor_branches, types):
    rows = []
    for item in compute_insights(business, branches, donor_branches=donor_branches):
        for risk in item.risks:
            if risk.type in types:
                rows.append({"branch": item.branch_name, "sku": item.sku, "product": item.product_name,
                             "variant": item.variant_name, "quantity": item.quantity,
                             "last_sale": (item.last_sale_at or "")[:10] or "Sotilmagan",
                             "sold_in_window": item.sold_in_window, "season": item.season or "",
                             "level": {"high": "Yuqori", "medium": "O'rta", "low": "Past"}[risk.level],
                             "level_key": risk.level, "title": risk.title, "reason": risk.reason,
                             "action": risk.action})
    order = {"high": 0, "medium": 1, "low": 2}
    rows.sort(key=lambda r: (order[r["level_key"]], -r["quantity"]))
    return rows


def slow_report(business, branches, params, donor_branches=None):
    rows = _risk_rows(business, branches, donor_branches, {"no_sale", "overstock"})
    return {
        "title": "Kam sotiladigan tovarlar", "date_from": None, "date_to": timezone.localdate(),
        "columns": [_col("level", "Xavf"), _col("branch", "Filial"), _col("sku", "SKU"), _col("product", "Mahsulot"),
                    _col("variant", "Rang / o'lcham"), _col("quantity", "Qoldiq", "int"),
                    _col("last_sale", "Oxirgi sotuv"), _col("sold_in_window", "Davrda sotildi", "int"),
                    _col("reason", "Sabab"), _col("action", "Tavsiya")],
        "rows": rows, "totals": {"level": "Jami", "quantity": sum(r["quantity"] for r in rows)},
        "formulas": ["Qoidalar va chegaralar Sozlamalar → Tavsiya qoidalari bo'limida"],
    }


def seasonal_report(business, branches, params, donor_branches=None):
    rows = _risk_rows(business, branches, donor_branches, {"seasonal"})
    return {
        "title": "Mavsumiy xavf hisoboti", "date_from": None, "date_to": timezone.localdate(),
        "columns": [_col("level", "Xavf"), _col("season", "Mavsum"), _col("branch", "Filial"), _col("sku", "SKU"),
                    _col("product", "Mahsulot"), _col("variant", "Rang / o'lcham"), _col("quantity", "Qoldiq", "int"),
                    _col("reason", "Sabab"), _col("action", "Tavsiya")],
        "rows": rows, "totals": {"level": "Jami", "quantity": sum(r["quantity"] for r in rows)},
        "formulas": ["Mavsum oylari tovar kartochkasidagi mavsumdan olinadi"],
    }


REPORTS = {"sales": sales_report, "products": products_report, "stock": stock_report,
           "slow": slow_report, "seasonal": seasonal_report}


def discount_results(discount, today=None):
    """Chegirma davridagi sotuvni undan oldingi xuddi shuncha kunlik davr bilan solishtiradi.

    Faqat haqiqiy sotuv ma'lumotlari. Farqning sababi faqat chegirma ekanini isbotlamaydi.
    """
    today = today or timezone.localdate()
    end = min(discount.ends_on, today)
    if end < discount.starts_on:
        return {"started": False}
    days = (end - discount.starts_on).days + 1
    before_from = discount.starts_on - timedelta(days=days)
    before_to = discount.starts_on - timedelta(days=1)
    base = SaleLine.objects.filter(variant=discount.variant, sale__business=discount.business)

    def period(d_from, d_to):
        start, finish = _bounds(d_from, d_to)
        lines = base.filter(sale__created_at__gte=start, sale__created_at__lt=finish)
        a = lines.aggregate(qty=Coalesce(Sum("quantity"), 0), revenue=Coalesce(Sum("line_total"), ZERO),
                            cost=Coalesce(Sum(ExpressionWrapper(F("unit_cost") * F("quantity"), output_field=MONEY)),
                                          ZERO))
        r = SaleReturnLine.objects.filter(sale_line__in=lines).aggregate(
            qty=Coalesce(Sum("quantity"), 0), refund=Coalesce(Sum("refund_amount"), ZERO),
            cost=Coalesce(Sum(ExpressionWrapper(F("sale_line__unit_cost") * F("quantity"), output_field=MONEY)), ZERO))
        qty = a["qty"] - r["qty"]
        revenue = a["revenue"] - r["refund"]
        return {"from": d_from, "to": d_to, "quantity": qty, "revenue": revenue,
                "gross_profit": revenue - (a["cost"] - r["cost"]), "per_day": round(qty / days, 2)}

    return {
        "started": True, "days": days,
        "during": period(discount.starts_on, end), "before": period(before_from, before_to),
        "note": "Bu faqat sotuv ma'lumotlari. Chegirma foydani oshirishini kafolatlamaydi: ikkala davrdagi tushum "
                "va taxminiy yalpi foydani solishtiring. Farqqa mavsum va boshqa omillar ham ta'sir qilishi mumkin.",
    }
