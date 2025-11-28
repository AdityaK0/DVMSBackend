
from .models import Vendor,Event,PosterTemplate
from .serializers import VendorSerializer, VendorUpdate
from django.db import transaction
from apps.core.events import VendorUpdated



class VendorService:
    
    @staticmethod
    def update_vendor(vendor, data, *, context=None):
        """
        Update vendor profile using VendorUpdate serializer.
        Returns the updated vendor instance.
        Raises DRF ValidationError if invalid.
        """
        serializer = VendorUpdate(
            vendor,
            data=data,
            partial=True,
            context=context
        )

        serializer.is_valid(raise_exception=True)

        updated_vendor = serializer.save()
        
        serializer = VendorSerializer(updated_vendor).data
        
        
        VendorUpdated({ # event launch to update the cache data 
            "id": vendor.id,
            "action": "updated",
            "data": serializer,
            "metadata": {
                "user_id": vendor.user_id  # Include user_id for cache invalidation
            }
        }).publish(bg=True)
        
        return serializer
    