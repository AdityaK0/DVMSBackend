# core/events.py

class BaseEvent:
    """Base event wrapper to hold payloads dynamically."""
    def __init__(self, event_payload: dict):
        # Extract all fields directly as attributes for easy access
        self.event_payload = event_payload
        for key, value in event_payload.items():
            setattr(self, key, value)


class ProductCacheUpdateEvent(BaseEvent): 
    pass

class CustomerCacheUpdateEvent(BaseEvent): 
    pass

class ActivityCacheUpdateEvent(BaseEvent): 
    pass