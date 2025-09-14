from django.contrib import admin
from .models import Payment, PaymentRefund


class PaymentRefundInline(admin.TabularInline):
    model = PaymentRefund
    extra = 0
    fields = ("amount", "reason", "status", "created_at", "processed_at")
    readonly_fields = ("created_at", "processed_at")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "order",
        "payment_method",
        "amount",
        "currency",
        "status",
        "transaction_id",
        "created_at",
        "updated_at",
    )
    list_filter = ("payment_method", "status", "created_at", "updated_at")
    search_fields = ("id", "order__order_number", "transaction_id")
    readonly_fields = ("created_at", "updated_at", "processed_at")
    inlines = [PaymentRefundInline]

    fieldsets = (
        ("Payment Info", {
            "fields": ("order", "payment_method", "amount", "currency", "status")
        }),
        ("Gateway Details", {
            "fields": ("transaction_id", "gateway_response")
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at", "processed_at")
        }),
    )


@admin.register(PaymentRefund)
class PaymentRefundAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "payment",
        "amount",
        "status",
        "created_at",
        "processed_at",
    )
    list_filter = ("status", "created_at")
    search_fields = ("id", "payment__id", "payment__order__order_number")
    readonly_fields = ("created_at", "processed_at")
