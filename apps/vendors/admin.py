from django.contrib import admin
from .models import Vendor

@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ("id", "user","business_name_slug", "business_name", "business_type", "gstin", "created_at")
    search_fields = ("business_name", "gstin", "pan", "user__name")
    list_filter = ("business_type", "created_at")

