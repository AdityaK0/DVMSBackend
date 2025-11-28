from functools import wraps
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)

def redis_cached(model_name: str, key_column: str = "id", ttl: int = None):
    """
    Simple Redis caching decorator.
    Caches function results based on model name + primary key.
    """

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            
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
