from django.core.cache import cache

def cache_safe_get(key, func, timeout=300):
    """
    Try to get from cache. If cache fails (server down), fallback to DB.
    """
    try:
        value = cache.get(key)
        if value is None:
            value = func()
            try:
                cache.set(key, value, timeout=timeout)
            except Exception:
                # cache server might be down, just ignore
                pass
        return value
    except Exception:
        # Cache server totally unavailable
        return func()
