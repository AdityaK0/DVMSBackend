from rest_framework import serializers
from .models import Product, ProductImage, Category


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'

class ProductImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    class Meta:
        model = ProductImage
        fields = ['id', 'image','image_url','alt_text', 'is_primary']
        
    # def get_image_url(self, obj):
    #     request = self.context.get('request')
    #     if request:
    #         return request.build_absolute_uri(obj.image.url)
    #     return obj.image.url   
    
    
    def get_image_url(self, obj):
        return obj.github_image_url  if obj.github_image_url else obj.image.url
        # """
        # Returns the best available image URL in order of reliability:
        # 1. github_image_url (permanent, safe)
        # 2. image.url (Cloudinary)
        # 3. image_url (manual uploads)
        # 4. Placeholder fallback
        # """
        # if getattr(obj, 'github_image_url', None):
        #     return obj.github_image_url

        # if obj.image and hasattr(obj.image, 'url') and obj.image.url:
        #     # request = self.context.get('request')
        #     # return request.build_absolute_uri(obj.image.url) if request else obj.image.url
        #     return obj.image.url

        # if getattr(obj, 'image_url', None):
        #     return obj.image_url

        # return "https://via.placeholder.com/300x300?text=No+Image"      

# class ProductSerializer(serializers.ModelSerializer):
#     images = ProductImageSerializer(many=True, read_only=True)
#     vendor_name = serializers.CharField(source='vendor.business_name', read_only=True)
#     category_name = serializers.CharField(source='category.name', read_only=True)
#     is_in_stock = serializers.ReadOnlyField()
#     is_low_stock = serializers.ReadOnlyField()
    
#     class Meta:
#         model = Product
#         fields = [
#             'id', 'name', 'description', 'category', 'price', 'cost_price',
#             'stock_quantity', 'min_stock_level', 'sku', 'weight', 'dimensions',
#             'is_active', 'is_featured', 'meta_title', 'meta_description',
#             'created_at', 'updated_at', 'images', 'vendor_name', 'category_name',
#             'is_in_stock', 'is_low_stock'
#         ]
#         read_only_fields = ['vendor', 'created_at', 'updated_at']
    
#     def validate_sku(self, value):
#         """Ensure SKU is unique, excluding current instance during updates"""
#         queryset = Product.objects.filter(sku=value)
#         if self.instance:
#             queryset = queryset.exclude(pk=self.instance.pk)
        
#         if queryset.exists():
#             raise serializers.ValidationError("Product with this SKU already exists.")
        
#         return value
    
#     # def get_images(self, obj):
#     #     images_qs = obj.images.all().order_by('-is_primary')
#     #     request = self.context.get('request')
#     #     images_list = []
#     #     for img in images_qs:
#     #         if request:
#     #             images_list.append(request.build_absolute_uri(img.image.url))
#     #         else:
#     #             images_list.append(img.image.url)
        
#     #     return [
#     #         img.github_image_url if img.github_image_url else img.image.url
#     #         for img in images_qs
#     #     ]

#         # return images_list
    

# serializers.py
from rest_framework import serializers
from .models import Product

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
        required=False
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
        read_only_fields = ['vendor', 'created_at', 'updated_at']

    def validate_sku(self, value):
        request = self.context.get("request")
        vendor = request.user.vendor

        qs = Product.objects.filter(sku=value, vendor=vendor)

        # Exclude the current product when updating
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise serializers.ValidationError("Product with this SKU already exists for your store.")

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
    
# class ProductListSerializer(serializers.ModelSerializer):
#     vendor_name = serializers.CharField(source='vendor.business_name', read_only=True)
#     images = serializers.SerializerMethodField()
#     is_in_stock = serializers.ReadOnlyField()

#     class Meta:
#         model = Product
#         fields = [
#             'id', 'name', 'price', 'stock_quantity', 'vendor_name','description','meta_title','meta_description',
#             'images', 'is_in_stock', 'is_featured', 'created_at', "is_active"
#         ]

#     def get_images(self, obj):
#         """
#         Return up to 4 images, primary first.
#         Uses prefetched 'images' queryset to avoid extra queries.
#         """
#         images_qs = getattr(obj, 'images_prefetched', None)
#         if images_qs is None:
#             # fallback if prefetch didn't happen
#             images_qs = obj.images.all()
#         # sort in Python to avoid DB query
#         sorted_images = sorted(images_qs, key=lambda i: not i.is_primary)[:4]

#         # request = self.context.get('request')
#         # return [
#         #     request.build_absolute_uri(img.image.url) if request else img.image.url
#         #     for img in sorted_images
#         # ]
        
#         return [
#             img.github_image_url if img.github_image_url else img.image.url
#             for img in sorted_images
#         ]

