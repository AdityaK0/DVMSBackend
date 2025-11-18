from rest_framework import permissions


class IsVendor(permissions.BasePermission):
    """
    Permission to only allow vendors to access.
    Rule: request.user.role == "vendor"
    """
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and 
            request.user.role == 'vendor'
        )


class IsVendorOwner(permissions.BasePermission):
    """
    Permission to only allow owners of an event to access it.
    """
    def has_object_permission(self, request, view, obj):
        return (
            request.user.is_authenticated and 
            request.user.role == 'vendor' and
            obj.vendor.user == request.user
        )

