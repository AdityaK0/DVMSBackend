# apps/portfolio/serializers.py

from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    Portfolio, PortfolioSection, PortfolioCollection, 
    PortfolioTestimonial, PortfolioContactInquiry, PortfolioTheme
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


class PortfolioSectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PortfolioSection
        fields = [
            'id', 'title', 'content', 'section_type', 
            'order', 'is_active'
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

        # ✅ Restrict max 5 collections per portfolio
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
        

class PortfolioTestimonialSerializer(serializers.ModelSerializer):
    class Meta:
        model = PortfolioTestimonial
        fields = [
            'id', 'customer_name', 'customer_image', 'customer_designation',
            'company', 'testimonial_text', 'rating', 'is_featured',
            'created_at'
        ]


class PortfolioContactInquirySerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    
    class Meta:
        model = PortfolioContactInquiry
        fields = [
            'id', 'name', 'email', 'phone', 'subject', 'message',
            'product', 'product_name', 'status', 'created_at'
        ]
        read_only_fields = ['status']


class PortfolioThemeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PortfolioTheme
        fields = [
            'id', 'name', 'description', 'preview_image',
            'theme_config', 'is_premium'
        ]

from apps.vendors.serializers import VendorSerializer

# class PortfolioSerializer(serializers.ModelSerializer):
#     """Full portfolio serializer for management"""
#     vendor = VendorBasicSerializer(read_only=True)
#     sections = PortfolioSectionSerializer(many=True, read_only=True)
#     # collections = PortfolioCollectionSerializer(many=True, read_only=True) no need cause we have diff api for this
#     testimonials = PortfolioTestimonialSerializer(many=True, read_only=True)
#     # featured_products = PortfolioProductSerializer(source='get_featured_products', many=True, read_only=True)
#     featured_products = ProductListSerializer(many=True, read_only=True)
    
    
#     carousel_images_input = serializers.ListField(
#         child=serializers.CharField(),
#         write_only=True,
#         required=False
#     )

#     # write-only field to update featured products
#     featured_product_ids = serializers.ListField(
#         child=serializers.IntegerField(),
#         write_only=True,
#         required=False
#     )

    
#     # Stats
#     # total_products = serializers.SerializerMethodField()
#     # total_collections = serializers.SerializerMethodField()
#     total_testimonials = serializers.SerializerMethodField()
#     banner_image = serializers.SerializerMethodField()
    
#     class Meta:
#         model = Portfolio
#         fields = [
#             'id', 'display_name', 'tagline', 'slug', 'about_us', 'our_story','last_viewed',
#             'mission', 'vision', 'logo', 'banner_image', 'gallery_images',
#             'theme_color', 'accent_color', 'background_color', 'text_color',
#             'font_family', 'layout_style','facebook_url', 'instagram_url',
#             'twitter_url', 'linkedin_url', 'youtube_url', 'website_url',
#             'show_pricing', 'show_stock_status', 'show_contact_form',
#             'show_social_links', 'show_testimonials', 'show_gallery',
#             'is_public', 'custom_domain', 'custom_css', 'meta_title',
#             'meta_description', 'meta_keywords', 'view_count',
#             'created_at', 'updated_at', 'vendor', 'sections','portfolio_url',
#             'testimonials', 'featured_products', 'featured_product_ids','is_carousel', 'total_testimonials',  'carousel_images',          # ✅ read response
#             # 'total_products', Not needed for portfolio summary

#         ]
#         read_only_fields = ['slug', 'view_count', 'vendor','carousel_images']
#         write_only_fields = ['featured_product_ids','carousel_images_input']
        
        
#     def get_banner_image(self,obj):
#         if obj.banner_image:
#             return obj.banner_image.url
#         return None
    
#     # def get_total_products(self, obj):
#     #     return obj.get_all_products().count()
    
        
#     def update(self, instance, validated_data):
#         featured_product_ids = validated_data.pop('featured_product_ids', None)
#         portfolio = super().update(instance, validated_data)

#         if featured_product_ids is not None:
#             products = Product.objects.filter(
#                 id__in=featured_product_ids,
#                 vendor=portfolio.vendor
#             )
#             portfolio.featured_products.set(products)

#         portfolio.refresh_from_db()
#         return portfolio

    
#     def get_total_collections(self, obj):
#         return obj.collections.filter(is_active=True).count()
    
#     def get_total_testimonials(self, obj):
#         return obj.testimonials.filter(is_approved=True).count()

class PortfolioSerializer(serializers.ModelSerializer):
    """Full portfolio serializer for management"""
    vendor = VendorBasicSerializer(read_only=True)
    sections = PortfolioSectionSerializer(many=True, read_only=True)
    testimonials = PortfolioTestimonialSerializer(many=True, read_only=True)
    featured_products = ProductListSerializer(many=True, read_only=True)
    
    # Write-only field to update featured products
    featured_product_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )

    # Stats
    total_testimonials = serializers.SerializerMethodField()
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
            'created_at', 'updated_at', 'vendor', 'sections', 'portfolio_url',
            'testimonials', 'featured_products', 'featured_product_ids', 
            'is_carousel', 'total_testimonials', 'carousel_images',
        ]
        read_only_fields = ['slug', 'view_count', 'vendor', 'carousel_images']
        extra_kwargs = {
            'featured_product_ids': {'write_only': True}
        }
        
    def get_banner_image(self, obj):
        if obj.banner_image:
            return obj.banner_image.url
        return None
    
    def get_total_testimonials(self, obj):
        return obj.testimonials.filter(is_approved=True).count()
    
    
    def validate_featured_product_ids(self, value):
        if len(value) > 8:
            raise serializers.ValidationError("Maximum 8 featured products are allowed.")
        return value


    def update(self, instance, validated_data):
        # Handle featured products
        featured_product_ids = validated_data.pop('featured_product_ids', None)
        
        # Update other fields
        portfolio = super().update(instance, validated_data)

        # Update featured products if provided
        if featured_product_ids is not None:
            products = Product.objects.filter(
                id__in=featured_product_ids,
                vendor=portfolio.vendor
            )
            portfolio.featured_products.set(products)

        return portfolio
class PublicPortfolioSerializer(serializers.ModelSerializer):
    """Public portfolio view - optimized for frontend"""
    vendor = VendorBasicSerializer(read_only=True)
    featured_products = PortfolioProductSerializer(source='get_featured_products', many=True, read_only=True)
    featured_collections = serializers.SerializerMethodField()
    featured_testimonials = serializers.SerializerMethodField()
    
    # Analytics
    stats = serializers.SerializerMethodField()
    
    class Meta:
        model = Portfolio
        fields = [
            'id', 'display_name', 'tagline', 'slug', 'about_us', 'our_story',
            'logo', 'banner_image', 'gallery_images', 'theme_color',
            'accent_color', 'background_color', 'text_color', 'font_family',
            'layout_style', 'contact_email', 'contact_phone', 'whatsapp_number',
            'address', 'facebook_url', 'instagram_url', 'twitter_url',
            'linkedin_url', 'youtube_url', 'website_url', 'show_pricing',
            'show_stock_status', 'show_contact_form', 'show_social_links',
            'show_testimonials', 'show_gallery', 'meta_title', 'meta_description',
            'vendor', 'featured_products', 'featured_collections',
            'featured_testimonials', 'stats', 'created_at'
        ]
    
    def get_featured_collections(self, obj):
        collections = obj.collections.filter(is_featured=True, is_active=True)[:6]
        return PortfolioCollectionSerializer(collections, many=True).data
    
    def get_featured_testimonials(self, obj):
        testimonials = obj.testimonials.filter(is_featured=True, is_approved=True)[:6]
        return PortfolioTestimonialSerializer(testimonials, many=True).data
    
    def get_stats(self, obj):
        from django.utils import timezone
        from datetime import timedelta
        
        # Calculate some basic stats
        total_products = obj.get_all_products().count()
        years_in_business = (timezone.now().date() - obj.vendor.created_at.date()).days // 365
        
        return {
            'total_products': total_products,
            'years_in_business': max(years_in_business, 1),
            'happy_customers': obj.testimonials.filter(is_approved=True).count() * 10,  # Mock multiplier
            'portfolio_views': obj.view_count,
            'featured_products': obj.get_featured_products().count(),
            'collections': obj.collections.filter(is_active=True).count(),
        }


class PortfolioCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new portfolio"""
    class Meta:
        model = Portfolio
        fields = [
            'display_name', 'tagline', 'about_us', 'theme_color',
            'layout_style', 'contact_email', 'contact_phone',
            'is_public'
        ]
    
    def create(self, validated_data):
        # Get vendor from request user
        request = self.context.get('request')
        if request and hasattr(request.user, 'vendor'):
            validated_data['vendor'] = request.user.vendor
        return super().create(validated_data)


class PortfolioUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating portfolio"""
    class Meta:
        model = Portfolio
        fields = [
            'display_name', 'tagline', 'about_us', 'our_story',
            'mission', 'vision', 'logo', 'banner_image', 'gallery_images',
            'theme_color', 'accent_color', 'background_color', 'text_color',
            'font_family', 'layout_style', 'contact_email', 'contact_phone',
            'whatsapp_number', 'address', 'facebook_url', 'instagram_url',
            'twitter_url', 'linkedin_url', 'youtube_url', 'website_url',
            'show_pricing', 'show_stock_status', 'show_contact_form',
            'show_social_links', 'show_testimonials', 'show_gallery',
            'is_public', 'custom_css', 'meta_title', 'meta_description',
            'meta_keywords'
        ]


# Analytics Serializer
class PortfolioAnalyticsSerializer(serializers.Serializer):
    """Custom serializer for portfolio analytics data"""
    overview = serializers.DictField()
    monthly_stats = serializers.ListField()
    popular_products = serializers.ListField()
    traffic_sources = serializers.DictField()
    recent_inquiries = serializers.ListField()