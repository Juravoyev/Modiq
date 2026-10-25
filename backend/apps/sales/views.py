from rest_framework import mixins, viewsets
from rest_framework.response import Response

from .models import Sale
from .serializers import SaleCreateSerializer, SaleManagerSerializer, SaleSerializer
from .services import LineInput, create_sale


class SaleViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin,
                  viewsets.GenericViewSet):
    """Kassa. POST savdoni yakunlaydi, GET savdolar tarixi."""

    queryset = Sale.objects.none()  # API sxemasi uchun
    filterset_fields = ["branch", "payment_type", "cashier"]
    ordering_fields = ["created_at", "total"]

    def get_queryset(self):
        return Sale.objects.filter(
            business=self.request.business, branch__in=self.request.membership.allowed_branches()
        ).select_related("branch", "cashier").prefetch_related(
            "lines__variant__product", "lines__variant__color", "lines__variant__size"
        )

    def get_serializer_class(self):
        if self.action == "create":
            return SaleCreateSerializer
        if getattr(self, "swagger_fake_view", False):
            return SaleManagerSerializer
        return SaleManagerSerializer if self.request.membership.is_manager else SaleSerializer

    def create(self, request, *args, **kwargs):
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        data = s.validated_data
        sale, created = create_sale(
            business=request.business, branch=data["branch"], user=request.user, membership=request.membership,
            lines=[LineInput(line["variant"], line["quantity"], line["discount_amount"]) for line in data["lines"]],
            payment_type=data["payment_type"], idempotency_key=data["idempotency_key"],
            allow_below_cost=data["allow_below_cost"], note=data["note"],
        )
        out_cls = SaleManagerSerializer if request.membership.is_manager else SaleSerializer
        sale = self.get_queryset().get(pk=sale.pk)
        return Response(out_cls(sale, context={"request": request}).data, status=201 if created else 200)
