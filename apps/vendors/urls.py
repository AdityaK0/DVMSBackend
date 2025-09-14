from django.urls import path
from .views import (
    VendorListView, VendorDetailView, vendor_profile,create_vendor
)
from apps.products.views import VendorCatalogView

urlpatterns = [
    path('', VendorListView.as_view(), name='vendor-list'),
    path('create/', create_vendor, name='vendor-create'),  
    path('profile/',vendor_profile, name='vendor-profile'),
    path('profile/<int:pk>/', vendor_profile, name='vendor-detail'),
    path('<int:vendor_id>/catalog/', VendorCatalogView.as_view(), name='vendor-catalog'),
]   