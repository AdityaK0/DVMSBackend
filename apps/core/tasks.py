# core/tasks.py

import logging
from celery import shared_task
from apps.core.router import EVENT_ROUTES

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
                # Instantiate handler
                handler = handler_cls()
                
                # Create event object from payload
                class EventObj:
                    """Lightweight event object for Celery context."""
                    def __init__(self, **kwargs):
                        for k, v in kwargs.items():
                            setattr(self, k, v)
                
                event = EventObj(**payload)
                
                # Execute handler
                handler(event)
                
                logger.info(f"✅ Handler {handler_name} completed successfully")
                return True
                
            except Exception as e:
                logger.error(f"❌ Handler {handler_name} failed: {e}", exc_info=True)
                
                # Retry on failure
                try:
                    raise self.retry(exc=e, countdown=60)  # Retry after 60 seconds
                except self.MaxRetriesExceededError:
                    logger.error(f"⛔ Max retries exceeded for {handler_name}")
                    return False

    logger.warning(f"⚠️  Handler not found: {handler_name}")
    return False
