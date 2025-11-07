from django.contrib import admin
from django.utils.html import format_html

from .models import Subscription



@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "id", "vendor", "start_date", "end_date","vendor__business_name",
        "is_active", "amount", "order_id","payment_id","created_at"
    )
    search_fields = ("id", "vendor", "vendor__business_name")


