# core/handlers/product_handler.py

import logging
from django.core.cache import cache

logger = logging.getLogger(__name__)


class ProductCreatedSubscriber:
    """
    Handles product.created events.
    
    Responsibilities:
    - Warm Redis cache with new product data
    - Update vendor product count cache
    """

    def __call__(self, event):
        logger.info(f"▶ ProductCreatedSubscriber called for product {event.id}")

        try:
            product_id = event.id
            product_data = event.data
            vendor_id = event.metadata.get("vendor_id")

            # 1. Warm product cache
            product_cache_key = f"product:{product_id}"
            cache.set(product_cache_key, product_data, timeout=60 * 60 * 5)
            logger.info(f"✅ Product cache warmed: {product_cache_key}")

            # 2. Invalidate vendor product list cache (will be rebuilt on next request)
            if vendor_id:
                vendor_products_key = f"vendor:{vendor_id}:products"
                cache.delete(vendor_products_key)
                logger.info(f"🗑️  Invalidated vendor products cache: {vendor_products_key}")

        except Exception as e:
            logger.error(f"❌ ProductCreatedSubscriber failed: {e}", exc_info=True)


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
            product_cache_key = f"product:{product_id}"
            cache.delete(product_cache_key)  # Delete first to ensure consistency
            # cache.set(product_cache_key, product_data, timeout=60 * 60 * 5)
            # logger.info(f"✅ Product cache updated: {product_cache_key}")

            # 2. Invalidate vendor product list cache
            if vendor_id:
                vendor_products_key = f"vendor:{vendor_id}:products"
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
            product_cache_key = f"product:{product_id}"
            cache.delete(product_cache_key)
            logger.info(f"🗑️  Deleted product cache: {product_cache_key}")

            # 2. Invalidate vendor product list cache
            if vendor_id:
                vendor_products_key = f"vendor:{vendor_id}:products"
                cache.delete(vendor_products_key)
                logger.info(f"🗑️  Invalidated vendor products cache: {vendor_products_key}")

        except Exception as e:
            logger.error(f"❌ ProductDeletedSubscriber failed: {e}", exc_info=True)
