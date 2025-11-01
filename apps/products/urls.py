# products/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Public endpoints
    path('', views.product_list, name='product-list'),
    path('vendor/products/<int:pk>/', views.product_detail, name='product-detail'),
    path('categories/', views.category_list, name='category-list'),
    path('vendor/<int:vendor_id>/products/', views.vendor_catalog, name='vendor-catalog'),
    
    # Vendor endpoints (authenticated)
    # path('vendor/products/', views.vendor_products, name='vendor-products'),
    # path('vendor/products/create/', views.create_product, name='create-product'),
    # path('vendor/products/<int:pk>/update/', views.update_product, name='update-product'),
    # path('vendor/products/<int:pk>/delete/', views.delete_product, name='delete-product'),
    
    path('vendor/my-products/', views.vendor_products, name='vendor-products'),
    path('vendor/my-categories/', views.vendor_categories, name='vendor-products'),
    path('vendor/my-categories/<int:pk>/delete/', views.delete_category, name='vendor-products'),
    
    
    path('vendor/my-products/create/', views.create_product, name='create-product'),
    path('vendor/my-products/<int:pk>/update/', views.update_product, name='update-product'),
    path('vendor/my-products/<int:pk>/activate/', views.activate_product, name='update-product'),

    path('vendor/my-products/<int:pk>/delete/', views.delete_product, name='delete-product'),
    # path("vendor/search/", views.search_products, name="search_products"),
    path("vendor/filter/", views.filter_products, name="filter_products"),
]

