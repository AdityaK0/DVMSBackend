# core/tasks.py

import logging
from celery import shared_task
from apps.core.router import EVENT_ROUTES


from celery import shared_task
from django.core.cache import cache
from apps.vendors.models import Vendor
from apps.products.models import Product
from apps.core.events import BaseEvent


logger = logging.getLogger(__name__)


@shared_task(name="apps.core.tasks.handle_event", bind=True, max_retries=3)
def handle_event(self, handler_name, event_name, payload):
    """
    Generic Celery task for executing event handlers asynchronously.
    
    Args:
        handler_name (str): Name of the handler class to execute
        event_name (str): Name of the event (e.g., "product.updated")
        payload (dict): Event payload data
    
    Returns:
        bool: True if handler executed successfully
    """
    logger.info(f"🔥 Celery executing event: {event_name} → {handler_name}")

    handlers = EVENT_ROUTES.get(event_name, [])
    
    for handler_cls in handlers:
        if handler_cls.__name__ == handler_name:
            try:
                handler = handler_cls()
                
                event = BaseEvent(payload)
                
                # Execute handler
                handler(event)
                
                logger.info(f" Handler {handler_name} completed successfully")
                return True
                
            except Exception as e:
                logger.error(f" Handler {handler_name} failed: {e}", exc_info=True)
                
                # Retry on failure
                try:
                    raise self.retry(exc=e, countdown=60)  # Retry after 60 seconds
                except self.MaxRetriesExceededError:
                    logger.error(f" Max retries exceeded for {handler_name}")
                    return False

    logger.warning(f"Handler not found: {handler_name}")
    return False




@shared_task(name="apps.core.tasks.celery_warmup")
def celery_warmup():
    """
    Run once on worker startup to warm everything:
    - Import Django models
    - Open DB connections
    - Touch Redis
    - Load serializers/subscribers
    """

    print("🔥 Celery warmup started...")

    # Touch cache
    cache.set("celery:warmup", "ok", timeout=60)

    # Touch DB
    Vendor.objects.first()
    Product.objects.first()

    # Import event handlers (forces load)
    from apps.core.handlers.vendor_handler import VendorUpdatedSubscriber
    from apps.core.handlers.product_handler import ProductUpdatedSubscriber

    VendorUpdatedSubscriber()
    ProductUpdatedSubscriber()

    print("✅ Celery warmup complete")
    return "warmed"
