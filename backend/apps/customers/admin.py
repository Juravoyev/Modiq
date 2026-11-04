from django.contrib import admin

from .models import Customer, CustomerGroup


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ["id", "phone", "full_name", "group", "business"]
    search_fields = ["phone", "full_name"]


admin.site.register(CustomerGroup)
