from functools import wraps
from django.core.cache import cache
import logging
from apps.core.cache_control import disable_cache, enable_cache
from apps.core.utils import invalidate_user_cache
from apps.core.cache_control import is_cache_disabled


logger = logging.getLogger(__name__)

def redis_cached(model_name: str, key_column: str = "id", ttl: int = None):
    """
    Simple Redis caching decorator.
    Caches function results based on model name + primary key.
    """

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if is_cache_disabled():
                return fn(*args, **kwargs)

            
            pk = kwargs.get(key_column)
            if pk is None and args:
                obj = args[0]
                pk = getattr(obj, "id", obj)  # works for both int and model obj

            if pk is None:  # can't cache without a primary key
                print("can't cause your instance and key column both have nothing")
                return fn(*args, **kwargs)

            cache_key = f"{model_name}:{pk}"

            cached = cache.get(cache_key)
            if cached is not None:
                return cached

            logger.info(f"Cache MISS → {cache_key}")
            data = fn(*args, **kwargs)

            # Cache only JSON-serializable values
            cache.set(cache_key, data, timeout=ttl)
            logger.info(f"Cache SET → {cache_key} (TTL={ttl})")

            return data

        return wrapper
    return decorator





def refresh_cache(invalidate_user=True, vendor=False):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            disable_cache()
            try:
                response = view_func(request, *args, **kwargs)
            finally:
                enable_cache()

            if hasattr(request, "user") and request.user.is_authenticated:
                if invalidate_user:
                    invalidate_user_cache(request.user.id)

                if vendor and hasattr(request.user, "vendor"):
                    v_id = request.user.vendor.id
                    cache.delete(f"subscription:{v_id}")
                    cache.delete(f"user_vendor_id:{request.user.id}")

            return response
        return wrapper
    return decorator
