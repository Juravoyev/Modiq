from rest_framework import serializers

from apps.accounts.models import Branch
from apps.catalog.models import ProductVariant
from apps.common.fields import AllowedBranchPKField, BusinessScopedPKField

from .models import Sale, SaleLine, SaleReturn, SaleReturnLine
from .services import return_deadline


def _user_name(user) -> str:
    return (user.full_name or user.phone) if user else ""


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
    returned_quantity = serializers.SerializerMethodField(
        help_text="Qaytarilgan yoki qaytarish tasdiqini kutayotgan miqdor")

    class Meta:
        model = SaleLine
        fields = ["id", "variant", "sku", "variant_name", "quantity", "unit_price", "discount_amount", "line_total",
                  "below_cost", "returned_quantity"]

    def get_returned_quantity(self, obj) -> int:
        # return_lines__sale_return oldindan yuklangan (prefetch), shuning uchun qo'shimcha so'rov yo'q.
        return sum(rl.quantity for rl in obj.return_lines.all() if rl.sale_return.status != SaleReturn.Status.REJECTED)


class SaleSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source="branch.name", read_only=True)
    cashier_name = serializers.SerializerMethodField()
    payment_type_display = serializers.CharField(source="get_payment_type_display", read_only=True)
    lines = SaleLineSerializer(many=True, read_only=True)
    return_deadline = serializers.SerializerMethodField()

    class Meta:
        model = Sale
        fields = ["id", "created_at", "branch", "branch_name", "cashier", "cashier_name", "payment_type",
                  "payment_type_display", "subtotal", "discount_total", "total", "note", "lines", "idempotency_key",
                  "return_deadline"]

    def get_cashier_name(self, obj) -> str:
        return _user_name(obj.cashier)

    def get_return_deadline(self, obj) -> str:
        return return_deadline(obj).isoformat()


class SaleManagerSerializer(SaleSerializer):
    """Menejer va egaga tannarx va yalpi foyda ham ko'rinadi."""

    gross_profit = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta(SaleSerializer.Meta):
        fields = SaleSerializer.Meta.fields + ["cost_total", "gross_profit"]


class ReturnLineInputSerializer(serializers.Serializer):
    sale_line = serializers.PrimaryKeyRelatedField(queryset=SaleLine.objects.select_related("variant"))
    quantity = serializers.IntegerField(min_value=1, max_value=10000)


class SaleReturnCreateSerializer(serializers.Serializer):
    sale = serializers.PrimaryKeyRelatedField(queryset=Sale.objects.all())
    reason = serializers.CharField(max_length=255)
    lines = ReturnLineInputSerializer(many=True, allow_empty=False)

    def validate_sale(self, sale):
        # Faqat o'z biznesi va ruxsat etilgan filialdagi savdo (boshqasi "topilmadi" kabi rad etiladi).
        membership = self.context["request"].membership
        if sale.business_id != membership.business_id or not membership.allowed_branches().filter(pk=sale.branch_id).exists():
            raise serializers.ValidationError("Savdo topilmadi.")
        return sale


class SaleReturnLineSerializer(serializers.ModelSerializer):
    sku = serializers.CharField(source="sale_line.variant.sku", read_only=True)
    variant_name = serializers.CharField(source="sale_line.variant.__str__", read_only=True)

    class Meta:
        model = SaleReturnLine
        fields = ["id", "sale_line", "sku", "variant_name", "quantity", "refund_amount"]


class SaleReturnSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source="branch.name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    requested_by_name = serializers.SerializerMethodField()
    decided_by_name = serializers.SerializerMethodField()
    lines = SaleReturnLineSerializer(many=True, read_only=True)

    class Meta:
        model = SaleReturn
        fields = ["id", "created_at", "sale", "branch", "branch_name", "status", "status_display", "reason",
                  "refund_total", "requested_by", "requested_by_name", "decided_by", "decided_by_name", "decided_at",
                  "decision_note", "lines"]

    def get_requested_by_name(self, obj) -> str:
        return _user_name(obj.requested_by)

    def get_decided_by_name(self, obj) -> str:
        return _user_name(obj.decided_by)


class SaleReturnManagerSerializer(SaleReturnSerializer):
    """Menejer hisobdan chiqarilgan tannarxni (zararni) ham ko'radi."""

    class Meta(SaleReturnSerializer.Meta):
        fields = SaleReturnSerializer.Meta.fields + ["cost_total"]


class ReturnDecisionSerializer(serializers.Serializer):
    note = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
