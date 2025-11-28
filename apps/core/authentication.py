from rest_framework_simplejwt.authentication import JWTAuthentication
from django.contrib.auth import get_user_model
from django.core.cache import cache
from apps.vendors.models import Vendor

User = get_user_model()

class CachedJWTAuthentication(JWTAuthentication):

    def get_user(self, validated_token):
        user_id = validated_token.get("user_id")

        if not user_id:
            return None

        cache_key = f"auth_user:{user_id}"

        # Try Redis first
        user = cache.get(cache_key)
        if user:
            return user

        # Fallback to DB (only once per TTL)
        try:
            user = User.objects.only(
                "id", "email", "username", "role", "is_active", "is_staff"
            ).get(id=user_id)
        except User.DoesNotExist:
            return None

        cache.set(cache_key, user, timeout=60 * 60)  # 1 hour cache 
        
        
        
        vendor_cache_key = f"user_vendor_id:{user_id}"
        vendor_id = cache.get(vendor_cache_key)

        if vendor_id is None:
            vendor_id = Vendor.objects.filter(
                user_id=user_id
            ).values_list("id", flat=True).first()

            cache.set(vendor_cache_key, vendor_id, timeout=60 * 60)

        
        return user


from django.core.cache import cache
from apps.vendors.models import Vendor

def get_request_vendor(request):
    """
    Assumes request.user is authenticated.
    """
    user_id = request.user.id
    vendor_cache_key = f"user_vendor_id:{user_id}"
    
    vendor_id = cache.get(vendor_cache_key)

    if vendor_id is None:
        vendor_id = Vendor.objects.filter(
            user_id=user_id
        ).values_list("id", flat=True).first()

        cache.set(vendor_cache_key, vendor_id, timeout=60 * 60)
    
    return vendor_id    
