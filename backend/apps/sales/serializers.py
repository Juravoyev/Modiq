from rest_framework import serializers

from apps.accounts.models import Branch
from apps.catalog.models import ProductVariant
from apps.customers.models import Customer
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


class SaleQuoteSerializer(serializers.Serializer):
    branch = AllowedBranchPKField(queryset=Branch.objects.all())
    lines = SaleLineInputSerializer(many=True, allow_empty=False)
    customer = BusinessScopedPKField(queryset=Customer.objects.select_related("group"), allow_null=True,
                                     required=False, default=None)
    bonus_to_use = serializers.IntegerField(min_value=0, required=False, default=0,
                                            help_text="Bonus bilan to'lanadigan summa (butun so'm)")


class SaleCreateSerializer(SaleQuoteSerializer):
    idempotency_key = serializers.UUIDField()
    payment_type = serializers.ChoiceField(choices=Sale.PaymentType.choices, default=Sale.PaymentType.CASH)
    allow_below_cost = serializers.BooleanField(default=False)
    note = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")


def customer_brief(customer) -> dict | None:
    if customer is None:
        return None
    return {"id": customer.id, "phone": customer.phone, "full_name": customer.full_name,
            "group_name": customer.group.name if customer.group_id else None,
            "discount_percent": customer.discount_percent}


def quote_to_dict(quote) -> dict:
    """Kassa ekrani uchun hisob natijasi. Tannarx yuborilmaydi (sotuvchi ham ko'radi)."""
    money = lambda d: f"{d:.2f}"  # noqa: E731
    return {
        "customer": customer_brief(quote.customer),
        "lines": [{
            "variant": ln.variant.id, "sku": ln.variant.sku, "quantity": ln.quantity,
            "unit_price": money(ln.unit_price), "gross": money(ln.gross),
            "auto_discount": money(ln.auto_discount), "discount_source": ln.discount_source,
            "discount_label": ln.discount_label, "promotion": ln.promotion.id if ln.promotion else None,
            "manual_discount": money(ln.manual_discount), "bonus_amount": money(ln.bonus_amount),
            "line_total": money(ln.line_total),
            "below_cost": ln.below_cost,
        } for ln in quote.lines],
        "subtotal": money(quote.subtotal),
        "auto_discount_total": money(quote.auto_discount_total),
        "manual_discount_total": money(quote.manual_discount_total),
        "discount_total": money(quote.discount_total),
        "total": money(quote.total),
        "below_cost_skus": quote.below_cost_skus,
        "cashier_max_discount_percent": quote.settings.cashier_max_discount_percent,
        "bonus": {
            "enabled": quote.settings.bonus_enabled and quote.customer is not None,
            "percent": quote.settings.bonus_percent,
            "max_share_percent": quote.settings.bonus_max_share_percent,
            "available": money(quote.bonus_available),
            "pending": money(quote.bonus_pending),
            "max": money(quote.bonus_max),
            "used": money(quote.bonus_used),
            "earned": money(quote.bonus_earned),
        },
    }


class SaleLineSerializer(serializers.ModelSerializer):
    sku = serializers.CharField(source="variant.sku", read_only=True)
    variant_name = serializers.CharField(source="variant.__str__", read_only=True)
    returned_quantity = serializers.SerializerMethodField(
        help_text="Qaytarilgan yoki qaytarish tasdiqini kutayotgan miqdor")

    class Meta:
        model = SaleLine
        fields = ["id", "variant", "sku", "variant_name", "quantity", "unit_price", "auto_discount",
                  "discount_source", "discount_label", "promotion", "discount_amount", "bonus_amount", "line_total", "below_cost",
                  "returned_quantity"]

    def get_returned_quantity(self, obj) -> int:
        # return_lines__sale_return oldindan yuklangan (prefetch), shuning uchun qo'shimcha so'rov yo'q.
        return sum(rl.quantity for rl in obj.return_lines.all() if rl.sale_return.status != SaleReturn.Status.REJECTED)


class SaleSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source="branch.name", read_only=True)
    cashier_name = serializers.SerializerMethodField()
    payment_type_display = serializers.CharField(source="get_payment_type_display", read_only=True)
    lines = SaleLineSerializer(many=True, read_only=True)
    return_deadline = serializers.SerializerMethodField()
    customer_info = serializers.SerializerMethodField()

    class Meta:
        model = Sale
        fields = ["id", "created_at", "branch", "branch_name", "cashier", "cashier_name", "payment_type",
                  "payment_type_display", "subtotal", "discount_total", "total", "note", "lines", "idempotency_key",
                  "return_deadline", "customer", "customer_info", "bonus_spent", "bonus_earned"]

    def get_cashier_name(self, obj) -> str:
        return _user_name(obj.cashier)

    def get_return_deadline(self, obj) -> str:
        return return_deadline(obj).isoformat()

    def get_customer_info(self, obj) -> dict | None:
        return customer_brief(obj.customer)


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
        fields = ["id", "sale_line", "sku", "variant_name", "quantity", "refund_amount", "bonus_refund"]


class SaleReturnSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source="branch.name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    requested_by_name = serializers.SerializerMethodField()
    decided_by_name = serializers.SerializerMethodField()
    lines = SaleReturnLineSerializer(many=True, read_only=True)

    class Meta:
        model = SaleReturn
        fields = ["id", "created_at", "sale", "branch", "branch_name", "status", "status_display", "reason",
                  "refund_total", "bonus_refund", "bonus_revoked", "requested_by", "requested_by_name", "decided_by", "decided_by_name", "decided_at",
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
