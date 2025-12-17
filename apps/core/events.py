# core/events.py

class BaseEvent:
    """
    Base event class for all domain events.
    
    Events should be published ONLY from the service layer,
    after successful state changes (create/update/delete).
    
    Never publish events from:
    - GET endpoints
    - Signals (use service layer instead)
    - View layer (use service layer instead)
    """
    event_name = None

    def __init__(self, payload: dict):
        """
        Initialize event with payload.
        
        Standard payload structure:
        {
            "id": <primary_key>,
            "action": "created|updated|deleted",
            "data": <serialized_object>,
            "metadata": {<optional_context>}
        }
        """
        self.payload = payload
        # Set payload keys as attributes for easy access
        for key, val in payload.items():
            setattr(self, key, val)

    def publish(self, bg=False):
        """
        Publish event to EventBus.
        
        Args:
            bg (bool): If True, process asynchronously via Celery.
                      If False, process synchronously.
        
        Use bg=True for:
        - Redis cache updates (global state)
        - Heavy operations (ES indexing, external APIs)
        - Non-critical side effects
        
        Use bg=False for:
        - Critical validations
        - Same-transaction updates
        """
        from apps.core.event_bus import EventBus
        return EventBus.dispatch(self, bg=bg)


# ============================================================================
# PRODUCT EVENTS
# ============================================================================

class ProductCreated(BaseEvent):
    """Published after a product is successfully created."""
    event_name = "product.created"


class ProductUpdated(BaseEvent):
    """Published after a product is successfully updated."""
    event_name = "product.updated"


class ProductDeleted(BaseEvent):
    """Published after a product is soft-deleted."""
    event_name = "product.deleted"


# ============================================================================
# CUSTOMER EVENTS
# ============================================================================

class CustomerCreated(BaseEvent):
    event_name = "customer.created"


class CustomerUpdated(BaseEvent):
    event_name = "customer.updated"


class CustomerDeleted(BaseEvent):
    event_name = "customer.deleted"



# ============================================================================
# VENDOR EVENTS
# ============================================================================

class VendorUpdated(BaseEvent):
    """Published after a vendor profile is successfully updated."""
    event_name = "vendor.updated"

