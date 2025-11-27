from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.core.cache import cache
from apps.products.models import Product
from apps.core.events import ProductCacheUpdateEvent
from apps.core.dispatcher import handle_event_sync

@receiver(pre_save, sender=Product)
def product_pre_save(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        instance._old_is_active = Product.objects.get(pk=instance.pk).is_active
    except Product.DoesNotExist:
        instance._old_is_active = instance.is_active


@receiver(post_save, sender=Product)
def product_saved(sender, instance, created, **kwargs):
    if not instance.vendor_id:
        return

    # Determine what changed
    if created:
        action = "CREATED"
    elif hasattr(instance, "_old_is_active") and instance._old_is_active != instance.is_active:
        action = "UPDATED"
    else:
        # No relevant change for cache
        return

    event_payload = {
        "vendor_id": instance.vendor_id,
        "instance": instance,
        "action": action
    }

    event = ProductCacheUpdateEvent(event_payload)
    handle_event_sync(event)


# --- Handle delete ---
@receiver(post_delete, sender=Product)
def product_deleted(sender, instance, **kwargs):
    if not instance.vendor_id:
        return

    event_payload = {
        "vendor_id": instance.vendor_id,
        "instance": instance,
        "action": "DELETED"
    }

    event = ProductCacheUpdateEvent(event_payload)
    handle_event_sync(event)

