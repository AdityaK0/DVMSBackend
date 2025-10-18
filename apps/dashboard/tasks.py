

# will take this when needed like async + celery + background tasks and all

from celery import shared_task
from apps.core.dispatcher import handle_event_async
from apps.core.events import (
    ProductCacheUpdateEvent,
    CustomerCacheUpdateEvent,
    ActivityCacheUpdateEvent,
)

EVENT_MAP = {
    "ProductCacheUpdateEvent": ProductCacheUpdateEvent,
    "CustomerCacheUpdateEvent": CustomerCacheUpdateEvent,
    "ActivityCacheUpdateEvent": ActivityCacheUpdateEvent,
}

@shared_task
def handle_event_task(event, vendor_id):
    """Async event handler to avoid blocking main thread"""
    event_class = EVENT_MAP.get(event.__class__.__name__)
    if not event_class:
        return
    event = event_class(vendor_id)
    handle_event_async(event)
