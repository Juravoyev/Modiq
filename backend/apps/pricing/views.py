from decimal import Decimal

from django.db.models import Count, DecimalField, IntegerField, OuterRef, Subquery, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import permissions
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import IsBusinessMember, IsManagerOrReadOnly
from apps.common.views import BusinessScopedViewSet
from apps.sales.models import SaleLine

from .models import PricingSettings, Promotion
from .serializers import PricingSettingsSerializer, PromotionSerializer

MANAGER_WRITE = [permissions.IsAuthenticated, IsBusinessMember, IsManagerOrReadOnly]


def _line_stat(expr, output):
    """Aksiya qo'llangan savdo qatorlari bo'yicha yig'indi (M2M join takrorlanishidan xoli subquery)."""
    qs = (SaleLine.objects.filter(promotion=OuterRef("pk")).order_by().values("promotion")
          .annotate(v=expr).values("v"))
    zero = Decimal("0") if isinstance(output, DecimalField) else 0
    return Coalesce(Subquery(qs, output_field=output), Value(zero, output_field=output))


class PromotionViewSet(BusinessScopedViewSet):
    """Aksiyalar. O'qish hammaga, yaratish va o'zgartirish egasi va menejerga.

    ?status=active|scheduled|ended|stopped bilan filtrlanadi.
    """

    queryset = Promotion.objects.all()
    serializer_class = PromotionSerializer
    permission_classes = MANAGER_WRITE
    search_fields = ["name"]
    filterset_fields = ["scope", "kind"]

    def get_queryset(self):
        qs = super().get_queryset().select_related("category", "season", "created_by").prefetch_related("products")
        qs = qs.annotate(
            sales_count=_line_stat(Count("sale", distinct=True), IntegerField()),
            units_sold=_line_stat(Sum("quantity"), IntegerField()),
            discount_given=_line_stat(Sum("auto_discount"), DecimalField(max_digits=16, decimal_places=2)),
        )
        status = self.request.query_params.get("status")
        if status:
            today = timezone.localdate()
            filters = {
                Promotion.Status.ACTIVE: {"is_active": True, "starts_on__lte": today, "ends_on__gte": today},
                Promotion.Status.SCHEDULED: {"is_active": True, "starts_on__gt": today},
                Promotion.Status.ENDED: {"is_active": True, "ends_on__lt": today},
                Promotion.Status.STOPPED: {"is_active": False},
            }
            if status not in filters:
                raise ValidationError({"status": "Noto'g'ri holat."})
            qs = qs.filter(**filters[status])
        return qs

    def perform_create(self, serializer):
        serializer.save(business=self.request.business, created_by=self.request.user)

    def _respond(self, promo):
        return Response(self.get_serializer(self.get_queryset().get(pk=promo.pk)).data)

    @action(detail=True, methods=["post"])
    def stop(self, request, pk=None):
        """Aksiyani muddatidan oldin to'xtatadi. Tarixdagi savdolar o'zgarmaydi."""
        promo = self.get_object()
        promo.is_active = False
        promo.save(update_fields=["is_active", "updated_at"])
        return self._respond(promo)

    @action(detail=True, methods=["post"])
    def resume(self, request, pk=None):
        promo = self.get_object()
        promo.is_active = True
        promo.save(update_fields=["is_active", "updated_at"])
        return self._respond(promo)


@extend_schema(request=PricingSettingsSerializer, responses=PricingSettingsSerializer)
class PricingSettingsView(APIView):
    """Chegirma sozlamalari: o'qish hammaga (kassa chegarani ko'rsatadi), o'zgartirish egasi va menejerga."""

    permission_classes = MANAGER_WRITE

    def get(self, request):
        return Response(PricingSettingsSerializer(PricingSettings.for_business(request.business)).data)

    def patch(self, request):
        obj = PricingSettings.for_business(request.business)
        s = PricingSettingsSerializer(obj, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        s.save()
        return Response(s.data)
