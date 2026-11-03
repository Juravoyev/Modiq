"""Dashboard ko'rsatkichlari. Formulalar FORMULAS da yozilgan va API javobida ham qaytariladi."""
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.db.models import Count, DecimalField, ExpressionWrapper, F, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.insights.engine import compute_insights
from apps.inventory.models import Stock
from apps.sales.models import Sale, SaleLine, SaleReturn

ZERO = Decimal("0.00")
MONEY = DecimalField(max_digits=16, decimal_places=2)

FORMULAS = {
    "revenue": "Tushum = bugungi savdolar yakuniy summasi (chegirmadan keyin) − bugun tasdiqlangan qaytarishlar summasi",
    "sales_count": "Savdolar soni = bugun yakunlangan cheklar soni",
    "items_sold": "Sotilgan dona = bugungi savdo qatorlaridagi miqdorlar yig'indisi",
    "gross_profit": "Taxminiy yalpi foyda = tushum − sotilgan tovar tannarxi (sotuvga qaytgan tovar tannarxi chiqarilgan, "
                    "yaroqsiz tovar tannarxi zarar sifatida qoldirilgan). "
                    "Ijara, maosh va boshqa xarajatlar hisobga olinmagan, bu sof foyda emas",
    "stock_units": "Umumiy qoldiq = tanlangan filiallardagi barcha variantlar qoldig'i yig'indisi (dona)",
    "stock_value": "Qoldiq qiymati = har bir variant qoldig'i × xarid narxi",
    "low_stock": "Kam qolgan = qoldig'i minimal chegaraga teng yoki undan past bo'lgan variantlar",
    "risky": "Xavfli tovarlar = kamida bitta yuqori yoki o'rta darajali xavfi bor variantlar",
}


def _day_range(day):
    tz = timezone.get_current_timezone()
    start = timezone.make_aware(datetime.combine(day, time.min), tz)
    return start, start + timedelta(days=1)


def dashboard(business, branches, is_manager: bool, donor_branches=None):
    start, end = _day_range(timezone.localdate())
    sales = Sale.objects.filter(business=business, branch__in=branches, created_at__gte=start, created_at__lt=end)
    returns = SaleReturn.objects.filter(business=business, branch__in=branches, status=SaleReturn.Status.APPROVED,
                                        created_at__gte=start, created_at__lt=end)
    s = sales.aggregate(total=Coalesce(Sum("total"), ZERO), cost=Coalesce(Sum("cost_total"), ZERO), n=Count("id"))
    r = returns.aggregate(total=Coalesce(Sum("refund_total"), ZERO),
                          cost=Coalesce(Sum("cost_total", filter=Q(kind=SaleReturn.Kind.RESALE)), ZERO))
    items = SaleLine.objects.filter(sale__in=sales).aggregate(q=Coalesce(Sum("quantity"), 0))["q"]

    stocks = Stock.objects.filter(business=business, branch__in=branches, variant__is_active=True)
    effective_min = Coalesce(F("variant__min_stock"), F("variant__product__min_stock"))
    low = (stocks.annotate(min_q=effective_min).filter(quantity__lte=F("min_q"))
           .select_related("branch", "variant__product", "variant__color", "variant__size").order_by("quantity"))
    unit_cost = Coalesce(F("variant__purchase_price"), F("variant__product__purchase_price"))
    stock_agg = stocks.aggregate(
        units=Coalesce(Sum("quantity"), 0),
        value=Coalesce(Sum(ExpressionWrapper(F("quantity") * unit_cost, output_field=MONEY)), Value(ZERO)),
    )

    insights = compute_insights(business, branches, donor_branches=donor_branches)
    risky = [i for i in insights if any(x.level in ("high", "medium") and x.type != "restock" for x in i.risks)]
    alerts = [
        {"sku": i.sku, "product_name": i.product_name, "variant_name": i.variant_name, "branch_name": i.branch_name,
         "type": x.type, "level": x.level, "title": x.title, "reason": x.reason}
        for i in insights for x in i.risks if x.level == "high"
    ][:6]

    recent = (Sale.objects.filter(business=business, branch__in=branches)
              .select_related("branch").prefetch_related("lines")[:5])
    data = {
        "date": timezone.localdate().isoformat(),
        "revenue": str(s["total"] - r["total"]),
        "returns_total": str(r["total"]),
        "sales_count": s["n"],
        "items_sold": items,
        "stock_units": stock_agg["units"],
        "low_stock_count": low.count(),
        "risky_count": len(risky),
        "low_stock": [
            {"sku": x.variant.sku, "product_name": x.variant.product.name,
             "variant_name": f"{x.variant.color.name} / {x.variant.size.name}", "branch_name": x.branch.name,
             "quantity": x.quantity, "min_stock": x.min_q}
            for x in low[:6]
        ],
        "alerts": alerts,
        "recent_sales": [
            {"id": x.id, "created_at": x.created_at.isoformat(), "branch_name": x.branch.name, "total": str(x.total),
             "items": sum(line.quantity for line in x.lines.all())}
            for x in recent
        ],
        "formulas": FORMULAS,
    }
    if is_manager:
        data["gross_profit"] = str((s["total"] - s["cost"]) - (r["total"] - r["cost"]))
        data["stock_value"] = str(stock_agg["value"])
    return data
