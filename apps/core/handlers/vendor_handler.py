# core/handlers/vendor_handler.py

import logging
from django.core.cache import cache
from datetime import datetime

logger = logging.getLogger(__name__)


class VendorUpdatedSubscriber:
    
    def __call__(self, event):
        logger.info(f"▶ VendorUpdatedSubscriber called for vendor {event.id}")
        
        user_id = event.metadata.get("user_id")
        vendor_id = event.id

        # ✅ Invalidate standardized cache keys
        cache.delete(f"user:context:{user_id}")        # User context (includes vendor data)
        cache.delete(f"vendor:context:{vendor_id}")    # Vendor profile
        cache.delete(f"portfolio:context:{vendor_id}") # Portfolio data
        
        logger.info(f"✅ Cache invalidated for user={user_id}, vendor={vendor_id}")
        print("vendor data and portfolio data cleaned", datetime.now())
        
        




