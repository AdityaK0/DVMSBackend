from functools import wraps
from django.core.cache import cache
import logging
import json
from apps.core.cache_control import disable_cache, enable_cache
from apps.core.utils import invalidate_user_cache
from apps.core.cache_control import is_cache_disabled


logger = logging.getLogger(__name__)





# apps/core/cache_decorators.py (or wherever)
from functools import wraps
from django.core.cache import cache
import json
from apps.core.cache_control import is_cache_disabled
import logging

logger = logging.getLogger(__name__)


def redis_cached(model_name: str, key_column: str = "id", ttl: int = None, serialize_fn=None):
    """
    Redis caching decorator with serialization support.
    
    IMPORTANT: Only caches JSON-serializable values (primitives, dicts, lists).
    Never caches ORM model instances.
    
    Args:
        model_name: Namespace for cache key (e.g., "user", "vendor", "product")
        key_column: Kwarg name containing the primary key (default: "id")
        ttl: Cache TTL in seconds (default: None = use Redis default)
        serialize_fn: Optional function to serialize result before caching
                     Example: lambda obj: serializer(obj).data
    
    Example:
        @redis_cached("user", "user_id", ttl=300, serialize_fn=lambda u: UserSerializer(u).data)
        def get_user(user_id):
            return User.objects.get(id=user_id)
    """

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            # ✅ Respect cache bypass (e.g., during @refresh_cache)
            if is_cache_disabled():
                logger.debug(f"Cache DISABLED → executing {fn.__name__}")
                return fn(*args, **kwargs)

            # Extract primary key from kwargs or args
            pk = kwargs.get(key_column)
            if pk is None and args:
                obj = args[0]
                pk = getattr(obj, "id", obj)  # works for both int and model obj

            if pk is None:  # can't cache without a primary key
                logger.warning(f"Cache SKIP → {fn.__name__}: no PK found in {key_column}")
                return fn(*args, **kwargs)

            cache_key = f"{model_name}:{pk}"

            # Try cache first
            cached = cache.get(cache_key)
            if cached is not None:
                logger.info(f"Cache HIT → {cache_key}")
                return cached

            logger.info(f"Cache MISS → {cache_key}")
            data = fn(*args, **kwargs)

            # ✅ Serialize if function provided
            to_cache = serialize_fn(data) if serialize_fn else data

            # ✅ Validate JSON-serializability (prevent caching ORM instances)
            try:
                json.dumps(to_cache)  # quick serializability check
                cache.set(cache_key, to_cache, timeout=ttl)
                logger.info(f"Cache SET → {cache_key} (TTL={ttl}s)")
            except (TypeError, ValueError) as e:
                logger.error(
                    f"Cache SKIP → {cache_key}: Result not JSON-serializable. "
                    f"Use serialize_fn parameter. Error: {e}"
                )
                # Return original data (not serialized) if caching fails
                return data

            return to_cache

        return wrapper
    return decorator





def refresh_cache(invalidate_user=True, invalidate_vendor=False):
    """
    Decorator that disables cache reads and invalidates cache after successful DB commit.
    
    CRITICAL: Uses transaction.on_commit to ensure cache is only invalidated
    after successful database transaction commit.
    
    Args:
        invalidate_user: If True, invalidate user-related caches (default: True)
        invalidate_vendor: If True, invalidate vendor-related caches (default: False)
    
    Usage:
        @refresh_cache(invalidate_user=True, invalidate_vendor=True)
        def create_vendor(request):
            # ... vendor creation logic
            return Response(...)
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            from django.db import transaction
            from apps.core.utils import invalidate_all_user_related
            
            # ✅ Disable cache reads for this request
            disable_cache()
            
            try:
                response = view_func(request, *args, **kwargs)
            finally:
                # ✅ Always re-enable cache, even on exception
                enable_cache()

            # ✅ Only invalidate on successful responses (2xx, 3xx)
            status_code = getattr(response, "status_code", 500)
            if 200 <= status_code < 400:
                if hasattr(request, "user") and request.user.is_authenticated:
                    user_id = request.user.id
                    vendor_id = None
                    
                    # Get vendor_id if needed
                    if invalidate_vendor and hasattr(request.user, "vendor"):
                        vendor_id = getattr(request.user.vendor, "id", None)
                    
                    # ✅ CRITICAL: Use transaction.on_commit for invalidation
                    # This ensures cache is only cleared AFTER DB commit succeeds
                    def _invalidate_caches():
                        if invalidate_user:
                            invalidate_all_user_related(
                                user_id=user_id,
                                vendor_id=vendor_id,
                                use_transaction=False  # Already in on_commit
                            )
                        elif invalidate_vendor and vendor_id:
                            from apps.core.utils import invalidate_vendor_cache
                            invalidate_vendor_cache(vendor_id, use_transaction=False)
                        
                        logger.info(
                            f"Cache invalidated for user={user_id}, vendor={vendor_id} "
                            f"after successful commit (status={status_code})"
                        )
                    
                    transaction.on_commit(_invalidate_caches)

            return response
        return wrapper
    return decorator

