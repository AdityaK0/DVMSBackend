# core/event_bus.py

from apps.core.router import EVENT_ROUTES
from .celery import celery_app

class EventBus:

    @staticmethod
    def dispatch(event, bg=False):
        handlers = EVENT_ROUTES.get(event.event_name, [])

        if bg:
            for handler_cls in handlers:
                celery_app.send_task(
                    "apps.core.tasks.handle_static",
                    args=(handler_cls.__name__, event.event_name, event.payload),
                    queue=getattr(handler_cls, "queue", "default")
                )

            return True

        # SYNC MODE
        for handler_cls in handlers:
            handler = handler_cls()  # instantiate once per call
            handler(event)
        return True
