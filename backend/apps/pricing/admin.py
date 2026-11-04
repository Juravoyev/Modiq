from django.contrib import admin

from .models import PricingSettings, Promotion


@admin.register(Promotion)
class PromotionAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "business", "kind", "value", "scope", "starts_on", "ends_on", "is_active"]
    list_filter = ["kind", "scope", "is_active"]


admin.site.register(PricingSettings)
