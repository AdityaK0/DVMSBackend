from django.contrib import admin
from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("total_price",)
    fields = ("product", "quantity", "unit_price", "total_price")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "order_number",
        "customer",
        "status",
        "total_amount",
        "tax_amount",
        "shipping_amount",
        "discount_amount",
        "created_at",
        "updated_at",
    )
    list_filter = ("status", "created_at", "updated_at")
    search_fields = ("order_number", "customer__name", "customer__email")
    readonly_fields = (
        "subtotal",
        "created_at",
        "updated_at",
        "shipped_at",
        "delivered_at",
    )
    inlines = [OrderItemInline]

    fieldsets = (
        ("Order Info", {
            "fields": ("order_number", "customer", "status", "notes")
        }),
        ("Amounts", {
            "fields": ("total_amount", "tax_amount", "shipping_amount", "discount_amount", "subtotal")
        }),
        ("Addresses", {
            "fields": ("shipping_address", "billing_address")
        }),
        ("Tracking", {
            "fields": ("tracking_number", "shipped_at", "delivered_at")
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at")
        }),
    )


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "product", "quantity", "unit_price", "total_price", "created_at")
    search_fields = ("order__order_number", "product__name")
    readonly_fields = ("total_price", "created_at")
