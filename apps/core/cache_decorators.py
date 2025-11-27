# apps/core/cache_decorators.py
from functools import wraps
from apps.core.sqlite_cache import SqliteCache
from django.conf import settings

def sqlite_cached(model_name: str, key_column: str = None, ttl: int = None):
    """
    Decorator for service getter functions. The decorated function must accept a primary key param.
    If cached JSON present, decorator returns that dict directly (skips function).
    Otherwise runs function, stores JSON result in cache, and returns the result.
    - model_name: "product" -> uses cache_product table
    - key_column: column used as key in sqlite (e.g. product_id)
    - ttl: time-to-live in seconds (0 => no TTL)
    """

    key_column = key_column or f"{model_name}_id"
    ttl = ttl if ttl is not None else getattr(settings, "SQLITE_CACHE_DEFAULT_TTL", 0)

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            # try to extract pk from positional or keyword args
            pk = kwargs.get("pk")
            if pk is None:
                # guess positional (common pattern: fn(pk, ...))
                if len(args) >= 1:
                    pk = args[0]
            if pk is None:
                # cannot determine key — fallback to actual function
                return fn(*args, **kwargs)

            cached = SqliteCache.get(model_name, key_column, pk, ttl_seconds=ttl)
            if cached is not None:
                # Return cached dict immediately
                return cached

            # otherwise call function, get model or dict
            result = fn(*args, **kwargs)
            # result should be either model instance or dict/serializable
            try:
                if isinstance(result, dict):
                    data_obj = result
                else:
                    # assume DRF serializer is needed; try to serialize using serializer from service
                    # we require service to return a serializable dict if it intends cache writes
                    # If it's a Django model, try to convert using a .to_dict() or raise.
                    # To keep safe, allow service to return dict for cacheable calls
                    # If model instance, we expect caller to handle serialization.
                    # So skip caching.
                    return result

                vendor_id = data_obj.get("vendor_id") or data_obj.get("vendor", {}).get("id") or 0
                SqliteCache.set(model_name, key_column, pk, vendor_id, data_obj)
            except Exception:
                # fail silently; return original result
                return result

            return result
        return wrapper
    return decorator
