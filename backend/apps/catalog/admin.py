from django.contrib import admin

from .models import Brand, Category, Color, Product, ProductVariant, Season, Size


class VariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 0


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["name", "article", "business", "sale_price", "is_active"]
    search_fields = ["name", "article"]
    inlines = [VariantInline]


for m in (Category, Brand, Season, Color, Size):
    admin.site.register(m)
