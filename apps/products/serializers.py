from rest_framework import serializers
from .models import Product, Category


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'
        


class ProductSerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source='vendor.business_name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    is_in_stock = serializers.ReadOnlyField()
    is_low_stock = serializers.ReadOnlyField()
    image_urls = serializers.ListField(
        child=serializers.CharField(),
        required=False
    )
    sizes = serializers.ListField(
        child=serializers.CharField(),
        required=True
    )

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'description', 'category', 'price', 'cost_price','vendor_id',
            'stock_quantity', 'min_stock_level', 'sku', 'sizes','gender', 'dimensions',
            'is_active', 'is_featured', 'meta_title', 'meta_description',
            'created_at', 'updated_at', 'image_urls', 'primary_image',
            'vendor_name', 'category_name', 'is_in_stock', 'is_low_stock',
        ]
        read_only_fields = ['vendor', 'created_at', 'updated_at', 'is_archived']

    def validate_sku(self, value):
        request = self.context.get("request")
        vendor = getattr(getattr(request, "user", None), "vendor", None)
        if not vendor:
            raise serializers.ValidationError("Vendor not found for this user.")

        qs = Product.objects.filter(sku=value, vendor=vendor)

        # Exclude the current product when updating
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise serializers.ValidationError("Product with this SKU already exists for your store.")

        return value

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Price must be greater than zero.")
        return value

    def validate_stock_quantity(self, value):
        if value < 0:
            raise serializers.ValidationError("Stock quantity cannot be negative.")
        return value



class ProductUpdateSerializer(serializers.ModelSerializer):
    """Used only for UPDATE product"""

    class Meta:
        model = Product
        fields = "__all__"
        extra_kwargs = {
            "image_urls": {"read_only": True},
            "primary_image": {"read_only": True},
        }
        
    
    def validate(self, attrs):
        """Custom validation for featured products."""

        # If is_featured was not provided → skip validation
        if 'is_featured' not in attrs:
            return attrs

        new_value = attrs['is_featured']
        product = self.instance
        vendor = product.vendor
        portfolio = getattr(vendor, 'portfolio', None)

        # If no portfolio yet → safe to continue
        if not portfolio:
            return attrs

        if new_value is True:
            # Count existing featured products (excluding current)
            current_featured_count = (
                portfolio.featured_products
                .exclude(id=product.id)
                .count()
            )

            if current_featured_count >= 8:
                raise serializers.ValidationError({
                    "is_featured": [
                        "You can only feature up to 8 products."
                    ]
                })

        return attrs    



class ProductListSerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source='vendor.business_name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    images = serializers.SerializerMethodField()
    is_in_stock = serializers.ReadOnlyField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'description', 'price', 'stock_quantity', 'vendor_name',
            'category_name', 'meta_title', 'meta_description', 'images','sizes',
            'is_in_stock', 'is_featured', 'created_at', 'is_active','gender'
        ]

    def get_images(self, obj):
        """
        Return up to 4 images from Product.image_urls,
        ensuring the primary_image is always first.
        """
        images = obj.image_urls or []
        primary = obj.primary_image

        # Move primary image to the front if exists
        if primary and primary in images:
            images = [primary] + [img for img in images if img != primary]
        elif primary and primary not in images:
            images = [primary] + images

        return images[:4]  
    