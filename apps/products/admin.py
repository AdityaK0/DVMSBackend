from django.contrib import admin
from .models import Product

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "vendor", "price", "stock_quantity", "category", "is_active", "created_at")
    list_filter = ("category", "is_active", "created_at")
    search_fields = ("name", "sku", "vendor__business_name")
