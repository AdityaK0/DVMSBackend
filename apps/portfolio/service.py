from django.shortcuts import get_object_or_404
from rest_framework import status
from apps.portfolio.models import Portfolio, PortfolioCollection,PortfolioSyncPlan
from apps.portfolio.serializers import PortfolioCollectionSerializer
from apps.utils.upload_image import upload_collection_image
from django.conf import settings
from django.utils import timezone

from apps.vendors.models import Vendor
from apps.portfolio.models import (
    Portfolio, PortfolioCollection,
)
from apps.portfolio.serializers import (
     ProductListSerializer,
)
from apps.users.serializers import AddressSerializer


class PortfolioService:

    @staticmethod
    def get_public_vendor_portfolio(vendor_id: int):

        """Fetch vendor, portfolio details, analytics, products, testimonials etc."""
        # Fetch vendor with related user & addresses
        vendor = (
            Vendor.objects
            .select_related('user')
            .prefetch_related('user__addresses')
            .get(id=vendor_id, is_active=True)
        )
        portfolio = get_object_or_404(Portfolio, vendor=vendor, is_public=True)

        portfolio.last_viewed = timezone.now()   # last updated can be used here i think
        portfolio.save(update_fields=["view_count", "last_viewed"])

        total_collections = PortfolioCollection.objects.filter(
            portfolio=portfolio, is_active=True
        ).count()

        featured_products = portfolio.get_featured_products()[:8]  

        # Prepare response data
        return {
            "id": portfolio.id,
            "business_name": vendor.business_name,
            "display_name": portfolio.display_name,
            "tagline": portfolio.tagline,
            "slug": portfolio.slug,
            "business_name_slug": vendor.business_name_slug,
            "about_us": portfolio.about_us,
            "theme_color": portfolio.theme_color,
            "accent_color": portfolio.accent_color,
            "background_color": portfolio.background_color,
            "font_family": portfolio.font_family,
            "layout_style": portfolio.layout_style,
            "show_pricing": portfolio.show_pricing,
            "show_contact_form": portfolio.show_contact_form,
            "show_stock_status":portfolio.show_stock_status,
            "is_public": portfolio.is_public,
            "view_count": portfolio.view_count,
            "total_collections": total_collections,
            # "total_testimonials": total_testimonials,
            "featured_products": ProductListSerializer(
                portfolio.featured_products.all(), many=True
            ).data,
            "banner_image": portfolio.banner_image if portfolio.banner_image else None,
            "carousel_images": portfolio.carousel_images or [],
            "is_carousel": portfolio.is_carousel,
            "logo": portfolio.logo.url if portfolio.logo else None,
            "gallery_images": portfolio.gallery_images or [],
            "contact_email": vendor.business_email,
            "contact_phone": vendor.business_phone,
            "address": AddressSerializer(vendor.user.addresses.all(), many=True).data,
            "whatsapp_number": vendor.whatsapp_number or None,
            "social_links": {
                "facebook": portfolio.facebook_url,
                "instagram": portfolio.instagram_url,
                "twitter": portfolio.twitter_url,
                "linkedin": portfolio.linkedin_url,
                "youtube": portfolio.youtube_url,
            },
            "created_at": portfolio.created_at,
            "updated_at": portfolio.updated_at,
        }
        
    @staticmethod   
    def get_vendor_collections(vendor):
        """
        Fetch all collections for a vendor's portfolio.
        """
        collections = PortfolioCollection.objects.filter(
            portfolio__vendor=vendor
        ).order_by('order', 'name')
        
        serializer = PortfolioCollectionSerializer(collections, many=True)
        return serializer.data    
    
    @staticmethod
    def create_vendor_sync_plan(vendor):
        plan, created = PortfolioSyncPlan.objects.get_or_create(
            vendor=vendor,
            defaults={
                "allowed_syncs_per_day": settings.DEFAULT_SYNC_COUNT,
                "used_syncs_today": 0,
                "extra_syncs_available": 0,
            },
        )

        if created:
            plan.last_sync_at = None
            plan.save()

        plan.refresh_from_db()
        return plan

          

        





def create_vendor_collection(vendor, data, files=None):
    """
    Create a new portfolio collection for a vendor.
    Handles image upload if provided.
    """
    portfolio = get_object_or_404(Portfolio, vendor=vendor)

    serializer = PortfolioCollectionSerializer(data=data)
    if serializer.is_valid():
        collection = serializer.save(portfolio=portfolio)

        # Handle optional image upload
        image_file = None
        if files:
            image_file = files.get('image')
        if image_file:
            upload_collection_image(collection, image_file)

        response_serializer = PortfolioCollectionSerializer(collection)
        return {
            "data": response_serializer.data,
            "status": status.HTTP_201_CREATED
        }
    else:
        return {
            "data": serializer.errors,
            "status": status.HTTP_400_BAD_REQUEST
        }
