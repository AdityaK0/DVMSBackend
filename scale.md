Product Listing and Public Portfolio Architecture
Overview

This architecture provides a unified and scalable approach for handling vendor products across two different contexts:

Vendor API (Authenticated) – Used by vendors to manage and view their own products.

Public Portfolio API (Unauthenticated) – Used to publicly display vendor products on their portfolio.

Both use the same core logic through a shared service layer but differ in data access sources and visibility rules.

Objectives

Centralize core logic for product retrieval inside a shared services.py.

Allow customization of API responses based on vendor portfolio settings.

Avoid direct database hits for public portfolio APIs.

Cache or index public data for fast and scalable access.

Provide a fallback to the service layer if the cache/index fails.

Limit how frequently vendors can trigger reindexing.

Service Layer (Common Logic)
# apps/products/services.py
from apps.products.models import Product

def get_vendor_products(vendor, include_private=False):
    """
    Common function to fetch vendor products.
    Can be reused by both vendor and public portfolio APIs.
    """
    queryset = Product.objects.filter(vendor=vendor, is_active=True)

    if not include_private:
        queryset = queryset.filter(is_public=True)

    return queryset

Vendor Products API (Authenticated)
# apps/products/api.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from apps.products.services import get_vendor_products

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def vendor_products_list(request):
    vendor = request.user.vendor
    products = get_vendor_products(vendor, include_private=True)

    # Customize as needed (e.g., show timestamps, vendor details, etc.)
    data = [
        {
            "id": p.id,
            "name": p.name,
            "price": p.price,
            "created_at": p.created_at,
            "updated_at": p.updated_at,
            "vendor": p.vendor.name,
        }
        for p in products
    ]
    return Response(data)

Public Portfolio API (Unauthenticated)
# apps/portfolio/api.py
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from apps.vendors.models import Vendor
from apps.portfolio.utils import fetch_portfolio_index_data
from apps.products.services import get_vendor_products

@api_view(["GET"])
def public_portfolio_products(request, business_name):
    vendor = get_object_or_404(Vendor, business_name=business_name)

    # Try fetching from cache/index first
    data = fetch_portfolio_index_data(vendor.id)

    # If cache/index fails, fall back to DB using service function
    if not data:
        products = get_vendor_products(vendor, include_private=False)
        data = [
            {
                "id": p.id,
                "name": p.name,
                "price": p.price,
                "image": p.image.url if p.image else None,
            }
            for p in products
        ]

    return Response(data)

Portfolio Data Caching and Reindexing

Triggered when the vendor clicks “Sync Data” or “Update Portfolio” on the frontend.

# apps/portfolio/tasks.py
from apps.products.services import get_vendor_products
from django.core.cache import cache
import json

def reindex_portfolio(vendor):
    products = get_vendor_products(vendor, include_private=False)
    serialized = [
        {
            "id": p.id,
            "name": p.name,
            "price": p.price,
            "image": p.image.url if p.image else None,
        }
        for p in products
    ]
    cache.set(f"portfolio:{vendor.id}:products", json.dumps(serialized), timeout=None)

Fetching Cached Data with Fallback Awareness
# apps/portfolio/utils.py
from django.core.cache import cache
import json

def fetch_portfolio_index_data(vendor_id):
    try:
        data = cache.get(f"portfolio:{vendor_id}:products")
        if data:
            return json.loads(data)
    except Exception:
        # Cache might be down or corrupted
        pass
    return None


If this function returns None, the API automatically falls back to get_vendor_products() as shown earlier.

Reindexing Rate Limiter
# apps/portfolio/tasks.py
MAX_REINDEX_PER_DAY = 5

def can_reindex(vendor):
    key = f"portfolio:{vendor.id}:reindex_count"
    count = cache.get(key, 0)

    if count >= MAX_REINDEX_PER_DAY:
        return False
    cache.set(key, count + 1, timeout=24*60*60)
    return True


Used in the reindexing process:

def reindex_portfolio(vendor):
    if not can_reindex(vendor):
        raise Exception("Reindex limit reached for today.")
    ...

Advantages
Concern	Solution
Database Load	Public portfolio reads from Redis/Elasticsearch
Data Consistency	Reindexing keeps cached data up to date
Fault Tolerance	Falls back to DB when cache fails
Flexibility	Can customize fields per vendor’s portfolio settings
Security	Public access stays read-only
Scalability	Async reindexing and request throttling
Reusability	Shared service layer for all product fetching logic
Future Enhancements

Integrate Celery for asynchronous reindexing jobs.

Use Redis Streams or Elasticsearch for faster reads and search capability.

Add API throttling for public endpoints to avoid abuse.

Create vendor-specific config models to store preferences such as:

show/hide price

show created/updated timestamps

show vendor details

Add monitoring dashboards to track reindex activity and cache hit rates.