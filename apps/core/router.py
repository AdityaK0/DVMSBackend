from apps.core.handlers.product_handler import ProductUpdatedSubscriber,ProductDeletedSubscriber
from apps.core.handlers.vendor_handler import VendorUpdatedSubscriber

EVENT_ROUTES = {
    "product.updated": [ProductUpdatedSubscriber],
    "vendor.updated":  [VendorUpdatedSubscriber],
    "product.deleted":[ProductDeletedSubscriber],
}

