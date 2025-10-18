# service.py
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from django.core.cache import cache
from .models import  Customer, Event, CustomerMessage, ActivityLog
from .serializers import ActivityLogSerializer
from  apps.utils.cache import cache_safe_get
from apps.products.models import Product


def get_product_stats_cached(vendor):
    key = f"vendor:{vendor.id}:products"
    return cache_safe_get(key, lambda: get_product_stats(vendor))

def get_customer_stats_cached(vendor):
    key = f"vendor:{vendor.id}:customers"
    return cache_safe_get(key, lambda: get_customer_stats(vendor))

def get_activity_data_cached(vendor):
    key = f"vendor:{vendor.id}:activity"
    return cache_safe_get(key, lambda: get_activity_data(vendor))




def get_product_stats(vendor):
    total_products = Product.objects.filter(vendor=vendor, is_archived=False).count()
    total_active_products = Product.objects.filter(vendor=vendor, is_active=True, is_archived=False).count()
    total_inactive_products = total_products - total_active_products

    return {
        'total_products': total_products,
        'total_active_products': total_active_products,
        'total_inactive_products': total_inactive_products
    }

def get_customer_stats(vendor):
    total_customers = Customer.objects.filter(vendor=vendor).count()
    total_active_customers = Customer.objects.filter(vendor=vendor, is_active=True).count()
    total_inactive_customers = total_customers - total_active_customers

    return {
        'total_customers': total_customers,
        'total_active_customers': total_active_customers,
        'total_inactive_customers': total_inactive_customers
    }

def get_activity_data(vendor):
    current_month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    events_count = Event.objects.filter(vendor=vendor, created_at__gte=current_month_start, is_active=True).count()
    messages_sent = CustomerMessage.objects.filter(vendor=vendor).count()
    logs = ActivityLog.objects.filter(vendor=vendor).order_by('-created_at')[:5]
    logs_data = ActivityLogSerializer(logs, many=True).data

    return {
        'events_this_month': events_count,
        'messages_sent': messages_sent,
        'recent_activities': logs_data
    }

def get_dashboard_summary(vendor):
    """Return all cached dashboard data"""
    return {
        "products": cache.get_or_set(f"vendor:{vendor.id}:products", lambda: get_product_stats(vendor), 300),
        "customers": cache.get_or_set(f"vendor:{vendor.id}:customers", lambda: get_customer_stats(vendor), 300),
        # "activity": cache.get_or_set(f"vendor:{vendor.id}:activity", lambda: get_activity_data(vendor), 300),
        "vendor_info": {
            "business_name": vendor.business_name,
            "is_verified": vendor.is_verified,
        }
    }
