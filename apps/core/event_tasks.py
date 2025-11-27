# core/event_tasks.py

from apps.core.celery import celery_app
from apps.core.router import EVENT_ROUTES


@celery_app.task(name="core.event_tasks.handle_static")
def handle_static(handler_name, event_name, payload):
    handlers = EVENT_ROUTES[event_name]

    for handler_cls in handlers:
        if handler_cls.__name__ == handler_name:
            event = type("Event", (), payload)  # simple dynamic event object
            handler = handler_cls()
            handler(event)
            return
