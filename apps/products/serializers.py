from rest_framework import serializers
from .models import Product, ProductImage, Category

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'alt_text', 'is_primary']

class ProductSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    vendor_name = serializers.CharField(source='vendor.business_name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    is_in_stock = serializers.ReadOnlyField()
    is_low_stock = serializers.ReadOnlyField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'description', 'category', 'price', 'cost_price',
            'stock_quantity', 'min_stock_level', 'sku', 'weight', 'dimensions',
            'is_active', 'is_featured', 'meta_title', 'meta_description',
            'created_at', 'updated_at', 'images', 'vendor_name', 'category_name',
            'is_in_stock', 'is_low_stock'
        ]
        read_only_fields = ['vendor', 'created_at', 'updated_at']
    
    def validate_sku(self, value):
        """Ensure SKU is unique, excluding current instance during updates"""
        queryset = Product.objects.filter(sku=value)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        
        if queryset.exists():
            raise serializers.ValidationError("Product with this SKU already exists.")
        
        return value

class ProductListSerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source='vendor.business_name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    primary_image = serializers.SerializerMethodField()
    is_in_stock = serializers.ReadOnlyField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'price', 'stock_quantity', 'vendor_name',
            'category_name', 'primary_image', 'is_in_stock', 'is_featured',
            'created_at'
        ]

    def get_primary_image(self, obj):
        primary_image = obj.images.filter(is_primary=True).first()
        if primary_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(primary_image.image.url)
            return primary_image.image.url
        return None

# from rest_framework import serializers
# from .models import Product, ProductImage, Category

# class CategorySerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Category
#         fields = '__all__'

# class ProductImageSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = ProductImage
#         fields = '__all__'

# class ProductSerializer(serializers.ModelSerializer):
#     images = ProductImageSerializer(many=True, read_only=True)
#     vendor_name = serializers.CharField(source='vendor.business_name', read_only=True)
#     category_name = serializers.CharField(source='category.name', read_only=True)
#     is_in_stock = serializers.ReadOnlyField()
#     is_low_stock = serializers.ReadOnlyField()

#     class Meta:
#         model = Product
#         fields = '__all__'
#         read_only_fields = ['vendor', 'created_at', 'updated_at']

# class ProductListSerializer(serializers.ModelSerializer):
#     vendor_name = serializers.CharField(source='vendor.business_name', read_only=True)
#     category_name = serializers.CharField(source='category.name', read_only=True)
#     primary_image = serializers.SerializerMethodField()
#     is_in_stock = serializers.ReadOnlyField()

#     class Meta:
#         model = Product
#         fields = ['id', 'name', 'price', 'stock_quantity', 'vendor_name', 
#                  'category_name', 'primary_image', 'is_in_stock', 'is_featured']

#     def get_primary_image(self, obj):
#         primary_image = obj.images.filter(is_primary=True).first()
#         if primary_image:
#             return self.context['request'].build_absolute_uri(primary_image.image.url)
#         return None