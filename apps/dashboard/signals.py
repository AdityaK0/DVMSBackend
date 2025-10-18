from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.products.models import Product
from .models import ActivityLog


@receiver(post_save, sender=Product)
def log_product_activity(sender, instance, created, **kwargs):
    """
    Automatically log product creation/updates
    """
    if created:
        ActivityLog.objects.create(
            vendor=instance.vendor,
            activity_type='product_added',
            description=f'New product "{instance.name}" added',
            metadata={
                'product_id': instance.id,
                'product_name': instance.name,
                'price': str(instance.price)
            }
        )
    else:
        # Only log if not archived and is a meaningful update
        if not instance.is_archived:
            ActivityLog.objects.create(
                vendor=instance.vendor,
                activity_type='product_updated',
                description=f'Product "{instance.name}" updated',
                metadata={
                    'product_id': instance.id,
                    'product_name': instance.name
                }
            )