from django.urls import path
from . import views

urlpatterns = [
    
    # ---------- Vendor management ----------
    path('manage/', views.vendor_portfolio_manage, name='manage-portfolio'),
    path('manage/collections/', views.portfolio_collections, name='manage-collections'),
    path('manage/collections/<int:id>/detail/', views.portfolio_collection_detail, name='manage-collections'),
    path('manage/puiblish_site/', views.trigger_sync, name='trigger-sync'),
    path('manage/sync_status/', views.sync_status, name='sync-status'),
    
]