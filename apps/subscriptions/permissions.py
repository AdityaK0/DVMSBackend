# marketplace/apps/subscriptions/permissions.py
from rest_framework.permissions import BasePermission
from django.utils import timezone

class IsSubscribed(BasePermission):
    message = "Your subscription is not active. Please subscribe to continue."

    def has_permission(self, request, view):
        vendor = getattr(request.user, "vendor", None)
        if not vendor:
            return False
        sub = getattr(vendor, "subscription", None)
        if not sub:
            return False
        return sub.is_active and sub.end_date and sub.end_date > timezone.now()


# BELOW CAN BE USED WHEN MORE TRAFIIC WILL COME

# from django.core.cache import cache

# class IsSubscribed(BasePermission):
#     message = "Your subscription is not active. Please subscribe to continue."

#     def has_permission(self, request, view):
#         vendor = getattr(request.user, "vendor", None)
#         if not vendor:
#             return False
        
#         # Add caching to reduce DB hits
#         cache_key = f"vendor_subscription_active_{vendor.id}"
#         is_active = cache.get(cache_key)
        
#         if is_active is None:
#             sub = getattr(vendor, "subscription", None)
#             if not sub:
#                 is_active = False
#             else:
#                 is_active = sub.is_active and sub.end_date and sub.end_date > timezone.now()
            
#             # Cache for 5 minutes
#             cache.set(cache_key, is_active, 300)
        
#         return is_active