from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from apps.products.models import Product
from .models import Customer
# from apps.core.events import CustomerCacheUpdateEvent
# from apps.core.dispatcher import handle_event_sync


# --- Pre-save: track old is_active state for updates ---

@receiver(pre_save, sender=Customer)
def customer_pre_save(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        instance._old_is_active = Customer.objects.get(pk=instance.pk).is_active
    except Customer.DoesNotExist:
        instance._old_is_active = instance.is_active


# --- Post-save: handle CREATE and UPDATE ---

@receiver(post_save, sender=Customer)
def customer_saved(sender, instance, created, **kwargs):
    if not instance.vendor_id:
        return

    # Determine the type of action
    if created:
        action = "CREATED"
    elif hasattr(instance, "_old_is_active") and instance._old_is_active != instance.is_active:
        action = "UPDATED"
    else:
        # No relevant change
        return

    event_payload = {
        "vendor_id": instance.vendor_id,
        "instance": instance,
        "action": action
    }

    # event = CustomerCacheUpdateEvent(event_payload)
    # handle_event_sync(event)


# --- Post-delete: handle DELETE ---
@receiver(post_delete, sender=Customer)
def customer_deleted(sender, instance, **kwargs):
    if not instance.vendor_id:
        return

    event_payload = {
        "vendor_id": instance.vendor_id,
        "instance": instance,
        "action": "DELETED"
    }

    # event = CustomerCacheUpdateEvent(event_payload)
    # handle_event_sync(event)
