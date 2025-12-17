
from django.core.cache import cache
from .models import  Customer
from  apps.utils.cache import cache_safe_get
from apps.products.models import Product
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Invoice
from .serializers import InvoiceSerializer
from apps.vendors.models import VendorStats


def get_product_stats_cached(vendor):
    key = f"vendor:context:{vendor.id}:products"  # ✅ Standardized key
    return cache_safe_get(key, lambda: get_product_stats(vendor))

def get_customer_stats_cached(vendor):
    key = f"vendor:context:{vendor.id}:customers"  # ✅ Standardized key
    return cache_safe_get(key, lambda: get_customer_stats(vendor))




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
    vendor_stats = VendorStats.objects.select_related('vendor').get(vendor=vendor)
    return {
        "products": {
            "total_products": vendor_stats.total_products,
            "total_active_products": vendor_stats.active_products,
            "total_inactive_products": vendor_stats.inactive_products,
        },
        "customers": {
            "total_customers": vendor_stats.total_customers,
            "total_active_customers": vendor_stats.active_customers,
            "total_inactive_customers": vendor_stats.inactive_customers,
        },
    }
    # return {
    #     "products": cache.get_or_set(f"vendor:context:{vendor.id}:products", lambda: get_product_stats(vendor), 300),
    #     "customers": cache.get_or_set(f"vendor:context:{vendor.id}:customers", lambda: get_customer_stats(vendor), 300),
    # }



def get_vendor_invoices_combined(
    vendor,
    request=None,
    page=1,
    page_size=10,
    search="",
    pending_only=False,
    paid_only=False,
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

    if paid_only:
        queryset = queryset.filter(pending_amount=0)        

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
    


TRACKED_FIELDS = [
    "customer_name",
    "customer_phone",
    "items",
    "total_amount",
    "paid_amount",
    "pending_amount",
    "is_udhaari",
     "invoice_date",
]


def normalize(v):
    """Normalize values for safer comparison."""
    if v is None:
        return ""
    if isinstance(v, str):
        return v.strip()
    return v


def build_invoice_changes(old_data, new_data, tracked_fields=None):
    """
    Compare old vs new values and return only changed fields.
    Example:
    {
        "customer_name": {"old": "Aditya", "new": "Aditya Chaudhary"},
        "paid_amount": {"old": 100, "new": 200},
    }
    """
    if tracked_fields is None:
        tracked_fields = TRACKED_FIELDS

    changes = {}

    for field in tracked_fields:

        old_val = old_data.get(field)
        new_val = new_data.get(field)

        # normalized values to detect real differences
        if normalize(old_val) != normalize(new_val):
            changes[field] = {
                "old": old_val,
                "new": new_val,
            }

    return changes


from django.db import transaction
from django.utils import timezone
from apps.dashboard.models import Customer
from apps.core.events import (
    CustomerCreated,
    CustomerUpdated,
    CustomerDeleted
)


class CustomerService:

    @staticmethod
    def create_customer(vendor, data):
        phone = data.get("phone")

        if Customer.objects.filter(vendor=vendor, phone=phone).exists():
            raise ValueError(f"Customer with phone '{phone}' already exists.")

        with transaction.atomic():
            customer = Customer.objects.create(
                vendor=vendor,
                name=data.get("name"),
                phone=phone,
                is_active=data.get("is_active", True),
                bought=0,
                last_interaction=timezone.now(),
            )

        CustomerCreated({
            "id": customer.id,
            "action": "created",
            "data": {
                "phone": customer.phone,
                "is_active": customer.is_active
            },
            "metadata": {
                "vendor_id": vendor.id,
            }
        }).publish(bg=False)

        return customer

    @staticmethod
    def update_customer(customer, data):
        old_is_active = customer.is_active

        for field in ["name", "phone", "is_active"]:
            if field in data:
                setattr(customer, field, data[field])

        customer.last_interaction = timezone.now()
        customer.save()

        CustomerUpdated({
            "id": customer.id,
            "action": "updated",
            "data": None,
            "metadata": {
                "vendor_id": customer.vendor_id,
                "old_is_active": old_is_active,
                "new_is_active": customer.is_active,
            }
        }).publish(bg=False)

        return customer

    @staticmethod
    def delete_customer(customer):
        vendor_id = customer.vendor_id
        was_active = customer.is_active

        customer.delete()

        CustomerDeleted({
            "id": customer.id,
            "action": "deleted",
            "data": None,
            "metadata": {
                "vendor_id": vendor_id,
                "was_active": was_active,
            }
        }).publish(bg=False)
