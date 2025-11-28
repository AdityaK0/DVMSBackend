from functools import wraps
from django.core.cache import cache
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def redis_cached(model_name: str, key_column: str = None, ttl: int = None):
    """
    Redis-based decorator for service getter functions.

    Works like your sqlite_cached:
    - Checks Redis cache before calling function
    - On miss, calls function, stores result in Redis
    - TTL supported (default: settings.REDIS_CACHE_DEFAULT_TTL)
    - Global across all instances

    Example usage:
        @redis_cached("vendor", "vendor_id", ttl=5*60*60)
        def get_vendor_profile(pk): ...
    """

    key_column = key_column or f"{model_name}_id"
    ttl = ttl if ttl is not None else getattr(settings, "REDIS_CACHE_DEFAULT_TTL", 60 * 60 * 5)

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):

            # Get primary key
            pk = kwargs.get("pk")
            if pk is None and len(args) >= 1:
                pk = args[0]

            if pk is None:
                return fn(*args, **kwargs)

            cache_key = f"{model_name}:{pk}"

            cached = cache.get(cache_key)
            if cached:
                logger.info(f"🔥 Redis Cache HIT: {cache_key}")
                return cached

            logger.info(f"❌ Redis Cache MISS: {cache_key}")

            result = fn(*args, **kwargs)

            try:
                # Only cache dict responses
                if not isinstance(result, dict):
                    return result

                cache.set(cache_key, result, timeout=ttl)
                logger.info(f"✅ Redis Cache SET: {cache_key} (TTL={ttl}s)")

            except Exception as e:
                logger.warning(f"⚠ Redis cache set failed: {e}")

            return result

        return wrapper
    return decorator
