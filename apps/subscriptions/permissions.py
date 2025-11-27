# marketplace/apps/subscriptions/permissions.py
from rest_framework.permissions import BasePermission
from django.utils import timezone

class IsSubscribed(BasePermission):
    """
    Permission class that checks if vendor has an active subscription.
    Used for FULL blocking (both read and write).
    """
    message = "Your subscription is not active. Please subscribe to continue."

    def has_permission(self, request, view):
        vendor = getattr(request.user, "vendor", None)
        if not vendor:
            return False
        sub = getattr(vendor, "subscription", None)
        if not sub:
            return False
        return sub.is_active and sub.end_date and sub.end_date > timezone.now()


class IsSubscribedOrReadOnly(BasePermission):
    """
    SOFT BLOCKING: Allow read operations (GET, HEAD, OPTIONS) for all vendors.
    Require active subscription for write operations (POST, PUT, PATCH, DELETE).
    
    This is vendor-friendly - they can view their data even with expired subscription,
    but cannot create/edit/delete until they renew.
    
    Usage:
        @permission_classes([IsAuthenticated, IsSubscribedOrReadOnly])
        def my_view(request):
            ...
    """
    message = "Active subscription required to perform this action. You can still view your data."

    def has_permission(self, request, view):
        # Allow all read operations
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return True
        
        # For write operations, check subscription
        vendor = getattr(request.user, "vendor", None)
        if not vendor:
            return False
        
        sub = getattr(vendor, "subscription", None)
        if not sub:
            return False
        
        return sub.is_active and sub.end_date and sub.end_date > timezone.now()


class RequiresActiveSubscription(BasePermission):
    """
    Strict subscription check for critical operations.
    Returns detailed error message with subscription status.
    
    Usage:
        @permission_classes([IsAuthenticated, RequiresActiveSubscription])
        def critical_operation(request):
            ...
    """
    
    def has_permission(self, request, view):
        vendor = getattr(request.user, "vendor", None)
        if not vendor:
            self.message = "User is not associated with a vendor account."
            return False
        
        sub = getattr(vendor, "subscription", None)
        if not sub:
            self.message = "No subscription found. Please subscribe to access this feature."
            return False
        
        if not sub.is_active:
            self.message = "Your subscription is inactive. Please renew to continue."
            return False
        
        if not sub.end_date or sub.end_date <= timezone.now():
            days_expired = (timezone.now() - sub.end_date).days if sub.end_date else 0
            self.message = f"Your subscription expired {days_expired} days ago. Please renew to continue."
            return False
        
        return True
