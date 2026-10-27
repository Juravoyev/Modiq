from django.contrib import admin

from .models import Discount


@admin.register(Discount)
class DiscountAdmin(admin.ModelAdmin):
    list_display = ["variant", "kind", "value", "price_before", "price_after", "starts_on", "ends_on", "status"]
    list_filter = ["status", "kind"]
