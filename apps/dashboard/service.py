# service.py
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from django.core.cache import cache
from .models import  Customer
from  apps.utils.cache import cache_safe_get
from apps.products.models import Product
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Invoice
from .serializers import InvoiceSerializer


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
    total_inactive_products = Product.objects.filter(vendor=vendor, is_active=False, is_archived=False).count()

    return {
        'total_products': total_products,
        'total_active_products': total_active_products,
        'total_inactive_products': total_inactive_products
    }

def get_customer_stats(vendor):
    total_customers = Customer.objects.filter(vendor=vendor).count()
    total_active_customers = Customer.objects.filter(vendor=vendor, is_active=True).count()
    total_inactive_customers = Customer.objects.filter(vendor=vendor, is_active=False).count()

    return {
        'total_customers': total_customers,
        'total_active_customers': total_active_customers,
        'total_inactive_customers': total_inactive_customers
    }


def get_dashboard_summary(vendor):
    """Return all cached dashboard data"""
    return {
        "products": cache.get_or_set(f"vendor:{vendor.id}:products", lambda: get_product_stats(vendor), 300),
        "customers": cache.get_or_set(f"vendor:{vendor.id}:customers", lambda: get_customer_stats(vendor), 300),
        # "activity": cache.get_or_set(f"vendor:{vendor.id}:activity", lambda: get_activity_data(vendor), 300),
        # "vendor_info": {
        #     "business_name": vendor.business_name,
        #     "is_verified": vendor.is_verified,
        # }
    }



def get_vendor_invoices(
    vendor,
    page=1,
    page_size=10,
    search="",
    pending_only=False,
    start_date=None,
    end_date=None
):
    """
    Unified invoice service for vendor:
    - Search by phone / customer name
    - Filter by pending only
    - Filter by date range
    - Pagination
    """

    queryset = Invoice.objects.filter(
        vendor=vendor
    ).order_by("-created_at")

    # Search filter
    if search:
        queryset = queryset.filter(
            Q(customer_phone__icontains=search) |
            Q(customer_name__icontains=search)
        )

    # Pending only filter
    if pending_only:
        queryset = queryset.filter(pending_amount__gt=0)

    # Date filters
    if start_date:
        queryset = queryset.filter(invoice_date__gte=start_date)

    if end_date:
        queryset = queryset.filter(invoice_date__lte=end_date)

    # Pagination
    paginator = Paginator(queryset, page_size)
    page_obj = paginator.get_page(page)

    serializer = InvoiceSerializer(page_obj.object_list, many=True)

    return {
        "results": serializer.data,
        "count": paginator.count,
        "total_pages": paginator.num_pages,
        "current_page": page,
        "has_next": page_obj.has_next(),
        "has_previous": page_obj.has_previous(),
    }
    




# dashboard/services/invoice_history.py (or inside views.py if you prefer)

TRACKED_FIELDS = [
    "items",
    "total_amount",
    "paid_amount",
    "pending_amount",
    "is_udhaari",
    "invoice_date",
]

def build_invoice_changes(old_data, new_data, tracked_fields=None):
    """
    Compare old vs new invoice data and return a dict of changes:
    {
      "field_name": {"old": ..., "new": ...},
      ...
    }
    """
    if tracked_fields is None:
        tracked_fields = TRACKED_FIELDS

    changes = {}

    for field in tracked_fields:
        old_val = old_data.get(field)
        new_val = new_data.get(field)

        # DRF often returns nested objects / lists; equality works fine for JSON
        if old_val != new_val:
            changes[field] = {
                "old": old_val,
                "new": new_val,
            }

    return changes
