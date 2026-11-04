from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Count, DecimalField, Q, Sum, Value
from django.db.models.functions import Coalesce
from rest_framework import permissions
from rest_framework.permissions import BasePermission

from apps.common.permissions import IsBusinessMember, IsManagerOrReadOnly
from apps.common.utils import normalize_phone
from apps.common.views import BusinessScopedViewSet

from .models import Customer, CustomerGroup
from .serializers import CustomerGroupSerializer, CustomerSerializer


class CanDeleteCustomer(BasePermission):
    """Mijozni sotuvchi ham qo'sha oladi (kassada), o'chirish esa faqat egasi va menejerga."""

    message = "Mijozni o'chirish uchun menejer yoki do'kon egasi huquqi kerak."

    def has_permission(self, request, view):
        if request.method != "DELETE":
            return True
        membership = getattr(request, "membership", None)
        return bool(membership and membership.is_manager)


class CustomerGroupViewSet(BusinessScopedViewSet):
    queryset = CustomerGroup.objects.all()
    serializer_class = CustomerGroupSerializer
    permission_classes = [permissions.IsAuthenticated, IsBusinessMember, IsManagerOrReadOnly]
    pagination_class = None

    def get_queryset(self):
        return super().get_queryset().annotate(customers_count=Count("customers"))


class CustomerViewSet(BusinessScopedViewSet):
    """Mijozlar. ?phone= aniq telefon bo'yicha (kassa uchun), ?search= ism yoki telefon qismi bo'yicha."""

    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [permissions.IsAuthenticated, IsBusinessMember, CanDeleteCustomer]
    search_fields = ["phone", "full_name"]
    filterset_fields = ["group"]
    ordering_fields = ["created_at", "full_name", "total_spent"]

    def get_queryset(self):
        qs = super().get_queryset().select_related("group").annotate(
            purchases_count=Count("sales", distinct=True),
            total_spent=Coalesce(Sum("sales__total"), Value(0, output_field=DecimalField(max_digits=16, decimal_places=2))),
        )
        phone = self.request.query_params.get("phone")
        if phone:
            try:
                qs = qs.filter(phone=normalize_phone(phone))
            except DjangoValidationError:
                qs = qs.none()
        return qs
