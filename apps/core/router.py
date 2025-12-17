# core/router.py

"""
Event routing configuration.

Maps event names to their subscriber handlers.
Add new event → handler mappings here.
"""

from apps.core.handlers.product_handler import (
    ProductCreatedSubscriber,
    ProductUpdatedSubscriber,
    ProductDeletedSubscriber
)
from apps.core.handlers.customer_handler import (
    CustomerCreatedSubscriber,
    CustomerUpdatedSubscriber,
    CustomerDeletedSubscriber,
)
from apps.core.handlers.vendor_handler import VendorUpdatedSubscriber


EVENT_ROUTES = {
    # Product events
    "product.created": [ProductCreatedSubscriber],
    "product.updated": [ProductUpdatedSubscriber],
    "product.deleted": [ProductDeletedSubscriber],
    

    
    # Customer events
    "customer.created": [CustomerCreatedSubscriber],
    "customer.updated": [CustomerUpdatedSubscriber],
    "customer.deleted": [CustomerDeletedSubscriber],

    # Vendor events
    "vendor.updated": [VendorUpdatedSubscriber],
}
