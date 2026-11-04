from decimal import Decimal

from rest_framework import permissions
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common import llm
from apps.common.permissions import IsBusinessMember, IsManager

from . import ai
from .models import InsightSettings
from .serializers import DismissSerializer, InsightSettingsSerializer
from .services import build_recommendations, dismiss, summary_totals

MANAGER = [permissions.IsAuthenticated, IsBusinessMember, IsManager]


def _money(value):
    if isinstance(value, Decimal):
        return f"{value:.2f}"
    if isinstance(value, dict):
        return {k: _money(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_money(v) for v in value]
    return value


def _branches(request):
    branches = request.membership.allowed_branches()
    branch_id = request.query_params.get("branch")
    if branch_id:
        if not branch_id.isdigit():
            raise ValidationError({"branch": "Noto'g'ri filial."})
        branches = branches.filter(pk=int(branch_id))
    return branches


class RecommendationsView(APIView):
    """Sotilmay qolish xavfi bo'lgan tovarlar va tavsiya qilingan chegirma (egasi va menejer). ?branch=<id>"""

    permission_classes = MANAGER

    def get(self, request):
        recs = build_recommendations(business=request.business, branches=_branches(request))
        return Response(_money({"summary": summary_totals(recs), "results": recs,
                                "ai_configured": llm.configured()}))


class SummaryView(APIView):
    """Gemini xulosasi. POST ?branch=<id>&refresh=1 — keshni chetlab o'tib qayta yozdirish."""

    permission_classes = MANAGER

    def post(self, request):
        recs = build_recommendations(business=request.business, branches=_branches(request))
        result = ai.summarize(business_id=request.business.id, recs=recs, totals=summary_totals(recs),
                              refresh=request.query_params.get("refresh") == "1")
        return Response(result)


class DismissView(APIView):
    """Tavsiyani rad etish: tovar N kun (standart 30) tavsiyalarda ko'rinmaydi."""

    permission_classes = MANAGER

    def post(self, request):
        s = DismissSerializer(data=request.data, context={"request": request})
        s.is_valid(raise_exception=True)
        until = dismiss(business=request.business, product=s.validated_data["product"], user=request.user,
                        days=s.validated_data["days"])
        return Response({"until": until.isoformat()})


class InsightSettingsView(APIView):
    permission_classes = MANAGER

    def get(self, request):
        return Response(InsightSettingsSerializer(InsightSettings.for_business(request.business)).data)

    def patch(self, request):
        s = InsightSettingsSerializer(InsightSettings.for_business(request.business), data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        s.save()
        return Response(s.data)
