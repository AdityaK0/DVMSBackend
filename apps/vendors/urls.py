from django.urls import path

from . import views
# from apps.products.views import VendorCatalogView

urlpatterns = [
    # path('', VendorListView.as_view(), name='vendor-list'),
    path('create/', views.create_vendor, name='vendor-create'),  
    path('profile/',views.vendor_profile, name='vendor-profile'),
    path('profile/<int:pk>/', views.vendor_profile, name='vendor-detail'),
    # path('<int:vendor_id>/catalog/', VendorCatalogView.as_view(), name='vendor-catalog'),
    
    path("events/create/", views.create_event),
    path("events/<int:event_id>/posters/create/", views.create_poster),

    # Vendor
    path("events/", views.list_events),
    path("events/<int:event_id>/posters/", views.list_event_posters),
    path("posters/<int:poster_id>/", views.get_single_poster),
]   