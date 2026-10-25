from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Branch, Business, Membership, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ["phone"]
    list_display = ["phone", "full_name", "is_active", "is_staff"]
    search_fields = ["phone", "full_name"]
    fieldsets = (
        (None, {"fields": ("phone", "password")}),
        ("Ma'lumot", {"fields": ("full_name",)}),
        ("Huquqlar", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
    )
    add_fieldsets = ((None, {"classes": ("wide",), "fields": ("phone", "password1", "password2")}),)


admin.site.register(Business)
admin.site.register(Branch)
admin.site.register(Membership)
