from django.core.cache import cache
from apps.products.models import Product
from apps.dashboard.models import Customer
from .events import (
    ProductCacheUpdateEvent,
    CustomerCacheUpdateEvent,
    ActivityCacheUpdateEvent,
)

def handle_event_sync(event):
    """Process cache updates synchronously."""

    # ---------- PRODUCT ----------
    if isinstance(event, ProductCacheUpdateEvent):
        try:
            key = f"vendor:{event.vendor_id}:products"
            counts = cache.get(key, {
                "total_products": 0,
                "total_active_products": 0,
                "total_inactive_products": 0
            })

            action = event.action
            instance = event.instance

            if action == "CREATED":
                counts["total_products"] += 1
                if instance.is_active:
                    counts["total_active_products"] += 1
                else:
                    counts["total_inactive_products"] += 1

            elif action == "UPDATED":
                if instance.is_active:
                    counts["total_active_products"] += 1
                    counts["total_inactive_products"] -= 1
                else:
                    counts["total_active_products"] -= 1
                    counts["total_inactive_products"] += 1

            elif action == "DELETED":
                counts["total_products"] -= 1
                if instance.is_active:
                    counts["total_active_products"] -= 1
                else:
                    counts["total_inactive_products"] -= 1

            cache.set(key, counts, timeout=300)

        except Exception as e:
            print("Product cache update failed:", e)

    # ---------- CUSTOMER ----------
    elif isinstance(event, CustomerCacheUpdateEvent):
        try:
            key = f"vendor:{event.vendor_id}:customers"
            counts = cache.get(key, {
                "total_customers": 0,
                "total_active_customers": 0,
                "total_inactive_customers": 0
            })

            action = event.action
            instance = event.instance

            if action == "CREATED":
                counts["total_customers"] += 1
                if instance.is_active:
                    counts["total_active_customers"] += 1
                else:
                    counts["total_inactive_customers"] += 1

            elif action == "UPDATED":
                if instance.is_active:
                    counts["total_active_customers"] += 1
                    counts["total_inactive_customers"] -= 1
                else:
                    counts["total_active_customers"] -= 1
                    counts["total_inactive_customers"] += 1

            elif action == "DELETED":
                counts["total_customers"] -= 1
                if instance.is_active:
                    counts["total_active_customers"] -= 1
                else:
                    counts["total_inactive_customers"] -= 1

            cache.set(key, counts, timeout=300)

        except Exception as e:
            print("Customer cache update failed:", e)

    # ---------- ACTIVITY (placeholder) ----------
    elif isinstance(event, ActivityCacheUpdateEvent):
        pass


# had added the async dispatcher functions and all but currently on sync flow 
# when user will come a lot then will shift to that

