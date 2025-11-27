from rest_framework import generics, permissions,status
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from .models import Vendor,Event,PosterTemplate
from .serializers import VendorSerializer, VendorListSerializer, VendorUpdate,EventSerializer,PosterTemplateSerializer
from shared.permissions import IsVendorOrReadOnly
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from apps.users.models import Address
from django.db import IntegrityError
from .permissions import IsVendor
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError
from apps.utils.default_creation import create_default_categories_for_vendor,create_default_portfolio_for_vendor
from django.utils.text import slugify
from django.shortcuts import get_object_or_404



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
        return updated_vendor
    