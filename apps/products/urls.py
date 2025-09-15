# products/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Public endpoints
    path('', views.product_list, name='product-list'),
    path('products/<int:pk>/', views.product_detail, name='product-detail'),
    path('categories/', views.category_list, name='category-list'),
    path('vendor/<int:vendor_id>/products/', views.vendor_catalog, name='vendor-catalog'),
    
    # Vendor endpoints (authenticated)
    # path('vendor/products/', views.vendor_products, name='vendor-products'),
    # path('vendor/products/create/', views.create_product, name='create-product'),
    # path('vendor/products/<int:pk>/update/', views.update_product, name='update-product'),
    # path('vendor/products/<int:pk>/delete/', views.delete_product, name='delete-product'),
    
    path('vendor/my-products/', views.vendor_products, name='vendor-products'),
    path('vendor/my-products/create/', views.create_product, name='create-product'),
    path('vendor/my-products/<int:pk>/update/', views.update_product, name='update-product'),
    path('vendor/my-products/<int:pk>/delete/', views.delete_product, name='delete-product'),
]

# from django.urls import path
# from .views import (
#     ProductListView, ProductDetailView, ProductCreateView,
#     ProductUpdateView, ProductDeleteView, CategoryListView,
#     VendorCatalogView
# )

# urlpatterns = [
#     path('', ProductListView.as_view(), name='product-list'),
#     path('create/', ProductCreateView.as_view(), name='product-create'),
#     path('<int:pk>/', ProductDetailView.as_view(), name='product-detail'),
#     path('<int:pk>/update/', ProductUpdateView.as_view(), name='product-update'),
#     path('<int:pk>/delete/', ProductDeleteView.as_view(), name='product-delete'),
#     path('categories/', CategoryListView.as_view(), name='category-list'),
# ]