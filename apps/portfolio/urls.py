from django.urls import path
from . import views
# from apps.products.views import VendorCatalogView

urlpatterns = [

    # Public portfolio views
    path('portfolio/<str:business_name>/', views.public_vendor_portfolio, name='portfolio'),
    path('portfolio/<str:business_name>/products/', views.portfolio_product_search, name='portfolio-products'),
    path('portfolio/<str:business_name>/contact/', views.portfolio_contact, name='portfolio-contact'),
    
    # Portfolio management (for vendors)
    path('manage/portfolio/', views.VendorPortfolioUpdateView.as_view(), name='manage-portfolio'),
    path('manage/portfolio/collections/', views.PortfolioCollectionListCreateView.as_view(), name='manage-collections'),
    path('manage/portfolio/testimonials/', views.TestimonialListCreateView.as_view(), name='manage-testimonials'),
    path('manage/portfolio/analytics/', views.portfolio_analytics, name='portfolio-analytics'),
]

# # Custom middleware for subdomain/custom domain handling (optional)
# # This would allow URLs like: vendor1.yourdomain.com or custom-domain.com
# class CustomDomainMiddleware:
#     def __init__(self, get_response):
#         self.get_response = get_response

#     def __call__(self, request):
#         host = request.get_host().lower()
        
#         # Check if it's a custom domain
#         if host not in ['yourdomain.com', 'www.yourdomain.com', 'localhost:8000']:
#             try:
#                 # Look for vendor with this custom domain
#                 vendor = Vendor.objects.get(
#                     portfolio__custom_domain=host,
#                     portfolio__is_portfolio_public=True,
#                     is_active=True
#                 )
#                 # Set custom attribute for view
#                 request.custom_domain_vendor = vendor
#             except Vendor.DoesNotExist:
#                 pass
        
#         response = self.get_response(request)
#         return response