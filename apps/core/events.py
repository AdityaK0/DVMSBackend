# core/events.py
class BaseEvent:
    def __init__(self, vendor_id):
        self.vendor_id = vendor_id

class ProductCacheUpdateEvent(BaseEvent): pass
class CustomerCacheUpdateEvent(BaseEvent): pass
class ActivityCacheUpdateEvent(BaseEvent): pass
