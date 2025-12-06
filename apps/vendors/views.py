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
from django.db import transaction
from apps.core.cache_decorators import refresh_cache


from .models import Event, PosterTemplate
from .serializers import EventSerializer, PosterTemplateSerializer
from .permissions import IsVendor
from .services import VendorService

import json
import logging


logger = logging.getLogger(__name__)
  

@api_view(["POST"])
@permission_classes([IsAuthenticated])
@refresh_cache(invalidate_user=True, invalidate_vendor=True)
def create_vendor(request):
    user = request.user

    if user.role == "customer":
        return Response(
            {"error": "You already have a customer account. Please create a new account for vendor access."},
            status=status.HTTP_400_BAD_REQUEST
        )

    if user.role != "vendor":
        return Response(
            {"error": "Only vendor accounts can create a vendor profile."},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        with transaction.atomic():
            vendor = getattr(user, "vendor", None)
            if vendor is None:
                return Response(
                    {"detail": "Vendor profile not found for this user."},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            incoming_phone = request.data.get("business_phone")
            if incoming_phone and Vendor.objects.exclude(id=vendor.id).filter(business_phone=incoming_phone).exists():
                raise ValidationError({"business_phone": "This business phone is already registered."})

            incoming_email = request.data.get("business_email")
            if incoming_email and Vendor.objects.exclude(id=vendor.id).filter(business_email=incoming_email).exists():
                raise ValidationError({"business_email": "This business email is already registered."})

            #  Vendor update
            update_fields = [
                "business_name", "business_type", "business_email",
                "business_description", "business_phone", "website", "gstin"
            ]
            for field in update_fields:
                setattr(vendor, field, request.data.get(field, getattr(vendor, field)))
                
            if request.data.get("geo_location"):
                vendor.geolocation  = json.loads(request.data.get("geo_location"))
            
    
            vendor.logo = request.data.get("logo", vendor.logo)
            vendor.is_onboarded = True
            vendor.save()

            # ✅ Generate permanent handle on first onboarding (never auto-updates)
            if not vendor.handle:
                from apps.vendors.utils import generate_unique_handle
                vendor.handle = generate_unique_handle(vendor.business_name, vendor_id=vendor.id)
                logger.info(f"Generated handle '{vendor.handle}' for vendor {vendor.id}")

            # Auto-generate slug (kept for backward compatibility)
            vendor.business_name_slug = slugify(f"{vendor.business_name}-v{vendor.id}")
            vendor.is_active = True
            
            vendor.save()

            # Create/update Address
            address, created = Address.objects.get_or_create(
                user=user,
                defaults={
                    "street_address": request.data.get("street_address", ""),
                    "city": request.data.get("city", ""),
                    "state": request.data.get("state", ""),
                    "postal_code": request.data.get("zip_code", ""),
                    "zip_code": request.data.get("zip_code", ""),
                    "country": request.data.get("country", ""),
                    "is_default": True,
                    "address_type": "both",
                }
            )

            if not created:
                for field in ["street_address", "city", "state", "zip_code", "country"]:
                    setattr(address, field, request.data.get(field, getattr(address, field)))
                address.save()

            # Auto-create default vendor data
            create_default_categories_for_vendor(vendor)
            create_default_portfolio_for_vendor(vendor)
            # Final response
            serializer = VendorSerializer(vendor)
            return Response(serializer.data, status=status.HTTP_200_OK)

    except ValidationError as ve:
        return Response({"errors": ve.detail}, status=status.HTTP_400_BAD_REQUEST)

    except IntegrityError:
        return Response({"error": "Business email already exists."}, status=status.HTTP_409_CONFLICT)

    except Exception as e:
        logger.exception("create_vendor failed: %s", e)
        return Response(
            {"error": "Internal server error during vendor update."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET', 'PUT', 'PATCH'])
@permission_classes([IsAuthenticated, IsVendorOrReadOnly])
def vendor_profile(request, pk=None):
    """
    GET   -> return vendor profile
    PUT/PATCH -> update vendor profile
    """

    try:
        if pk:
            vendor = Vendor.objects.select_related('user').prefetch_related('user__addresses').get(pk=pk)
        else:
            vendor = Vendor.objects.select_related('user').prefetch_related('user__addresses').get(user=request.user)
    except Vendor.DoesNotExist:
        return Response({"detail": "Vendor profile not found."}, status=404)

    # --------- GET ---------
    if request.method == "GET":
        serializer = VendorSerializer(vendor)
        return Response(serializer.data)

    try:
        updated_vendor = VendorService.update_vendor( 
            vendor,
            request.data,
            context={"request": request},
        )
    except ValidationError as e:
        return Response(e.detail, status=400)
    
    if isinstance(updated_vendor,dict):
        return Response(updated_vendor)
    
    serializer = VendorSerializer(updated_vendor)
    return Response(serializer.data)

    



# vendor implenentation for posters this will be always vendor side so kind of static data non-violate data


@api_view(["POST"])
@permission_classes([permissions.IsAdminUser])
def create_event(request):
    """
    Admin creates a festival event template.
    """
    serializer = EventSerializer(data=request.data)
    if serializer.is_valid():
        event = serializer.save()

        # auto-update status on creation
        event.auto_update_status()

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["PUT", "PATCH"])
@permission_classes([permissions.IsAdminUser])
def update_event(request, event_id):
    """
    Admin updates an existing event.
    """
    event = get_object_or_404(Event, id=event_id)
    
    serializer = EventSerializer(event, data=request.data, partial=True)
    if serializer.is_valid():
        updated_event = serializer.save()
        updated_event.auto_update_status()
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["DELETE"])
@permission_classes([permissions.IsAdminUser])
def delete_event(request, event_id):
    """
    Admin deletes an event (and all associated posters).
    """
    event = get_object_or_404(Event, id=event_id)
    event.delete()
    return Response({"detail": "Event deleted successfully"}, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([permissions.IsAdminUser])
def create_poster(request, event_id):
    """
    Admin creates a poster template inside an event.
    """
    event = get_object_or_404(Event, id=event_id)

    data = request.data.copy()
    data["event"] = event.id

    serializer = PosterTemplateSerializer(data=data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["PUT", "PATCH"])
@permission_classes([permissions.IsAdminUser])
def update_poster(request, poster_id):
    """
    Admin updates an existing poster template.
    """
    poster = get_object_or_404(PosterTemplate, id=poster_id)
    
    serializer = PosterTemplateSerializer(poster, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["DELETE"])
@permission_classes([permissions.IsAdminUser])
def delete_poster(request, poster_id):
    """
    Admin deletes a poster template.
    """
    poster = get_object_or_404(PosterTemplate, id=poster_id)
    poster.delete()
    return Response({"detail": "Poster template deleted successfully"}, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsVendor | permissions.IsAdminUser])
def list_events(request):
    """
    Vendor sees ALL events (admin created).
    Frontend can filter by status.
    """
    for event in Event.objects.all():
        event.auto_update_status()

    events = Event.objects.filter(is_active=True).order_by("start_date")
    serializer = EventSerializer(events, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsVendor | permissions.IsAdminUser])
def list_event_posters(request, event_id):
    """
    Vendor gets list of posters for a given event.
    """
    event = get_object_or_404(Event, id=event_id, is_active=True)

    posters = PosterTemplate.objects.filter(event=event, is_active=True)
    serializer = PosterTemplateSerializer(posters, many=True)

    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(["GET"])
@permission_classes([IsVendor | permissions.IsAdminUser])
def get_single_poster(request, poster_id):
    """
    Vendor fetches a single poster for editing/preview.
    """
    poster = get_object_or_404(PosterTemplate, id=poster_id, is_active=True)
    serializer = PosterTemplateSerializer(poster)

    return Response(serializer.data, status=status.HTTP_200_OK)




import requests
from django.conf import settings

def is_telegram_chat_active(chat_id: str) -> bool:
    """
    Verify if the Telegram chat_id is still valid and user has not blocked the bot.
    """
    if not chat_id:
        return False
    try:
        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/getChat"
        resp = requests.post(url, json={"chat_id": chat_id}, timeout=5)
        data = resp.json()
        # Telegram returns {"ok": false, "description": "Forbidden: bot was blocked by the user"}
        return data.get("ok", False)
    except Exception:
        return False
