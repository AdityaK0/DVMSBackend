from apps.products.models import Category
from django.conf import settings


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
    from apps.portfolio.models import Portfolio,PortfolioSyncPlan
    # Check if already exists
    portfolio, created = Portfolio.objects.get_or_create(
        vendor=vendor,
        defaults={
            "display_name": vendor.business_name,
            "business_name_slug": vendor.business_name_slug,
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
    print("Portfolio created:", created)  # <-- Debug
    
    if settings.ENVIRONMENT == "development":
        portfolio_url = f"http://{vendor.business_name_slug}.localhost:3000"
    else:
        # For production domain, path-based structure
        portfolio_url = f"{settings.FRONTEND_BASE_PORTFOLIO_PREVIEW}/{vendor.business_name_slug}"
    portfolio.portfolio_url = portfolio_url
    portfolio.save()
    
    PortfolioSyncPlan.objects.get_or_create(
        portfolio=portfolio,
        defaults={"allowed_syncs_per_day": 5}
    )
    
    return portfolio
