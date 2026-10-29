"""Dashboard hisobotlari: tushum, foyda, qaytarishlar, qoldiq qiymati va sotilmayotgan tovarlar.

Barcha summalar Decimal, kunlar Toshkent vaqti bo'yicha hisoblanadi.
"""
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.db.models import Count, DecimalField, ExpressionWrapper, F, Q, Sum, Value
from django.db.models.functions import Coalesce, TruncDate
from django.utils import timezone

from apps.inventory.models import Stock

from .models import Sale, SaleLine, SaleReturn

ZERO = Decimal("0.00")
MONEY_FIELD = DecimalField(max_digits=16, decimal_places=2)


def _money_sum(expr):
    return Coalesce(Sum(expr, output_field=MONEY_FIELD), Value(ZERO, output_field=MONEY_FIELD))


def _sales_totals(qs):
    t = qs.aggregate(revenue=_money_sum("total"), cost=_money_sum("cost_total"), count=Count("id"))
    t["avg_check"] = (t["revenue"] / t["count"]).quantize(Decimal("0.01")) if t["count"] else ZERO
    return t


def _approved_returns(business, branches, since):
    return SaleReturn.objects.filter(business=business, branch__in=branches, status=SaleReturn.Status.APPROVED,
                                     decided_at__gte=since)


def build_dashboard(*, business, branches, days: int):
    now = timezone.now()
    today = timezone.localdate()
    start_day = today - timedelta(days=days - 1)
    since = timezone.make_aware(datetime.combine(start_day, time.min))
    today_start = timezone.make_aware(datetime.combine(today, time.min))

    sales = Sale.objects.filter(business=business, branch__in=branches)
    period_sales = sales.filter(created_at__gte=since)
    period = _sales_totals(period_sales)
    today_totals = _sales_totals(sales.filter(created_at__gte=today_start))

    returns = _approved_returns(business, branches, since).aggregate(
        refunds=_money_sum("refund_total"), written_off=_money_sum("cost_total"), count=Count("id"))
    today_refunds = _approved_returns(business, branches, today_start).aggregate(s=_money_sum("refund_total"))["s"]

    # Kunlik tushum: savdo bo'lmagan kunlar ham 0 bilan ko'rsatiladi.
    by_day = {
        row["day"]: row
        for row in period_sales.annotate(day=TruncDate("created_at")).values("day")
        .annotate(revenue=_money_sum("total"), count=Count("id"))
    }
    daily = []
    for i in range(days):
        d = start_day + timedelta(days=i)
        row = by_day.get(d)
        daily.append({"date": d.isoformat(), "revenue": row["revenue"] if row else ZERO, "count": row["count"] if row else 0})

    payments = list(period_sales.values("payment_type").annotate(revenue=_money_sum("total"), count=Count("id"))
                    .order_by("-revenue"))
    labels = dict(Sale.PaymentType.choices)
    for p in payments:
        p["label"] = labels.get(p["payment_type"], p["payment_type"])

    top_products = list(
        SaleLine.objects.filter(sale__in=period_sales)
        .values(product_id=F("variant__product_id"), name=F("variant__product__name"))
        .annotate(quantity=Sum("quantity"), revenue=_money_sum("line_total"))
        .order_by("-quantity", "-revenue")[:5]
    )

    unit_cost = Coalesce(F("variant__purchase_price"), F("variant__product__purchase_price"))
    stock = Stock.objects.filter(business=business, branch__in=branches, quantity__gt=0)
    stock_totals = stock.aggregate(
        units=Coalesce(Sum("quantity"), Value(0)),
        value=_money_sum(ExpressionWrapper(F("quantity") * unit_cost, output_field=MONEY_FIELD)),
    )
    low_stock = Stock.objects.filter(business=business, branch__in=branches).filter(
        Q(variant__min_stock__isnull=False, quantity__lte=F("variant__min_stock"))
        | Q(variant__min_stock__isnull=True, quantity__lte=F("variant__product__min_stock"))
    ).filter(variant__is_active=True, variant__product__is_active=True).count()

    # Sotilmay turgan tovarlar: qoldig'i bor, lekin davr ichida bitta ham sotilmagan.
    # Keyinchalik aksiya bo'yicha maslahat shu ro'yxatdan boshlanadi.
    sold_products = SaleLine.objects.filter(sale__in=period_sales).values("variant__product_id")
    slow_movers = list(
        stock.filter(variant__product__is_active=True).exclude(variant__product_id__in=sold_products)
        .values(product_id=F("variant__product_id"), name=F("variant__product__name"),
                article=F("variant__product__article"))
        .annotate(
            units=Sum("quantity"),
            value=_money_sum(ExpressionWrapper(F("quantity") * unit_cost, output_field=MONEY_FIELD)),
        )
        .order_by("-value")[:5]
    )

    pending_returns = SaleReturn.objects.filter(business=business, branch__in=branches,
                                                status=SaleReturn.Status.PENDING).count()

    gross_profit = period["revenue"] - returns["refunds"] - period["cost"]
    return {
        "generated_at": now.isoformat(),
        "days": days,
        "today": {
            "revenue": today_totals["revenue"], "sales_count": today_totals["count"],
            "avg_check": today_totals["avg_check"], "refunds": today_refunds,
        },
        "period": {
            "revenue": period["revenue"], "sales_count": period["count"], "avg_check": period["avg_check"],
            "refunds": returns["refunds"], "returns_count": returns["count"], "written_off": returns["written_off"],
            "net_revenue": period["revenue"] - returns["refunds"], "cost": period["cost"],
            "gross_profit": gross_profit,
        },
        "daily": daily,
        "payments": payments,
        "top_products": top_products,
        "slow_movers": slow_movers,
        "stock": {"units": stock_totals["units"], "value": stock_totals["value"], "low_count": low_stock},
        "pending_returns": pending_returns,
    }
