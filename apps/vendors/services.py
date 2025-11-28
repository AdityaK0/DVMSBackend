from rest_framework import generics, permissions,status
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from .models import Vendor,Event,PosterTemplate
from .serializers import VendorSerializer, VendorListSerializer, VendorUpdate,EventSerializer,PosterTemplateSerializer
from shared.permissions import IsVendorOrReadOnly
from rest_framework.exceptions import ValidationError

from apps.users.models import Address
from django.db import IntegrityError
from rest_framework import status
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
        
        # Publish event with standardized payload after transaction commits
        from django.db import transaction
        transaction.on_commit(lambda: VendorUpdated({
            "id": vendor.id,
            "action": "updated",
            "data": serializer,
            "metadata": {}
        }).publish(bg=True))
        
        return serializer
    