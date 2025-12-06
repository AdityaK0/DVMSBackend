from django.conf import settings

def update_portfolio_url(portfolio, vendor_handle=None):
    """
    Update portfolio URL using vendor's permanent handle.
    
    Args:
        portfolio: Portfolio instance
        vendor_handle: Optional vendor handle (if None, fetches from portfolio.vendor.handle)
    """
    # Use vendor's permanent handle for URL generation
    if vendor_handle is None:
        vendor_handle = portfolio.vendor.handle
    
    # Fallback to business_name_slug if handle is not set (backward compatibility)
    if not vendor_handle:
        vendor_handle = portfolio.vendor.business_name_slug
    
    if not vendor_handle:
        # Last resort: generate from business name
        from django.utils.text import slugify
        vendor_handle = slugify(portfolio.vendor.business_name)
    
    if settings.ENVIRONMENT == "development":
        portfolio_url = f"http://{vendor_handle}.localhost:{settings.FRONTEND_PORTFOLIO_PORT}"
    else:
        portfolio_url = f"https://{vendor_handle}.{settings.FRONTEND_BASE_PORTFOLIO_PREVIEW}/"
        
    portfolio.portfolio_url = portfolio_url
    portfolio.save()
    
    
 
import uuid
from datetime import timedelta
from django.utils.timezone import now

def rotate_secret(vendor=None):
    if not vendor:
        secret = uuid.uuid4().hex[:8]
        return secret
    vendor.telegram_secret = uuid.uuid4().hex[:8]   # short secret like: A92F3B1C
    vendor.telegram_secret_expires_at = now() + timedelta(days=7)
    vendor.save()   