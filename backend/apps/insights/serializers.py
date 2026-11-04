from rest_framework import serializers

from apps.catalog.models import Product
from apps.common.fields import BusinessScopedPKField

from .models import InsightSettings


class InsightSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = InsightSettings
        fields = ["no_sale_days", "high_discount", "cover_days_medium", "medium_discount", "cover_days_low",
                  "low_discount", "season_end_days", "season_discount", "min_age_days"]

    def validate(self, attrs):
        get = lambda k: attrs.get(k, getattr(self.instance, k))  # noqa: E731
        if get("cover_days_low") > get("cover_days_medium"):
            raise serializers.ValidationError({"cover_days_low": "Past xavf chegarasi o'rta xavfnikidan katta bo'lmasin."})
        return attrs


class DismissSerializer(serializers.Serializer):
    product = BusinessScopedPKField(queryset=Product.objects.all())
    days = serializers.IntegerField(min_value=1, max_value=365, default=30)
