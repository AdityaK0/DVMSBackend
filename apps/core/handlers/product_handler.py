from django.core.cache import cache
from apps.products.models import Product

class ProductUpdatedSubscriber:
    queue = "product"

    def __call__(self, event):
        print("▶ ProductUpdatedSubscriber called")

        product = Product.objects.get(pk=event.product_id)
        is_active = product.is_active
        old_active = event._old_is_active

        key = f"vendor:{event.vendor_id}:products"
        counts = cache.get(key, {
            "total_products": 0,
            "total_active_products": 0,
            "total_inactive_products": 0
        })

        action = event.action

        if action == "CREATED":
            counts["total_products"] += 1
            if is_active:
                counts["total_active_products"] += 1
            else:
                counts["total_inactive_products"] += 1

        elif action == "UPDATED":
            if old_active is False and is_active is True:
                counts["total_active_products"] += 1
                counts["total_inactive_products"] -= 1
            elif old_active is True and is_active is False:
                counts["total_active_products"] -= 1
                counts["total_inactive_products"] += 1

        cache.set(key, counts, timeout=300)
        print("✔ Product cache updated:", counts)




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
