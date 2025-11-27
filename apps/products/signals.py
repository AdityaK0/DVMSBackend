from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from apps.products.models import Product
from apps.core.events import ProductUpdated,ProductDeleted


@receiver(pre_save, sender=Product)
def product_pre_save(sender, instance, **kwargs):
    if not instance.pk:
        instance._old_is_active = None
        return

    try:
        instance._old_is_active = Product.objects.get(pk=instance.pk).is_active
    except Product.DoesNotExist:
        instance._old_is_active = None


@receiver(post_save, sender=Product)
def product_saved(sender, instance, created, **kwargs):
    if not instance.vendor_id:
        return

    if created:
        action = "CREATED"
    elif hasattr(instance, "_old_is_active") and instance._old_is_active != instance.is_active:
        action = "UPDATED"
    else:
        return

    payload = {
        "product_id": instance.pk,
        "vendor_id": instance.vendor_id,
        "is_active": instance.is_active,
        "_old_is_active": instance._old_is_active, 
        "action": action
    }

    ProductUpdated(payload).publish()     # SYNC
    


@receiver(post_delete, sender=Product)
def product_deleted(sender, instance, **kwargs):
    if not instance.vendor_id:
        return

    
    payload = {
    "product_id": instance.pk,
    "vendor_id": instance.vendor_id,
    "is_active": instance.is_active,
    "_old_is_active": instance._old_is_active if hasattr(instance, "_old_is_active") else None,
    "action": "DELETED"
   }


    ProductDeleted(payload).publish()
