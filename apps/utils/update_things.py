from django.conf import settings

def update_portfolio_url(portfolio,business_name_slug):
    if settings.ENVIRONMENT == "development":
            portfolio_url = f"http://{business_name_slug}.localhost:{settings.FRONTEND_PORT}"
    else:
        portfolio_url = f"{settings.FRONTEND_BASE_URL}/{business_name_slug}"
        
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