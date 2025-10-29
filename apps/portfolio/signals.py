from django.db.models.signals import pre_delete
from django.dispatch import receiver
from cloudinary.uploader import destroy
from .models import PortfolioCollection

@receiver(pre_delete, sender=PortfolioCollection)
def delete_collection_image_from_cloudinary(sender, instance, **kwargs):
    if instance.image:
        try:
            destroy(instance.image)
        except Exception as e:
            print("Failed to delete Cloudinary image:", e)
