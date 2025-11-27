# apps/portfolio/serializers.py

from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    Portfolio, PortfolioCollection, 
    PortfolioTheme
)
from apps.vendors.models import Vendor
from apps.products.models import Product, ProductImage
from apps.products.serializers import ProductListSerializer

# from cloudinary.utils import cloudinary_url
User = get_user_model()


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'image_url', 'alt_text', 'is_primary']


class PortfolioProductSerializer(serializers.ModelSerializer):
    """Serializer for products in portfolio context"""
    images = ProductImageSerializer(many=True, read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'description', 'price', 'stock_quantity',
            'is_in_stock', 'is_low_stock', 'is_featured', 'sku',
            'images', 'category_name', 'created_at'
        ]


class VendorBasicSerializer(serializers.ModelSerializer):
    """Basic vendor info for portfolio"""
    class Meta:
        model = Vendor
        fields = [
            'id', 'business_name', 'business_description',"business_name_slug",
            'business_email', 'business_phone', 'website',
            'logo', 'business_type', 'is_verified'
        ]
    
    

class PortfolioCollectionSerializer(serializers.ModelSerializer):
    products = ProductListSerializer(many=True, read_only=True)  # ✅ reuse your existing product serializer
    product_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )
    product_count = serializers.SerializerMethodField()
    cover_image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = PortfolioCollection
        fields = [
            'id', 'name', 'description', 'cover_image', 'slug',
            'is_featured', 'is_active', 'order', 
            'products', 'cover_image_url', 
            'product_ids', 'product_count', 'created_at'
        ]
        read_only_fields = ['slug']
        
    # ----- Derived Fields -----
    def get_product_count(self, obj):
        return obj.products.count()

    def get_cover_image_url(self, obj):
        if not obj.cover_image:
            return None
        request = self.context.get('request')
        return request.build_absolute_uri(obj.cover_image.url) if request else obj.cover_image.url
    
    # ----- Create / Update -----
    def create(self, validated_data):
        portfolio = validated_data.get("portfolio")

        #  Restrict max 5 collections per portfolio
        if portfolio.collections.count() >= 5:
            raise serializers.ValidationError({
                "message": "A portfolio can have at most 5 collections."
            })
        product_ids = validated_data.pop('product_ids', [])
        collection = PortfolioCollection.objects.create(**validated_data)

        if product_ids:
            # restrict to vendor products
            products = Product.objects.filter(
                id__in=product_ids,
                vendor=collection.portfolio.vendor
            )
            collection.products.set(products)
        
        return collection

    def update(self, instance, validated_data):
        product_ids = validated_data.pop('product_ids', None)
        collection = super().update(instance, validated_data)

        if product_ids is not None:
            products = Product.objects.filter(
                id__in=product_ids,
                vendor=collection.portfolio.vendor
            )
            collection.products.set(products)
        
        return collection
        

class PortfolioThemeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PortfolioTheme
        fields = [
            'id', 'name', 'description', 'preview_image',
            'theme_config', 'is_premium'
        ]

class PortfolioSerializer(serializers.ModelSerializer):
    """Full portfolio serializer for management"""
    vendor = VendorBasicSerializer(read_only=True)
    featured_products = ProductListSerializer(many=True, read_only=True)
    
    featured_product_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )

    banner_image = serializers.SerializerMethodField()
    
    class Meta:
        model = Portfolio
        fields = [
            'id', 'display_name', 'tagline', 'slug', 'about_us', 'our_story', 'last_viewed',
            'mission', 'vision', 'logo', 'banner_image', 'gallery_images',
            'theme_color', 'accent_color', 'background_color', 'text_color',
            'font_family', 'layout_style', 'facebook_url', 'instagram_url',
            'twitter_url', 'linkedin_url', 'youtube_url', 'website_url',
            'show_pricing', 'show_stock_status', 'show_contact_form',
            'show_social_links', 'show_testimonials', 'show_gallery',
            'is_public', 'custom_domain', 'custom_css', 'meta_title',
            'meta_description', 'meta_keywords', 'view_count',
            'created_at', 'updated_at', 'vendor', 'portfolio_url', 'featured_products', 'featured_product_ids', 'is_featured',
            'is_carousel', 'carousel_images',
        ]
        read_only_fields = ['slug', 'view_count', 'vendor']

        extra_kwargs = {
            'featured_product_ids': {'write_only': True}
        }
        
    def get_banner_image(self, obj):
        return obj.banner_image or None
    
    
    def validate_featured_product_ids(self, value):
        if len(value) > 8:
            raise serializers.ValidationError("Maximum 8 featured products are allowed.")
        return value


    def update(self, instance, validated_data):
        featured_product_ids = validated_data.pop('featured_product_ids', None)

        portfolio = super().update(instance, validated_data)

        if featured_product_ids is not None:
            # Set M2M
            products = Product.objects.filter(
                id__in=featured_product_ids,
                vendor=portfolio.vendor
            )
            portfolio.featured_products.set(products)

            # ---- NEW: Sync product.is_featured with M2M ----

            # 1 Mark selected as featured
            Product.objects.filter(
                id__in=featured_product_ids,
                vendor=portfolio.vendor
            ).update(is_featured=True)

            # 2 Mark all other vendor products as NOT featured
            Product.objects.filter(
                vendor=portfolio.vendor
            ).exclude(id__in=featured_product_ids).update(is_featured=False)

        return portfolio
