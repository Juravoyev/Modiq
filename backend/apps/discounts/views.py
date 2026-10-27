from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.common.permissions import IsBusinessMember, IsManager

from .models import Discount
from .serializers import (
    ActiveDiscountSerializer,
    DiscountApproveSerializer,
    DiscountCreateSerializer,
    DiscountSerializer,
)
from .services import active_discounts, approve_discount, cancel_discount, create_discount

MANAGER = [permissions.IsAuthenticated, IsBusinessMember, IsManager]


class DiscountViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin,
                      viewsets.GenericViewSet):
    """Chegirmalar: yaratish (qoralama) -> tasdiqlash -> kassada qo'llanadi. Tarix o'chirilmaydi."""

    queryset = Discount.objects.none()
    permission_classes = MANAGER
    filterset_fields = ["variant", "status"]
    search_fields = ["variant__sku", "variant__product__name"]
    ordering_fields = ["starts_on", "created_at"]

    def get_queryset(self):
        qs = Discount.objects.filter(business=self.request.business).select_related(
            "variant__product", "variant__color", "variant__size", "created_by", "approved_by")
        state = self.request.query_params.get("state")
        today = timezone.localdate()
        approved = qs.filter(status=Discount.Status.APPROVED)
        if state == "active":
            qs = approved.filter(starts_on__lte=today, ends_on__gte=today)
        elif state == "scheduled":
            qs = approved.filter(starts_on__gt=today)
        elif state == "finished":
            qs = approved.filter(ends_on__lt=today)
        elif state in ("draft", "cancelled"):
            qs = qs.filter(status=state)
        return qs

    def get_serializer_class(self):
        if self.action == "create":
            return DiscountCreateSerializer
        if self.action == "approve":
            return DiscountApproveSerializer
        if self.action == "active":
            return ActiveDiscountSerializer
        return DiscountSerializer

    def get_serializer_context(self):
        return {**super().get_serializer_context(), "today": timezone.localdate()}

    def get_permissions(self):
        if self.action == "active":  # kassir ham chegirmadagi narxni ko'rishi kerak
            return [permissions.IsAuthenticated(), IsBusinessMember()]
        return super().get_permissions()

    def create(self, request, *args, **kwargs):
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        discount = create_discount(business=request.business, user=request.user, **s.validated_data)
        return Response(DiscountSerializer(discount, context=self.get_serializer_context()).data, status=201)

    @extend_schema(request=DiscountApproveSerializer, responses={200: DiscountSerializer})
    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        discount = self.get_object()
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        discount = approve_discount(discount.pk, user=request.user, membership=request.membership,
                                    allow_below_cost=s.validated_data["allow_below_cost"])
        return Response(DiscountSerializer(discount, context=self.get_serializer_context()).data)

    @extend_schema(request=None, responses={200: DiscountSerializer})
    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        discount = cancel_discount(self.get_object().pk, user=request.user)
        return Response(DiscountSerializer(discount, context=self.get_serializer_context()).data)

    @extend_schema(responses={200: ActiveDiscountSerializer(many=True)})
    @action(detail=False, methods=["get"])
    def active(self, request):
        """Bugun amal qilayotgan chegirmalar (kassa narxni shu yerdan ko'rsatadi)."""
        qs = active_discounts(request.business)
        return Response(ActiveDiscountSerializer(qs, many=True).data)
