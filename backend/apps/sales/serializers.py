from rest_framework import serializers

from apps.accounts.models import Branch
from apps.catalog.models import ProductVariant
from apps.common.fields import AllowedBranchPKField, BusinessScopedPKField

from .models import Sale, SaleLine, SaleReturn, SaleReturnLine


class SaleLineInputSerializer(serializers.Serializer):
    variant = BusinessScopedPKField(queryset=ProductVariant.objects.filter(is_active=True)
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
    returned_quantity = serializers.SerializerMethodField()

    class Meta:
        model = SaleLine
        fields = ["id", "variant", "sku", "variant_name", "quantity", "unit_price", "discount_amount", "line_total",
                  "below_cost", "returned_quantity"]

    def get_returned_quantity(self, obj) -> int:
        return sum(r.quantity for r in obj.return_lines.all())


class SaleReturnLineSerializer(serializers.ModelSerializer):
    sku = serializers.CharField(source="sale_line.variant.sku", read_only=True)

    class Meta:
        model = SaleReturnLine
        fields = ["id", "sale_line", "sku", "quantity", "refund_amount"]


class SaleReturnSerializer(serializers.ModelSerializer):
    lines = SaleReturnLineSerializer(many=True, read_only=True)

    class Meta:
        model = SaleReturn
        fields = ["id", "created_at", "sale", "refund_total", "reason", "lines"]


class SaleReturnItemInput(serializers.Serializer):
    sale_line = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)


class SaleReturnCreateSerializer(serializers.Serializer):
    lines = SaleReturnItemInput(many=True, allow_empty=False)
    reason = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")


class SaleSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source="branch.name", read_only=True)
    cashier_name = serializers.SerializerMethodField()
    payment_type_display = serializers.CharField(source="get_payment_type_display", read_only=True)
    lines = SaleLineSerializer(many=True, read_only=True)
    returns = SaleReturnSerializer(many=True, read_only=True)
    returned_total = serializers.SerializerMethodField()

    class Meta:
        model = Sale
        fields = ["id", "created_at", "branch", "branch_name", "cashier", "cashier_name", "payment_type",
                  "payment_type_display", "subtotal", "discount_total", "total", "returned_total", "note", "lines",
                  "returns", "idempotency_key"]

    def get_returned_total(self, obj) -> str:
        return str(sum((r.refund_total for r in obj.returns.all()), 0))

    def get_cashier_name(self, obj) -> str:
        return (obj.cashier.full_name or obj.cashier.phone) if obj.cashier else ""


class SaleManagerSerializer(SaleSerializer):
    """Menejer va egaga tannarx va yalpi foyda ham ko'rinadi."""

    gross_profit = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta(SaleSerializer.Meta):
        fields = SaleSerializer.Meta.fields + ["cost_total", "gross_profit"]
