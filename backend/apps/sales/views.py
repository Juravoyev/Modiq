from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Sale, SaleReturn
from .serializers import (
    ReturnDecisionSerializer,
    SaleCreateSerializer,
    SaleManagerSerializer,
    SaleReturnCreateSerializer,
    SaleReturnManagerSerializer,
    SaleReturnSerializer,
    SaleSerializer,
)
from .services import LineInput, ReturnLineInput, create_return, create_sale, decide_return


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
            "lines__variant__product", "lines__variant__color", "lines__variant__size",
            "lines__return_lines__sale_return",
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


class SaleReturnViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin,
                        viewsets.GenericViewSet):
    """Yaroqsiz tovarni qaytarish. Sotuvchi so'rov yaratadi, huquqi bor xodim tasdiqlaydi yoki rad etadi."""

    queryset = SaleReturn.objects.none()  # API sxemasi uchun
    filterset_fields = ["status", "branch", "sale"]

    def get_queryset(self):
        return SaleReturn.objects.filter(
            business=self.request.business, branch__in=self.request.membership.allowed_branches()
        ).select_related("branch", "requested_by", "decided_by").prefetch_related(
            "lines__sale_line__variant__product", "lines__sale_line__variant__color", "lines__sale_line__variant__size"
        )

    def get_serializer_class(self):
        if self.action == "create":
            return SaleReturnCreateSerializer
        if self.action in ("approve", "reject"):
            return ReturnDecisionSerializer
        return self._out_cls()

    def _out_cls(self):
        if getattr(self, "swagger_fake_view", False) or self.request.membership.is_manager:
            return SaleReturnManagerSerializer
        return SaleReturnSerializer

    def _respond(self, sale_return, status=200):
        obj = self.get_queryset().get(pk=sale_return.pk)
        return Response(self._out_cls()(obj, context={"request": self.request}).data, status=status)

    def create(self, request, *args, **kwargs):
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        data = s.validated_data
        sale_return = create_return(
            sale=data["sale"], user=request.user, membership=request.membership, reason=data["reason"],
            lines=[ReturnLineInput(line["sale_line"], line["quantity"]) for line in data["lines"]],
        )
        return self._respond(sale_return, status=201)

    def _decide(self, approve):
        sale_return = self.get_object()  # tenant va filial tekshiruvi
        s = self.get_serializer(data=self.request.data)
        s.is_valid(raise_exception=True)
        decide_return(sale_return.pk, user=self.request.user, membership=self.request.membership, approve=approve,
                      note=s.validated_data["note"])
        return self._respond(sale_return)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        return self._decide(True)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        return self._decide(False)
