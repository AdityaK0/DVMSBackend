from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Product
from apps.core.events import ProductCacheUpdateEvent
from apps.core.dispatcher import handle_event

@receiver([post_save, post_delete], sender=Product)
def update_product_cache(sender, instance, **kwargs):
    if instance.vendor:
        event = ProductCacheUpdateEvent(vendor_id=instance.vendor_id)
        handle_event(event)
