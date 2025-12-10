from apps.products.models import Category
from django.conf import settings
from django.utils.text import slugify

BUSINESS_TYPE_CATEGORIES = {
    'clothing': ["Shirts","T-Shirts", "Jeans", "Jackets"],
    'electronics': ["Mobile Phones", "Laptops", "Cameras", "Accessories"],
    'furniture': ["Sofas", "Beds", "Tables", "Chairs"],
    'other': []
}
    

def create_default_categories_for_vendor(vendor):
    default_list = BUSINESS_TYPE_CATEGORIES.get(vendor.business_type, [])
    for cat_name in default_list:
        Category.objects.get_or_create(
            name=cat_name,
            vendor=vendor,
            is_default=True
            # defaults={'is_default': True}
        )


def create_default_portfolio_for_vendor(vendor):
    """
    Create default portfolio for a vendor using their permanent handle.
    
     Uses vendor.handle (permanent, never changes)
     Falls back to business_name+vendor_id only if handle is missing (shouldn't happen)
    
    Args:
        vendor: Vendor instance
    
    Returns:
        Portfolio instance
    """
    from apps.portfolio.models import Portfolio, PortfolioSyncPlan
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Check if already exists
    portfolio, created = Portfolio.objects.get_or_create(
        vendor=vendor,
        defaults={
            "display_name": vendor.business_name,
            "handle": vendor.handle,
            "tagline": "",
            "about_us": "",
            "our_story": "",
            "mission": "",
            "vision": "",
            "font_family": "Inter",
            "layout_style": "modern",
            "gallery_images": [],
            "carousel_images": [],
        }
    )
    
    #  ALWAYS use vendor's permanent handle for portfolio URL
    # This ensures stable URLs even if business name changes
    if not vendor.handle:
        logger.warning(
            f"Vendor {vendor.id} has no handle! This shouldn't happen. "
            f"Falling back to business_name+vendor_id."
        )
        url_handle = f"{slugify(vendor.business_name)}-v{vendor.id}"
    else:
        url_handle = vendor.handle
    
    # Generate portfolio URL based on environment
    if settings.ENVIRONMENT == "development":
        portfolio_url = f"http://{url_handle}.localhost:3000"
    else:
        # Production: use handle-based subdomain
        portfolio_url = f"https://www.{url_handle}.site.fordgeindia.online"
    
    # Update portfolio URL
    portfolio.portfolio_url = portfolio_url
    portfolio.save()
    
    # Create sync plan
    PortfolioSyncPlan.objects.get_or_create(
        portfolio=portfolio,
        defaults={"allowed_syncs_per_day": 5}
    )
    
    return portfolio
