# core/dispatcher.py
from django.core.cache import cache

from apps.vendors.models import Vendor
from .events import (
    ProductCacheUpdateEvent,
    CustomerCacheUpdateEvent,
    ActivityCacheUpdateEvent,
)



def handle_event(event):
    """
    Dispatch cache update based on event type.
    If cache server is down, just skip caching and rely on DB fallback.
    """
    vendor = Vendor.objects.get(id=event.vendor_id)
    
    try:
        from apps.dashboard.service import (
            get_product_stats,
            get_customer_stats,
            get_activity_data,
        )
    except ImportError:
        # dashboard might not be loaded yet
        return


    if isinstance(event, ProductCacheUpdateEvent):
        
        try:
            cache.set(f"vendor:{vendor.id}:products", get_product_stats(vendor), timeout=300)
        except Exception:
            pass  # cache server might be down, DB fallback still works

    elif isinstance(event, CustomerCacheUpdateEvent):
        try:
            cache.set(f"vendor:{vendor.id}:customers", get_customer_stats(vendor), timeout=300)
        except Exception:
            pass

    elif isinstance(event, ActivityCacheUpdateEvent):
        try:
            cache.set(f"vendor:{vendor.id}:activity", get_activity_data(vendor), timeout=300)
        except Exception:
            pass

