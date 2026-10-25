from django.contrib import admin

from .models import Receipt, ReceiptLine, Stock, StockMovement, Transfer, TransferLine


class ReadOnlyAdmin(admin.ModelAdmin):
    """Qoldiq va jurnal faqat servislar orqali o'zgaradi, admin paneldan tahrirlab bo'lmaydi."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Stock)
class StockAdmin(ReadOnlyAdmin):
    list_display = ["variant", "branch", "quantity"]


@admin.register(StockMovement)
class StockMovementAdmin(ReadOnlyAdmin):
    list_display = ["created_at", "variant", "branch", "kind", "quantity_delta", "balance_after"]
    list_filter = ["kind"]


class ReceiptLineInline(admin.TabularInline):
    model = ReceiptLine
    extra = 0


class TransferLineInline(admin.TabularInline):
    model = TransferLine
    extra = 0


@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = ["id", "document_number", "branch", "document_date", "status"]
    readonly_fields = ["status", "confirmed_by", "confirmed_at"]
    inlines = [ReceiptLineInline]


@admin.register(Transfer)
class TransferAdmin(admin.ModelAdmin):
    list_display = ["id", "from_branch", "to_branch", "status", "created_at"]
    readonly_fields = ["status", "sent_at", "received_at", "cancelled_at"]
    inlines = [TransferLineInline]
