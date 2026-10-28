from rest_framework import serializers

from apps.accounts.models import Branch
from apps.catalog.models import ProductVariant
from apps.common.fields import AllowedBranchPKField, BusinessScopedPKField

from .models import Sale, SaleLine


class SaleLineInputSerializer(serializers.Serializer):
    variant = BusinessScopedPKField(queryset=ProductVariant.objects.filter(is_active=True, product__is_active=True)
                                    .select_related("product", "color", "size"))
    quantity = serializers.IntegerField(min_value=1, max_value=10000)
    discount_amount = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=0, default=0)


class SaleCreateSerializer(serializers.Serializer):
    idempotency_key = serializers.UUIDField()
    branch = AllowedBranchPKField(queryset=Branch.objects.all())
    payment_type = serializers.ChoiceField(choices=Sale.PaymentType.choices, default=Sale.PaymentType.CASH)
    lines = SaleLineInputSerializer(many=True, allow_empty=False)
    allow_below_cost = serializers.BooleanField(default=False)
    note = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")


class SaleLineSerializer(serializers.ModelSerializer):
    sku = serializers.CharField(source="variant.sku", read_only=True)
    variant_name = serializers.CharField(source="variant.__str__", read_only=True)

    class Meta:
        model = SaleLine
        fields = ["id", "variant", "sku", "variant_name", "quantity", "unit_price", "discount_amount", "line_total",
                  "below_cost"]


class SaleSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source="branch.name", read_only=True)
    cashier_name = serializers.SerializerMethodField()
    payment_type_display = serializers.CharField(source="get_payment_type_display", read_only=True)
    lines = SaleLineSerializer(many=True, read_only=True)

    class Meta:
        model = Sale
        fields = ["id", "created_at", "branch", "branch_name", "cashier", "cashier_name", "payment_type",
                  "payment_type_display", "subtotal", "discount_total", "total", "note", "lines", "idempotency_key"]

    def get_cashier_name(self, obj) -> str:
        return (obj.cashier.full_name or obj.cashier.phone) if obj.cashier else ""


class SaleManagerSerializer(SaleSerializer):
    """Menejer va egaga tannarx va yalpi foyda ham ko'rinadi."""

    gross_profit = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta(SaleSerializer.Meta):
        fields = SaleSerializer.Meta.fields + ["cost_total", "gross_profit"]
