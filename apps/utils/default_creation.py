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
    
    # Logic to generate default description
    description = ""
    if vendor.business_description:
        description = vendor.business_description
    else:
        # Generate dynamically
        city = "India"
        # Try to get city from user addresses
        address = vendor.user.addresses.filter(is_default=True).first()
        if not address:
            address = vendor.user.addresses.first()
        if address and address.city:
            city = address.city
            
        started_str = f", established in {vendor.business_started_year}," if vendor.business_started_year else ""
        
        role = vendor.business_role or "Business"
        if role == 'custom_printing': role = "Custom Printing Provider"
        elif role == 'online_only': role = "Online Seller"
        role = role.replace('_', ' ').title()
        
        categories = vendor.business_categories
        cat_str = ""
        if isinstance(categories, list) and categories:
            cat_str = f" The business specializes in {', '.join(categories)}, offering quality products and reliable service to customers."
        else:
            cat_str = " The business offers quality products and reliable service to customers."
            
        hours_str = ""
        if vendor.business_hours: 
             open_time = vendor.business_hours.get('open', '09:00')
             close_time = vendor.business_hours.get('close', '22:00')
             # formatting time is tricky without knowing input format strictly, assuming HH:MM
             hours_str = f" {vendor.business_name} is open from {open_time} to {close_time}, serving local customers and nearby areas."

        description = f"{vendor.business_name}{started_str} is a trusted {role} based in {city}.{cat_str}{hours_str}"
        
    # ✅ Auto-fill vendor business_description if empty
    if not vendor.business_description:
        vendor.business_description = description
        vendor.save(update_fields=["business_description"])
        
    # SEO Meta Generation
    category = "Retail"
    if vendor.business_categories and len(vendor.business_categories) > 0:
        category = vendor.business_categories[0]
        
    years_str = f" Serving customers since {vendor.business_started_year}." if vendor.business_started_year else ""
    meta_desc = f"{vendor.business_name} – {category} retailer in {city}.{years_str}"

    # Check if already exists
    portfolio, created = Portfolio.objects.get_or_create(
        vendor=vendor,
        defaults={
            "display_name": vendor.business_name,
            "handle": vendor.handle,
            "tagline": "",
            "about_us": description,
            "our_story": "",
            "mission": "",
            "vision": "",
            "font_family": "Inter",
            "layout_style": "modern",
            "gallery_images": [],
            "carousel_images": [],
            "meta_description": meta_desc,
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
        portfolio_url = f"http://{url_handle}.localhost:5174"
    else:
        # Production: use handle-based subdomain
        portfolio_url = f"https://{url_handle}.fordgeindia.online"
    
    # Update portfolio URL
    portfolio.portfolio_url = portfolio_url
    portfolio.save()
    
    # Create sync plan
    PortfolioSyncPlan.objects.get_or_create(
        portfolio=portfolio,
        defaults={"allowed_syncs_per_day": 5}
    )
    
    return portfolio
