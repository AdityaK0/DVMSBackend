from django.contrib import admin
from django.utils.html import format_html

from .models import Product,Category


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "id", "name", "vendor", "price", "stock_quantity",
        "category", "is_active", "created_at"
    )
    list_filter = ("category", "is_active", "created_at")
    search_fields = ("name", "sku", "vendor__business_name")


@admin.register(Category)
class ProductsCategory(admin.ModelAdmin):
    pass