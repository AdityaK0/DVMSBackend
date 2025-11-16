"""
Product recommendation service.
Recommends products based on priority:
1. Featured products
2. Most viewed (if analytics available)
3. Highest stock
4. Random active products
"""
from apps.products.models import Product
from apps.vendors.models import Vendor
from django.db.models import Q, F
import random


def recommend_products(vendor, limit=10):
    """
    Recommend products for a vendor's event.
    
    Priority:
    1. Featured products
    2. Most viewed (if analytics available - placeholder for now)
    3. Highest stock
    4. Random active products
    
    Args:
        vendor: Vendor instance
        limit: Maximum number of products to return
    
    Returns:
        QuerySet of Product objects
    """
    # Base queryset: active products for this vendor
    base_qs = Product.objects.filter(
        vendor=vendor,
        is_active=True,
        is_archived=False
    )
    
    # Priority 1: Featured products
    featured = base_qs.filter(is_featured=True).order_by('-created_at')
    
    # Priority 2: Most viewed (placeholder - can be enhanced with analytics)
    # For now, we'll use products with higher stock as a proxy
    
    # Priority 3: Highest stock
    high_stock = base_qs.filter(
        ~Q(id__in=featured.values_list('id', flat=True))
    ).order_by('-stock_quantity', '-created_at')
    
    # Priority 4: Random active products
    remaining = base_qs.filter(
        ~Q(id__in=featured.values_list('id', flat=True)),
        ~Q(id__in=high_stock.values_list('id', flat=True))
    )
    
    # Combine results
    recommended = list(featured) + list(high_stock)
    
    # If we still need more, add random products
    if len(recommended) < limit:
        remaining_list = list(remaining)
        random.shuffle(remaining_list)
        recommended.extend(remaining_list[:limit - len(recommended)])
    
    # Return up to limit
    return recommended[:limit]


def get_product_recommendation_data(products):
    """
    Convert Product queryset/list to recommendation data format.
    
    Args:
        products: List or QuerySet of Product objects
    
    Returns:
        List of dicts with product data
    """
    result = []
    for product in products:
        result.append({
            'id': product.id,
            'name': product.name,
            'price': str(product.price),
            'image': product.primary_image or (product.image_urls[0] if product.image_urls else None),
            'is_in_stock': product.is_in_stock,
            'stock_quantity': product.stock_quantity,
            'is_featured': product.is_featured,
        })
    return result

