from django.core.cache import cache
from apps.products.models import Product
from apps.core.sqlite_cache import SqliteCache



class ProductUpdatedSubscriber: 
    queue = "product"

    def __call__(self, event):
        print("▶ ProductUpdatedSubscriber called")

        from django.conf import settings
        print("📌 Writing to:", settings.SQLITE_CACHE_FILES["product"])

        SqliteCache.set("product", "product_id", event.product_id, event.vendor_id, event.data)
        print("✔ WRITE DONE")



class ProductDeletedSubscriber:
    queue = "product"

    def __call__(self, event):
        print("▶ ProductDeletedSubscriber called")

        key = f"vendor:{event.vendor_id}:products"
        counts = cache.get(key, {
            "total_products": 0,
            "total_active_products": 0,
            "total_inactive_products": 0
        })

        is_active = event.is_active

        counts["total_products"] -= 1
        if is_active:
            counts["total_active_products"] -= 1
        else:
            counts["total_inactive_products"] -= 1

        cache.set(key, counts, timeout=300)
        print("✔ Product cache updated after delete:", counts)
