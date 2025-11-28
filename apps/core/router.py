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
from apps.core.handlers.vendor_handler import VendorUpdatedSubscriber


EVENT_ROUTES = {
    # Product events
    "product.created": [ProductCreatedSubscriber],
    "product.updated": [ProductUpdatedSubscriber],
    "product.deleted": [ProductDeletedSubscriber],
    
    # Vendor events
    "vendor.updated": [VendorUpdatedSubscriber],
}
