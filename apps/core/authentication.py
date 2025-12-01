from rest_framework_simplejwt.authentication import JWTAuthentication
from django.contrib.auth import get_user_model
from django.core.cache import cache
from apps.vendors.models import Vendor
from apps.core.cache_control import is_cache_disabled
from django.core.cache import cache
from django.conf import settings

User = get_user_model()

class CachedJWTAuthentication(JWTAuthentication):
    """
    JWT Authentication with Redis caching.
    
    IMPORTANT: Caches only primitives (dict), NOT ORM instances.
    Respects thread-local cache bypass via is_cache_disabled().
    """

    def get_user(self, validated_token):
        user_id = validated_token.get("user_id")
        if not settings.BIG_MACHINE:
            print("CACHE KEYS IN WORKER AUTH: **** \n"*10, list(cache._cache.keys()))

        if not user_id:
            return None

        # ✅ Respect cache bypass (e.g., during @refresh_cache)
        if is_cache_disabled():
            return self._fetch_user_from_db(user_id)

        cache_key = f"auth:user:{user_id}"  # ✅ Standardized key naming

        # Try Redis first
        cached_payload = cache.get(cache_key)
        if cached_payload:
            # ✅ Reconstruct User from cached primitives
            return self._user_from_payload(cached_payload)

        # Fallback to DB (only once per TTL)
        return self._fetch_user_from_db(user_id)

    def _fetch_user_from_db(self, user_id):
        """Fetch user from DB and cache primitives."""
        try:
            user = User.objects.only(
                "id", "email", "username", "role", "is_active", "is_staff"
            ).get(id=user_id)
        except User.DoesNotExist:
            return None

        # ✅ Cache only primitives (JSON-serializable dict)
        auth_payload = {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "role": user.role,
            "is_active": user.is_active,
            "is_staff": user.is_staff,
        }
        
        cache_key = f"auth:user:{user_id}"
        cache.set(cache_key, auth_payload, timeout=60 * 60)  # 1 hour cache
        
        # ✅ Cache vendor_id mapping (primitives only)
        self._cache_vendor_id(user_id)
        
        return user

    def _cache_vendor_id(self, user_id):
        """Cache user→vendor_id mapping."""
        vendor_cache_key = f"user:vendor_id:{user_id}"  # ✅ Standardized key
        
        if is_cache_disabled():
            return
        
        vendor_id = cache.get(vendor_cache_key)
        if vendor_id is None:
            vendor_id = Vendor.objects.filter(
                user_id=user_id
            ).values_list("id", flat=True).first()

            cache.set(vendor_cache_key, vendor_id or 0, timeout=60 * 60)

    def _user_from_payload(self, payload):
        """Reconstruct User instance from cached payload."""
        try:
            # Fetch fresh user from DB using cached ID
            # (DRF expects a real User instance for permissions)
            user = User.objects.only(
                "id", "email", "username", "role", "is_active", "is_staff"
            ).get(id=payload["id"])
            return user
        except User.DoesNotExist:
            return None


from django.core.cache import cache
from apps.vendors.models import Vendor

def get_request_vendor(request):
    """
    Get vendor_id for authenticated user.
    Assumes request.user is authenticated.
    
    Returns vendor_id (int) or None if no vendor exists.
    """
    from apps.core.cache_control import is_cache_disabled
    
    user_id = request.user.id
    vendor_cache_key = f"user:vendor_id:{user_id}"  # ✅ Standardized key naming
    
    # Respect cache bypass
    if is_cache_disabled():
        return Vendor.objects.filter(
            user_id=user_id
        ).values_list("id", flat=True).first()
    
    vendor_id = cache.get(vendor_cache_key)

    if vendor_id is None:
        vendor_id = Vendor.objects.filter(
            user_id=user_id
        ).values_list("id", flat=True).first()

        cache.set(vendor_cache_key, vendor_id or 0, timeout=60 * 60)
    
    return vendor_id if vendor_id != 0 else None    
