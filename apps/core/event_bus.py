# core/event_bus.py

import logging
from apps.core.router import EVENT_ROUTES
from .celery import celery_app

logger = logging.getLogger(__name__)


class EventBus:
    """
    Central event dispatcher.
    
    Routes events to registered subscribers based on EVENT_ROUTES.
    Supports both synchronous and asynchronous (Celery) processing.
    """

    @staticmethod
    def dispatch(event, bg=False):
        """
        Dispatch event to all registered handlers.
        
        Args:
            event: BaseEvent instance
            bg (bool): If True, dispatch via Celery (async)
                      If False, execute handlers synchronously
        
        Returns:
            bool: True if dispatched successfully
        """
        handlers = EVENT_ROUTES.get(event.event_name, [])

        if not handlers:
            logger.warning(f"⚠️  No handlers registered for event: {event.event_name}")
            return False

        if bg:
            # ASYNC MODE: Send to Celery queue
            logger.info(f"📤 Dispatching event '{event.event_name}' to {len(handlers)} handler(s) [ASYNC]")
            
            for handler_cls in handlers:
                try:
                    celery_app.send_task(
                        "apps.core.tasks.handle_event",
                        args=(handler_cls.__name__, event.event_name, event.payload),
                    )
                except Exception as e:
                    logger.error(f"❌ Failed to dispatch event to Celery: {e}")
                    return False

            return True

        # SYNC MODE: Execute handlers immediately
        logger.info(f"⚡ Dispatching event '{event.event_name}' to {len(handlers)} handler(s) [SYNC]")
        
        for handler_cls in handlers:
            try:
                handler = handler_cls()
                handler(event)
            except Exception as e:
                logger.error(f"❌ Handler {handler_cls.__name__} failed: {e}", exc_info=True)
                # Continue processing other handlers even if one fails
                
        return True
