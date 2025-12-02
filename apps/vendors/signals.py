from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Vendor
from django.core.cache import cache

@receiver(post_save, sender=Vendor)
def vendor_saved(sender, instance, created, **kwargs):
    cache.delete(f"user:context:{instance.user_id}")        # User context (includes vendor data)
    cache.delete(f"vendor:context:{instance.id}")    # Vendor profile
    cache.delete(f"portfolio:context:{instance.id}")
