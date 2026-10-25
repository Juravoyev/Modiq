from django.db.models import F, Q
from rest_framework import mixins, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.common.permissions import IsBusinessMember, IsManagerOrReadOnly

from . import services
from .models import Receipt, Stock, StockMovement, Transfer
from .serializers import ReceiptSerializer, StockMovementSerializer, StockSerializer, TransferSerializer

MANAGER_WRITE = [permissions.IsAuthenticated, IsBusinessMember, IsManagerOrReadOnly]


class StockViewSet(viewsets.ReadOnlyModelViewSet):
    """Qoldiqlar. ?low=true kam qolgan variantlarni qaytaradi."""

    serializer_class = StockSerializer
    queryset = Stock.objects.none()  # API sxemasi uchun; haqiqiy queryset get_queryset() da
    filterset_fields = ["branch", "variant", "variant__product"]
    search_fields = ["variant__sku", "variant__product__name"]
    ordering_fields = ["quantity", "updated_at"]

    def get_queryset(self):
        qs = Stock.objects.filter(
            business=self.request.business, branch__in=self.request.membership.allowed_branches()
        ).select_related("branch", "variant__product", "variant__color", "variant__size")
        if self.request.query_params.get("low") in ("1", "true"):
            qs = qs.filter(
                Q(variant__min_stock__isnull=False, quantity__lte=F("variant__min_stock"))
                | Q(variant__min_stock__isnull=True, quantity__lte=F("variant__product__min_stock"))
            )
        return qs.order_by("branch_id", "variant_id")


class StockMovementViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = StockMovementSerializer
    queryset = StockMovement.objects.none()
    filterset_fields = ["branch", "variant", "kind", "ref_type", "ref_id"]

    def get_queryset(self):
        return StockMovement.objects.filter(
            business=self.request.business, branch__in=self.request.membership.allowed_branches()
        ).select_related("branch", "variant__product", "variant__color", "variant__size")


class _DocumentViewSet(mixins.CreateModelMixin, mixins.RetrieveModelMixin, mixins.UpdateModelMixin,
                       mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = MANAGER_WRITE
    filterset_fields = ["status"]

    def perform_create(self, serializer):
        serializer.save(business=self.request.business, created_by=self.request.user)

    def _run(self, fn):
        doc = self.get_object()  # tenant va filial tekshiruvi shu yerda
        fn(doc.pk, self.request.user)
        doc.refresh_from_db()
        return Response(self.get_serializer(doc).data)


class ReceiptViewSet(_DocumentViewSet):
    serializer_class = ReceiptSerializer
    queryset = Receipt.objects.none()

    def get_queryset(self):
        return Receipt.objects.filter(
            business=self.request.business, branch__in=self.request.membership.allowed_branches()
        ).select_related("branch").prefetch_related("lines__variant__product", "lines__variant__color",
                                                    "lines__variant__size")

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        return self._run(services.confirm_receipt)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        return self._run(services.cancel_receipt)


class TransferViewSet(_DocumentViewSet):
    serializer_class = TransferSerializer
    queryset = Transfer.objects.none()

    def get_queryset(self):
        allowed = self.request.membership.allowed_branches()
        return Transfer.objects.filter(business=self.request.business).filter(
            Q(from_branch__in=allowed) | Q(to_branch__in=allowed)
        ).select_related("from_branch", "to_branch").prefetch_related(
            "lines__variant__product", "lines__variant__color", "lines__variant__size"
        ).distinct()

    def _require_branch(self, branch):
        if not self.request.membership.allowed_branches().filter(pk=branch.pk).exists():
            raise ValidationError({"detail": f"'{branch.name}' filiali uchun ruxsatingiz yo'q."})

    @action(detail=True, methods=["post"])
    def send(self, request, pk=None):
        self._require_branch(self.get_object().from_branch)
        return self._run(services.send_transfer)

    @action(detail=True, methods=["post"])
    def receive(self, request, pk=None):
        self._require_branch(self.get_object().to_branch)
        return self._run(services.receive_transfer)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        self._require_branch(self.get_object().from_branch)
        return self._run(services.cancel_transfer)
