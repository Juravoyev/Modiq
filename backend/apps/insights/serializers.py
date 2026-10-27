from rest_framework import serializers

from .models import RiskSettings


class RiskSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = RiskSettings
        fields = ["no_sale_days", "sales_window_days", "min_sales_for_velocity", "overstock_cover_days",
                  "season_warning_days"]
