# core/handlers/vendor_handler.py

import logging
from django.core.cache import cache

logger = logging.getLogger(__name__)


class VendorUpdatedSubscriber:
    
    def __call__(self, event):
        logger.info(f"▶ VendorUpdatedSubscriber called for vendor {event.id}")
        
        user_id = event.metadata.get("user_id")
        vendor_id = event.id

        logger.info(f"📋 Invalidating caches - user_id: {user_id}, vendor_id: {vendor_id}")

        # Delete all related caches
        cache.delete(f"user:{user_id}")
        logger.info(f"🗑️  Deleted cache: user:{user_id}")
        
        cache.delete(f"portfolio:{vendor_id}")
        logger.info(f"🗑️  Deleted cache: portfolio:{vendor_id}")
        
        cache.delete(f"vendor:{vendor_id}")
        logger.info(f"🗑️  Deleted cache: vendor:{vendor_id}")
        
        print(f"✅ User + vendor + portfolio cache invalidated for user:{user_id}, vendor:{vendor_id}")




