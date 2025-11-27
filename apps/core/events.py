# core/events.py

class BaseEvent:
    event_name = None

    def __init__(self, payload: dict):
        self.payload = payload
        for key, val in payload.items():
            setattr(self, key, val)

    def publish(self, bg=False):
        from apps.core.event_bus import EventBus
        return EventBus.dispatch(self, bg=bg)


class ProductUpdated(BaseEvent):
    event_name = "product.updated"


class VendorUpdated(BaseEvent):
    event_name = "vendor.updated"


class ProductDeleted(BaseEvent):
    event_name = "product.deleted"

