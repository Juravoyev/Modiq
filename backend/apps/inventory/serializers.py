from django.db import transaction
from rest_framework import serializers

from apps.accounts.models import Branch
from apps.catalog.models import ProductVariant
from apps.common.fields import AllowedBranchPKField, BusinessScopedPKField

from .models import Receipt, ReceiptLine, Stock, StockMovement, Transfer, TransferLine


class VariantLabelMixin(serializers.Serializer):
    sku = serializers.CharField(source="variant.sku", read_only=True)
    variant_name = serializers.CharField(source="variant.__str__", read_only=True)


class StockSerializer(VariantLabelMixin, serializers.ModelSerializer):
    branch_name = serializers.CharField(source="branch.name", read_only=True)
    product = serializers.IntegerField(source="variant.product_id", read_only=True)
    min_stock = serializers.IntegerField(source="variant.effective_min_stock", read_only=True)
    is_low = serializers.SerializerMethodField()

    class Meta:
        model = Stock
        fields = ["id", "branch", "branch_name", "variant", "sku", "variant_name", "product", "quantity",
                  "min_stock", "is_low", "updated_at"]

    def get_is_low(self, obj) -> bool:
        return obj.quantity <= obj.variant.effective_min_stock


class StockMovementSerializer(VariantLabelMixin, serializers.ModelSerializer):
    branch_name = serializers.CharField(source="branch.name", read_only=True)
    kind_display = serializers.CharField(source="get_kind_display", read_only=True)

    class Meta:
        model = StockMovement
        fields = ["id", "created_at", "branch", "branch_name", "variant", "sku", "variant_name", "kind",
                  "kind_display", "quantity_delta", "balance_after", "ref_type", "ref_id", "user", "note"]


class _LinesMixin:
    """Qoralama hujjat qatorlarini yaratish/almashtirish. Bir variant hujjatda bir marta bo'ladi."""

    line_model = None
    parent_field = None

    def validate_lines(self, lines):
        if not lines:
            raise serializers.ValidationError("Kamida bitta tovar qo'shing.")
        ids = [line["variant"].id for line in lines]
        if len(ids) != len(set(ids)):
            raise serializers.ValidationError("Bir variant hujjatda faqat bir marta bo'lishi kerak.")
        return lines

    def _save_lines(self, doc, lines):
        doc.lines.all().delete()
        self.line_model.objects.bulk_create([self.line_model(**{self.parent_field: doc}, **line) for line in lines])

    @transaction.atomic
    def create(self, validated):
        lines = validated.pop("lines")
        doc = super().create(validated)
        self._save_lines(doc, lines)
        return doc

    @transaction.atomic
    def update(self, instance, validated):
        locked = type(instance).objects.select_for_update().get(pk=instance.pk)
        if locked.status != "draft":
            raise serializers.ValidationError({"detail": "Faqat qoralama hujjatni tahrirlash mumkin."})
        lines = validated.pop("lines", None)
        doc = super().update(instance, validated)
        if lines is not None:
            self._save_lines(doc, lines)
        return doc


class ReceiptLineSerializer(VariantLabelMixin, serializers.ModelSerializer):
    variant = BusinessScopedPKField(queryset=ProductVariant.objects.all())
    quantity = serializers.IntegerField(min_value=1)
    purchase_price = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=0)

    class Meta:
        model = ReceiptLine
        fields = ["id", "variant", "sku", "variant_name", "quantity", "purchase_price"]


class ReceiptSerializer(_LinesMixin, serializers.ModelSerializer):
    line_model = ReceiptLine
    parent_field = "receipt"

    branch = AllowedBranchPKField(queryset=Branch.objects.all())
    branch_name = serializers.CharField(source="branch.name", read_only=True)
    lines = ReceiptLineSerializer(many=True)
    total_quantity = serializers.SerializerMethodField()
    total_cost = serializers.SerializerMethodField()

    class Meta:
        model = Receipt
        fields = ["id", "branch", "branch_name", "supplier_name", "document_number", "document_date", "status",
                  "note", "lines", "total_quantity", "total_cost", "created_by", "confirmed_by", "confirmed_at",
                  "created_at"]
        read_only_fields = ["status", "created_by", "confirmed_by", "confirmed_at"]

    def get_total_quantity(self, obj) -> int:
        return sum(line.quantity for line in obj.lines.all())

    def get_total_cost(self, obj) -> str:
        return str(sum((line.quantity * line.purchase_price for line in obj.lines.all()), 0))


class TransferLineSerializer(VariantLabelMixin, serializers.ModelSerializer):
    variant = BusinessScopedPKField(queryset=ProductVariant.objects.all())
    quantity = serializers.IntegerField(min_value=1)

    class Meta:
        model = TransferLine
        fields = ["id", "variant", "sku", "variant_name", "quantity"]


class TransferSerializer(_LinesMixin, serializers.ModelSerializer):
    line_model = TransferLine
    parent_field = "transfer"

    from_branch = AllowedBranchPKField(queryset=Branch.objects.all())
    to_branch = BusinessScopedPKField(queryset=Branch.objects.filter(is_active=True))
    from_branch_name = serializers.CharField(source="from_branch.name", read_only=True)
    to_branch_name = serializers.CharField(source="to_branch.name", read_only=True)
    lines = TransferLineSerializer(many=True)

    class Meta:
        model = Transfer
        fields = ["id", "from_branch", "from_branch_name", "to_branch", "to_branch_name", "status", "note", "lines",
                  "created_by", "sent_at", "received_at", "cancelled_at", "created_at"]
        read_only_fields = ["status", "created_by", "sent_at", "received_at", "cancelled_at"]

    def validate(self, attrs):
        src = attrs.get("from_branch", getattr(self.instance, "from_branch", None))
        dst = attrs.get("to_branch", getattr(self.instance, "to_branch", None))
        if src and dst and src == dst:
            raise serializers.ValidationError({"to_branch": "Qabul qiluvchi filial jo'natuvchidan farq qilishi kerak."})
        return attrs
