from django.contrib import admin

from .models import Sale, SaleLine


class SaleLineInline(admin.TabularInline):
    model = SaleLine
    extra = 0
    can_delete = False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ["id", "created_at", "branch", "total", "payment_type"]
    list_filter = ["payment_type", "branch"]
    inlines = [SaleLineInline]

    def has_change_permission(self, request, obj=None):
        return False
