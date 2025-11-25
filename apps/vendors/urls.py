from django.urls import path

from . import views
# from apps.products.views import VendorCatalogView

urlpatterns = [
    # path('', VendorListView.as_view(), name='vendor-list'),
    path('create/', views.create_vendor, name='vendor-create'),  
    path('profile/',views.vendor_profile, name='vendor-profile'),
    path('profile/<int:pk>/', views.vendor_profile, name='vendor-detail'),
    # path('<int:vendor_id>/catalog/', VendorCatalogView.as_view(), name='vendor-catalog'),
    
    # Admin - Event Management
    path("events/create/", views.create_event),
    path("events/<int:event_id>/update/", views.update_event),
    path("events/<int:event_id>/delete/", views.delete_event),
    
    # Admin - Poster Management
    path("events/<int:event_id>/posters/create/", views.create_poster),
    path("posters/<int:poster_id>/update/", views.update_poster),
    path("posters/<int:poster_id>/delete/", views.delete_poster),

    # Vendor - View Events & Posters
    path("events/", views.list_events),
    path("events/<int:event_id>/posters/", views.list_event_posters),
    path("posters/<int:poster_id>/", views.get_single_poster),
]   