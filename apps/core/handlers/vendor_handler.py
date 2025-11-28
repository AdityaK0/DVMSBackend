# core/handlers/vendor_handler.py

import logging
from django.core.cache import cache

logger = logging.getLogger(__name__)


class VendorUpdatedSubscriber:
    """
    Handles vendor.updated events.
    
    Responsibilities:
    - Update Redis cache with latest vendor data
    - Invalidate related caches (portfolio, products, etc.)
    """
    queue = "default"

    def __call__(self, event):
        logger.info(f"▶ VendorUpdatedSubscriber called for vendor {event.id}")

        try:
            vendor_id = event.id
            vendor_data = event.data

            # 1. Update vendor cache
            vendor_cache_key = f"vendor:{vendor_id}"
            cache.delete(vendor_cache_key)  # Delete first to ensure consistency
            cache.set(vendor_cache_key, vendor_data, timeout=60 * 60 * 5)
            logger.info(f"✅ Vendor cache updated: {vendor_cache_key}")

            # 2. Optionally invalidate related caches
            # Example: If vendor name changed, invalidate portfolio cache
            portfolio_cache_key = f"portfolio:{vendor_id}"
            cache.delete(portfolio_cache_key)
            logger.info(f"🗑️  Invalidated portfolio cache: {portfolio_cache_key}")

        except Exception as e:
            logger.error(f"❌ VendorUpdatedSubscriber failed: {e}", exc_info=True)
