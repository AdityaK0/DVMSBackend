from django.contrib import admin
from django.utils.html import format_html

from .models import Product, ProductImage, Vendor,Category


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    readonly_fields = ('image_preview',)
    fields = ('image', 'image_preview', 'alt_text', 'is_primary')

    def image_preview(self, obj):
        if obj.image_url:
            return format_html('<img src="{}" style="max-height: 100px;" />', obj.image_url)
        return "-"
    image_preview.short_description = "Preview"


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "id", "name", "vendor", "price", "stock_quantity",
        "category", "is_active", "created_at"
    )
    list_filter = ("category", "is_active", "created_at")
    search_fields = ("name", "sku", "vendor__business_name")
    inlines = [ProductImageInline]


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ("product", "is_primary", "alt_text", "image_preview", "created_at")
    readonly_fields = ("image_preview",)

    def image_preview(self, obj):
        if obj.image_url:
            return format_html('<img src="{}" style="max-height: 100px;" />', obj.image_url)
        return "-"
    image_preview.short_description = "Preview"


@admin.register(Category)
class ProductsCategory(admin.ModelAdmin):
    pass


# from django.contrib import admin
# from .models import Product

# @admin.register(Product)
# class ProductAdmin(admin.ModelAdmin):
#     list_display = ("id", "name", "vendor", "price", "stock_quantity", "category", "is_active", "created_at")
#     list_filter = ("category", "is_active", "created_at")
#     search_fields = ("name", "sku", "vendor__business_name")
