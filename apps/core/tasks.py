

from celery import shared_task
from apps.core.router import EVENT_ROUTES
from apps.core.event_bus import EventBus

@shared_task(name="apps.core.tasks.handle_static")
def handle_static(handler_name, event_name, payload):
    """
    Generic task runner for event handlers.
    """
    print("🔥 Celery executing event:", event_name)

    handlers = EVENT_ROUTES.get(event_name, [])
    for handler_cls in handlers:
        if handler_cls.__name__ == handler_name:
            handler = handler_cls()
            class EventObj:
                def __init__(self, **kwargs):
                    for k, v in kwargs.items():
                        setattr(self, k, v)
            event = EventObj(**payload)
            handler(event)
            return True

    print("⚠ handler not found:", handler_name)
    return False
