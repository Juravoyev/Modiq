from django.utils import timezone
from rest_framework import serializers

from apps.catalog.models import Category, Product, Season
from apps.common.fields import BusinessScopedPKField

from .models import PricingSettings, Promotion


class PricingSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = PricingSettings
        fields = ["cashier_max_discount_percent", "bonus_enabled", "bonus_percent", "bonus_max_share_percent"]


class PromotionSerializer(serializers.ModelSerializer):
    category = BusinessScopedPKField(queryset=Category.objects.all(), allow_null=True, required=False)
    season = BusinessScopedPKField(queryset=Season.objects.all(), allow_null=True, required=False)
    products = BusinessScopedPKField(queryset=Product.objects.all(), many=True, required=False)
    category_name = serializers.CharField(source="category.name", read_only=True, default=None)
    season_name = serializers.CharField(source="season.name", read_only=True, default=None)
    product_names = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()
    label = serializers.CharField(read_only=True)
    created_by_name = serializers.SerializerMethodField()
    # Natija: aksiya bilan nechta savdo bo'ldi, necha dona sotildi, qancha chegirma berildi.
    sales_count = serializers.IntegerField(read_only=True, default=0)
    units_sold = serializers.IntegerField(read_only=True, default=0)
    discount_given = serializers.DecimalField(max_digits=16, decimal_places=2, read_only=True, default=0)

    class Meta:
        model = Promotion
        fields = ["id", "name", "kind", "value", "scope", "category", "category_name", "season", "season_name",
                  "products", "product_names", "starts_on", "ends_on", "is_active", "status", "status_display",
                  "label", "created_at", "created_by_name", "sales_count", "units_sold", "discount_given"]
        read_only_fields = ["is_active"]

    def get_product_names(self, obj) -> list[str]:
        return [p.name for p in obj.products.all()]

    def get_status(self, obj) -> str:
        return obj.status_on(timezone.localdate())

    def get_status_display(self, obj) -> str:
        return Promotion.Status(obj.status_on(timezone.localdate())).label

    def get_created_by_name(self, obj) -> str:
        u = obj.created_by
        return (u.full_name or u.phone) if u else ""

    def validate(self, attrs):
        get = lambda name: attrs.get(name, getattr(self.instance, name, None) if self.instance else None)  # noqa: E731
        kind, value = get("kind") or Promotion.Kind.PERCENT, get("value")
        errors = {}
        if value is not None:
            if value <= 0:
                errors["value"] = "Chegirma 0 dan katta bo'lishi kerak."
            elif kind == Promotion.Kind.PERCENT and value > 90:
                errors["value"] = "Foiz 90 dan oshmasligi kerak."
            elif kind == Promotion.Kind.PERCENT and value != value.to_integral_value():
                errors["value"] = "Foiz butun son bo'lishi kerak."
        starts, ends = get("starts_on"), get("ends_on")
        if starts and ends and ends < starts:
            errors["ends_on"] = "Tugash sanasi boshlanish sanasidan oldin bo'lmasligi kerak."

        scope = get("scope") or Promotion.Scope.ALL
        # Faqat tanlangan qamrovga tegishli maydon saqlanadi, qolganlari tozalanadi.
        if scope == Promotion.Scope.CATEGORY:
            if not get("category"):
                errors["category"] = "Kategoriyani tanlang."
        else:
            attrs["category"] = None
        if scope == Promotion.Scope.SEASON:
            if not get("season"):
                errors["season"] = "Mavsumni tanlang."
        else:
            attrs["season"] = None
        if scope == Promotion.Scope.PRODUCTS:
            products = attrs.get("products")
            if products is None and self.instance is not None:
                products = list(self.instance.products.all())
            if not products:
                errors["products"] = "Kamida bitta tovarni tanlang."
        else:
            attrs["products"] = []
        if errors:
            raise serializers.ValidationError(errors)
        return attrs
