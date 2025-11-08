from django.contrib import admin
from django.utils.html import format_html
from .models import SubscriptionPlan, PaymentTransaction, Subscription


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'name', 'plan_type', 'price', 'duration_days', 
        'sync_limit', 'is_active', 'created_at', 'updated_at'
    )
    list_filter = ('plan_type', 'is_active')
    search_fields = ('name', 'description', 'plan_type')
    ordering = ('price',)
    readonly_fields = ('price_in_paise', 'created_at', 'updated_at')
    fieldsets = (
        ('Plan Details', {
            'fields': ('name', 'plan_type', 'description', 'price', 'price_in_paise')
        }),
        ('Plan Settings', {
            'fields': ('duration_days', 'sync_limit', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    def save_model(self, request, obj, form, change):
        """Ensure paise is recalculated every time price changes."""
        if 'price' in form.changed_data:
            obj.price_in_paise = int(obj.price * 100)
        super().save_model(request, obj, form, change)


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'vendor', 'plan', 'colored_status', 'amount_in_rupees', 
        'razorpay_order_id', 'razorpay_payment_id', 
        'created_at', 'verified_at'
    )
    list_filter = ('status', 'currency', 'created_at', 'verified_at')
    search_fields = (
        'vendor__business_name', 'razorpay_order_id', 
        'razorpay_payment_id', 'plan__name'
    )
    readonly_fields = (
        'razorpay_order_id', 'razorpay_payment_id', 'razorpay_signature',
        'razorpay_response', 'verified_at', 'created_at', 'updated_at'
    )
    ordering = ('-created_at',)

    fieldsets = (
        ('Transaction Details', {
            'fields': (
                'vendor', 'plan', 'amount', 'currency', 
                'status', 'error_message'
            )
        }),
        ('Razorpay Proof', {
            'fields': (
                'razorpay_order_id', 'razorpay_payment_id', 
                'razorpay_signature', 'razorpay_response'
            )
        }),
        ('Timestamps', {
            'fields': ('verified_at', 'created_at', 'updated_at')
        }),
    )

    def colored_status(self, obj):
        """Show status in color."""
        color_map = {
            'created': '#999999',
            'authorized': '#0066cc',
            'captured': 'green',
            'failed': 'red',
            'cancelled': 'orange',
        }
        color = color_map.get(obj.status, 'black')
        return format_html(f'<strong style="color: {color};">{obj.status.upper()}</strong>')
    colored_status.short_description = "Status"

    def amount_in_rupees(self, obj):
        return f"₹{obj.amount / 100:.2f}"
    amount_in_rupees.short_description = "Amount (INR)"


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'vendor', 'plan', 'is_active_colored','after_webhook_called',
        'start_date', 'end_date', 'days_remaining', 
        'amount', 'created_at'
    )
    list_filter = ('is_active', 'plan__plan_type', 'created_at', 'end_date','after_webhook_called')
    search_fields = (
        'vendor__business_name', 'plan__name', 
        'transaction__razorpay_order_id'
    )
    readonly_fields = (
        'start_date', 'end_date', 'created_at', 'updated_at', 
        'order_id', 'payment_id'
    )
    ordering = ('-created_at',)
    autocomplete_fields = ('vendor', 'plan', 'transaction')

    fieldsets = (
        ('Subscription Details', {
            'fields': (
                'vendor', 'plan', 'transaction', 'amount',
                'is_active', 'start_date', 'end_date'
            )
        }),
        ('Razorpay Legacy', {
            'fields': ('order_id', 'payment_id')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    def is_active_colored(self, obj):
        color = 'green' if obj.is_active else 'red'
        text = 'Active' if obj.is_active else 'Inactive'
        return format_html(f'<b style="color:{color}">{text}</b>')
    is_active_colored.short_description = "Active Status"

    def days_remaining(self, obj):
        return f"{obj.days_remaining} days"
    days_remaining.short_description = "Days Remaining"
