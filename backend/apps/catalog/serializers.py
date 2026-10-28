from django.db import transaction
from rest_framework import serializers

from apps.common.fields import BusinessScopedPKField
from apps.common.serializers import HideCostFieldsMixin

from .models import Brand, Category, Color, Product, ProductVariant, Season, Size
from .services import generate_variants


class UniqueNamePerBusinessMixin:
    """Nom takrorlanmasligini serializer darajasida tekshiradi (DB constraint ham bor)."""

    def validate_name(self, value):
        qs = self.Meta.model.objects.filter(business=self.context["request"].business, name__iexact=value)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Bu nom allaqachon mavjud.")
        return value


class CategorySerializer(UniqueNamePerBusinessMixin, serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name"]


class BrandSerializer(UniqueNamePerBusinessMixin, serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ["id", "name"]


class SeasonSerializer(UniqueNamePerBusinessMixin, serializers.ModelSerializer):
    class Meta:
        model = Season
        fields = ["id", "name", "start_month", "end_month"]


class ColorSerializer(UniqueNamePerBusinessMixin, serializers.ModelSerializer):
    class Meta:
        model = Color
        fields = ["id", "name", "code", "hex"]


class SizeSerializer(UniqueNamePerBusinessMixin, serializers.ModelSerializer):
    class Meta:
        model = Size
        fields = ["id", "name", "sort_order"]


class VariantSerializer(HideCostFieldsMixin, serializers.ModelSerializer):
    cost_fields = ("purchase_price", "effective_purchase_price")

    product_name = serializers.CharField(source="product.name", read_only=True)
    color_name = serializers.CharField(source="color.name", read_only=True)
    size_name = serializers.CharField(source="size.name", read_only=True)
    effective_purchase_price = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    effective_sale_price = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    effective_min_stock = serializers.IntegerField(read_only=True)
    stock = serializers.IntegerField(read_only=True, default=None,
                                     help_text="?branch= berilsa shu filial, aks holda barcha ruxsat etilgan filiallar")

    class Meta:
        model = ProductVariant
        fields = [
            "id", "product", "product_name", "color", "color_name", "size", "size_name", "sku", "barcode",
            "purchase_price", "sale_price", "min_stock", "is_active",
            "effective_purchase_price", "effective_sale_price", "effective_min_stock", "stock",
        ]
        read_only_fields = ["product", "color", "size"]

    def validate_sku(self, value):
        qs = ProductVariant.objects.filter(business=self.context["request"].business, sku=value)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Bu SKU allaqachon mavjud.")
        return value


class ProductSerializer(HideCostFieldsMixin, serializers.ModelSerializer):
    cost_fields = ("purchase_price",)

    category = BusinessScopedPKField(queryset=Category.objects.all(), allow_null=True, required=False)
    brand = BusinessScopedPKField(queryset=Brand.objects.all(), allow_null=True, required=False)
    season = BusinessScopedPKField(queryset=Season.objects.all(), allow_null=True, required=False)
    variants = VariantSerializer(many=True, read_only=True)
    total_stock = serializers.IntegerField(read_only=True, default=0,
                                           help_text="Barcha variantlar qoldig'i yig'indisi")
    # Yaratishda rang va o'lchamlar berilsa, variantlar matritsasi avtomatik yaratiladi.
    color_ids = BusinessScopedPKField(queryset=Color.objects.all(), many=True, write_only=True, required=False)
    size_ids = BusinessScopedPKField(queryset=Size.objects.all(), many=True, write_only=True, required=False)

    class Meta:
        model = Product
        fields = [
            "id", "name", "article", "category", "brand", "season", "purchase_price", "sale_price",
            "min_stock", "image", "is_active", "total_stock", "variants", "color_ids", "size_ids",
        ]

    def validate_article(self, value):
        qs = Product.objects.filter(business=self.context["request"].business, article__iexact=value)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Bu artikul allaqachon mavjud.")
        return value

    def validate(self, attrs):
        if bool(attrs.get("color_ids")) != bool(attrs.get("size_ids")):
            raise serializers.ValidationError("Variant yaratish uchun rang va o'lchamlarni birga tanlang.")
        return attrs

    @transaction.atomic
    def create(self, validated):
        colors = validated.pop("color_ids", [])
        sizes = validated.pop("size_ids", [])
        product = super().create(validated)
        if colors:
            generate_variants(product, colors, sizes)
        return product

    def update(self, instance, validated):
        validated.pop("color_ids", None)
        validated.pop("size_ids", None)
        return super().update(instance, validated)


class GenerateVariantsSerializer(serializers.Serializer):
    color_ids = BusinessScopedPKField(queryset=Color.objects.all(), many=True, allow_empty=False)
    size_ids = BusinessScopedPKField(queryset=Size.objects.all(), many=True, allow_empty=False)
