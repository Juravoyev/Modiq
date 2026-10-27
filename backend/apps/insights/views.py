from collections import Counter

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import IsBusinessMember, IsManagerOrReadOnly

from .engine import compute_insights
from .models import RiskSettings
from .serializers import RiskSettingsSerializer


def selected_branches(request):
    allowed = request.membership.allowed_branches()
    branch_id = request.query_params.get("branch")
    if branch_id and branch_id.isdigit():
        return list(allowed.filter(pk=int(branch_id)))
    return list(allowed)


class RiskListView(APIView):
    """Xavfli variantlar ro'yxati: har birida sabab ("Nega bu tavsiya berildi?") va tavsiya etilgan harakat."""

    @extend_schema(parameters=[
        OpenApiParameter("branch", int), OpenApiParameter("type", str, enum=["no_sale", "overstock", "seasonal", "restock"]),
        OpenApiParameter("level", str, enum=["high", "medium", "low"]),
    ], responses={200: dict})
    def get(self, request):
        items = compute_insights(request.business, selected_branches(request),
                                donor_branches=list(request.membership.allowed_branches()))
        risk_type = request.query_params.get("type")
        level = request.query_params.get("level")
        data = []
        for item in items:
            d = item.as_dict()
            if risk_type and not any(r["type"] == risk_type for r in d["risks"]):
                continue
            if level and not any(r["level"] == level for r in d["risks"]):
                continue
            data.append(d)
        counts = Counter(r.type for i in items for r in i.risks)
        levels = Counter(r.level for i in items for r in i.risks)
        return Response({"count": len(data), "by_type": counts, "by_level": levels, "results": data})


class RiskSettingsView(generics.RetrieveUpdateAPIView):
    serializer_class = RiskSettingsSerializer
    permission_classes = [permissions.IsAuthenticated, IsBusinessMember, IsManagerOrReadOnly]

    def get_object(self):
        return RiskSettings.for_business(self.request.business)
