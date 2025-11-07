from django.conf import settings

def update_portfolio_url(portfolio,business_name_slug):
    if settings.ENVIRONMENT == "development":
            portfolio_url = f"http://{business_name_slug}.localhost:{settings.FRONTEND_PORT}"
    else:
        portfolio_url = f"{settings.FRONTEND_BASE_URL}/{business_name_slug}"
        
    portfolio.portfolio_url = portfolio_url
    portfolio.save()