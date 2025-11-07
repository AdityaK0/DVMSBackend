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
