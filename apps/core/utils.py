from django.core.cache import cache
from django.db import transaction
import logging

logger = logging.getLogger(__name__)


def invalidate_user_cache(user_id, use_transaction=True):
    """
    Invalidate all user-related cache keys.
    
    Args:
        user_id: User ID to invalidate
        use_transaction: If True, wrap in transaction.on_commit (default)
    """
    def _invalidate():
        keys = [
            f"user:context:{user_id}",      # /me API response
            f"auth:user:{user_id}",         # JWT auth payload
            f"user:vendor_id:{user_id}",    # vendor mapping
            # Legacy keys (for backward compatibility during migration)
            f"user:{user_id}",
            f"auth_user:{user_id}",
            f"user_vendor_id:{user_id}",
        ]
        
        for key in keys:
            cache.delete(key)
            logger.debug(f"Cache invalidated: {key}")
    
    if use_transaction:
        transaction.on_commit(_invalidate)
    else:
        _invalidate()


def invalidate_vendor_cache(vendor_id, use_transaction=True):
    """
    Invalidate all vendor-related cache keys.
    
    Args:
        vendor_id: Vendor ID to invalidate
        use_transaction: If True, wrap in transaction.on_commit (default)
    """
    def _invalidate():
        keys = [
            f"vendor:profile:{vendor_id}",      # vendor profile
            f"portfolio:vendor:{vendor_id}",    # portfolio data
            f"subscription:vendor:{vendor_id}", # subscription status
        ]
        
        for key in keys:
            cache.delete(key)
            logger.debug(f"Cache invalidated: {key}")
    
    if use_transaction:
        transaction.on_commit(_invalidate)
    else:
        _invalidate()


def invalidate_subscription_cache(vendor_id=None, user_id=None, use_transaction=True):
    """
    Invalidate subscription-related cache keys.
    
    Args:
        vendor_id: Vendor ID to invalidate (preferred)
        user_id: User ID to invalidate (fallback)
        use_transaction: If True, wrap in transaction.on_commit (default)
    """
    def _invalidate():
        keys = []
        
        if vendor_id:
            keys.append(f"subscription:vendor:{vendor_id}")
        
        if user_id:
            keys.extend([
                f"user:context:{user_id}",
                f"auth:user:{user_id}",
                # Legacy keys
                f"subscription:{user_id}",
                f"user:{user_id}",
            ])
        
        for key in keys:
            cache.delete(key)
            logger.debug(f"Cache invalidated: {key}")
    
    if use_transaction:
        transaction.on_commit(_invalidate)
    else:
        _invalidate()


def invalidate_all_user_related(user_id, vendor_id=None, use_transaction=True):
    """
    Comprehensive invalidation for all user-related caches.
    Use after major user/vendor changes (e.g., vendor creation, subscription update).
    
    Args:
        user_id: User ID
        vendor_id: Optional vendor ID
        use_transaction: If True, wrap in transaction.on_commit (default)
    """
    invalidate_user_cache(user_id, use_transaction=use_transaction)
    
    if vendor_id:
        invalidate_vendor_cache(vendor_id, use_transaction=use_transaction)
        invalidate_subscription_cache(vendor_id=vendor_id, use_transaction=use_transaction)