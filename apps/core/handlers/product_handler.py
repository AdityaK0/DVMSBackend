# core/handlers/product_handler.py

import logging
from django.core.cache import cache
from apps.vendors.models import VendorStats
logger = logging.getLogger(__name__)

class ProductCreatedSubscriber:

    def __call__(self, event):
        vendor_id = event.metadata["vendor_id"]
        is_active = event.data.get("is_active", True)

        stats = VendorStats.objects.select_for_update().get(vendor_id=vendor_id)

        stats.total_products += 1
        if is_active:
            stats.active_products += 1
        else:
            stats.inactive_products += 1

        stats.save(update_fields=[
            "total_products",
            "active_products",
            "inactive_products"
        ])


class ProductUpdatedSubscriber:
    """
    Handles product.updated events.
    
    Responsibilities:
    - Update Redis cache with latest product data
    - Invalidate related caches
    """

    def __call__(self, event):
        logger.info(f"▶ ProductUpdatedSubscriber called for product {event.id}")

        try:
            product_id = event.id
            product_data = event.data
            vendor_id = event.metadata.get("vendor_id")

            # 1. Update product cache
            product_cache_key = f"product:context:{product_id}"  # ✅ Standardized key
            cache.delete(product_cache_key)  
        
            # 2. Invalidate vendor product list cache
            if vendor_id:
                vendor_products_key = f"vendor:context:{vendor_id}:products"  # ✅ Standardized key
                cache.delete(vendor_products_key)
                logger.info(f"🗑️  Invalidated vendor products cache: {vendor_products_key}")

        except Exception as e:
            logger.error(f"❌ ProductUpdatedSubscriber failed: {e}", exc_info=True)


class ProductDeletedSubscriber:
    """
    Handles product.deleted events.
    
    Responsibilities:
    - Remove product from Redis cache
    - Update vendor product count cache
    """

    def __call__(self, event):
        logger.info(f"▶ ProductDeletedSubscriber called for product {event.id}")

        try:
            product_id = event.id
            vendor_id = event.metadata.get("vendor_id")

            # 1. Remove product cache
            product_cache_key = f"product:context:{product_id}"  # ✅ Standardized key
            cache.delete(product_cache_key)
            logger.info(f"🗑️  Deleted product cache: {product_cache_key}")

            # 2. Invalidate vendor product list cache
            if vendor_id:
                vendor_products_key = f"vendor:context:{vendor_id}:products"  # ✅ Standardized key
                cache.delete(vendor_products_key)
                logger.info(f"🗑️  Invalidated vendor products cache: {vendor_products_key}")

        except Exception as e:
            logger.error(f"❌ ProductDeletedSubscriber failed: {e}", exc_info=True)
