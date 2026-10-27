import csv
import hashlib
from decimal import Decimal

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import permissions
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import IsBusinessMember, IsManager
from apps.discounts.models import Discount
from apps.insights.views import selected_branches

from .reports import REPORTS, discount_results
from .services import dashboard
from .summary import SummaryUnavailable, generate_text, weekly_facts

MANAGER = [permissions.IsAuthenticated, IsBusinessMember, IsManager]


class DashboardView(APIView):
    """Bosh sahifa ko'rsatkichlari (bugun, Toshkent vaqti bo'yicha)."""

    @extend_schema(parameters=[OpenApiParameter("branch", int)], responses={200: dict})
    def get(self, request):
        return Response(dashboard(request.business, selected_branches(request), request.membership.is_manager,
                                  donor_branches=list(request.membership.allowed_branches())))


def _csv_value(value):
    if isinstance(value, Decimal):
        return f"{value:.2f}"
    return "" if value is None else value


def report_csv(name, report):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="modiq-{name}-{report["date_to"]}.csv"'
    response.write("﻿")  # Excel o'zbekcha harflarni to'g'ri ochishi uchun
    writer = csv.writer(response)
    cols = report["columns"]
    writer.writerow([c["label"] for c in cols])
    for row in report["rows"]:
        writer.writerow([_csv_value(row.get(c["key"])) for c in cols])
    if report.get("totals"):
        writer.writerow([_csv_value(report["totals"].get(c["key"], "")) for c in cols])
    return response


class ReportView(APIView):
    """Hisobotlar: sales (group=day|week|month), products, stock, slow, seasonal. ?export=csv — CSV fayl."""

    permission_classes = MANAGER

    @extend_schema(parameters=[OpenApiParameter("branch", int), OpenApiParameter("date_from", str),
                               OpenApiParameter("date_to", str), OpenApiParameter("group", str),
                               OpenApiParameter("export", str, enum=["csv"])], responses={200: dict})
    def get(self, request, name):
        func = REPORTS.get(name)
        if func is None:
            raise NotFound("Bunday hisobot yo'q.")
        kwargs = {}
        if name in ("slow", "seasonal"):
            kwargs["donor_branches"] = list(request.membership.allowed_branches())
        report = func(request.business, selected_branches(request), request.query_params, **kwargs)
        if request.query_params.get("export") == "csv":
            return report_csv(name, report)
        return Response(report)


class DiscountResultsView(APIView):
    """Chegirma natijasi: chegirma davri va undan oldingi teng davrdagi sotuv."""

    permission_classes = MANAGER

    @extend_schema(responses={200: dict})
    def get(self, request, pk):
        discount = get_object_or_404(Discount, pk=pk, business=request.business)
        return Response(discount_results(discount))


class WeeklySummaryView(APIView):
    """Haftalik xulosa. GET: hisoblangan faktlar. POST: shu faktlardan qisqa matn (1 soat keshlanadi)."""

    permission_classes = MANAGER

    def _facts(self, request):
        return weekly_facts(request.business, selected_branches(request),
                            donor_branches=list(request.membership.allowed_branches()))

    @extend_schema(parameters=[OpenApiParameter("branch", int)], responses={200: dict})
    def get(self, request):
        return Response({"facts": self._facts(request), "configured": bool(settings.GEMINI_API_KEY)})

    @extend_schema(parameters=[OpenApiParameter("branch", int)], request=None, responses={200: dict})
    def post(self, request):
        facts = self._facts(request)
        raw = f"{request.business.pk}:{facts['davr']}:{','.join(facts['filiallar'])}"
        key = "weekly-summary:" + hashlib.sha256(raw.encode()).hexdigest()  # har qanday keshda xavfsiz kalit
        cached = None if request.data.get("refresh") else cache.get(key)
        if cached:
            return Response({**cached, "facts": facts, "cached": True})
        try:
            text = generate_text(facts)
        except SummaryUnavailable as e:
            return Response({"detail": str(e), "code": e.code, "facts": facts}, status=503)
        result = {"text": text, "generated_at": timezone.now().isoformat(), "model": settings.GEMINI_MODEL}
        cache.set(key, result, 60 * 60)
        return Response({**result, "facts": facts, "cached": False})
