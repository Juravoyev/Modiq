from decimal import Decimal

from rest_framework import serializers

from apps.catalog.models import ProductVariant
from apps.common.fields import BusinessScopedPKField

from .models import Discount


class DiscountSerializer(serializers.ModelSerializer):
    sku = serializers.CharField(source="variant.sku", read_only=True)
    variant_name = serializers.CharField(source="variant.__str__", read_only=True)
    kind_display = serializers.CharField(source="get_kind_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    state = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
    approved_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Discount
        fields = ["id", "variant", "sku", "variant_name", "kind", "kind_display", "value", "price_before",
                  "price_after", "unit_cost", "below_cost", "starts_on", "ends_on", "status", "status_display",
                  "state", "note", "created_at", "created_by_name", "approved_by_name", "approved_at", "cancelled_at"]

    def get_state(self, obj) -> str:
        """Ko'rsatish uchun holat: draft, scheduled, active, finished, cancelled."""
        today = self.context["today"]
        if obj.status == Discount.Status.DRAFT:
            return "draft"
        if obj.status == Discount.Status.CANCELLED:
            return "cancelled"
        if today < obj.starts_on:
            return "scheduled"
        if today > obj.ends_on:
            return "finished"
        return "active"

    def _name(self, user):
        return (user.full_name or user.phone) if user else None

    def get_created_by_name(self, obj) -> str | None:
        return self._name(obj.created_by)

    def get_approved_by_name(self, obj) -> str | None:
        return self._name(obj.approved_by)


class DiscountCreateSerializer(serializers.Serializer):
    variant = BusinessScopedPKField(queryset=ProductVariant.objects.filter(is_active=True).select_related("product"))
    kind = serializers.ChoiceField(choices=Discount.Kind.choices)
    value = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0.01"))
    starts_on = serializers.DateField()
    ends_on = serializers.DateField()
    note = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")


class DiscountApproveSerializer(serializers.Serializer):
    allow_below_cost = serializers.BooleanField(default=False)


class ActiveDiscountSerializer(serializers.ModelSerializer):
    """Kassa uchun: faqat narxlar (tannarx yo'q)."""

    class Meta:
        model = Discount
        fields = ["id", "variant", "price_before", "price_after", "ends_on"]
