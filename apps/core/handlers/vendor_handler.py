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

        
        
        # Delete the data related to the vendors so that vendor wont get invalid data 
        cache.delete(f"user:{user_id}")
        cache.delete(f"portfolio:{vendor_id}")
        cache.delete(f"auth_user:{user_id}")
        # thought to revalidate data (after cache delete add again by calling their service method ) will do if needed 
        
        
        print("vendor data and portfolio data cleaned",datetime.now())
        
        




