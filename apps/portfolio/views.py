from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.conf import settings
from rest_framework.parsers import MultiPartParser, FormParser
from apps.vendors.models import Vendor
from .models import (
    Portfolio, PortfolioCollection
)
from .serializers import (
    PortfolioSerializer, PortfolioCollectionSerializer,
)
from apps.utils.upload_image import upload_collection_image
from scripts.es.sync_vendor_to_es import sync_vendor
from .service import PortfolioService
import logging
from django.conf import settings

logger = logging.getLogger(__name__)



# ---- product service currently importing but later on had to go on cache due to public api

from apps.subscriptions.permissions import IsSubscribed



def safe_get_list(data, key):
    """
    Safely extract list-like data from request.data,
    supporting both QueryDict (multipart) and dict (JSON).
    """
    # If multipart QueryDict
    if hasattr(data, "getlist"):
        return data.getlist(key)

    # If JSON dict
    value = data.get(key)

    if value is None:
        return []

    if isinstance(value, list):
        return value

    # Single value fallback
    return [value]


@api_view(['GET', 'PUT', 'PATCH'])
@permission_classes([permissions.IsAuthenticated])
def vendor_portfolio_manage(request):
    vendor = request.user.vendor
    portfolio = Portfolio.objects.get(vendor=vendor)

    if request.method == "GET":
        return Response(PortfolioSerializer(portfolio).data)

    # Banner image already uploaded from frontend
    banner_url = request.data.get("banner_image_url")
    if banner_url == "":
        portfolio.banner_image = None  #  Remove banner
    elif banner_url:
        portfolio.banner_image = banner_url  #  Update banner


    #  Existing carousel URLs (kept by user)
    # existing = request.data.getlist("carousel_images_existing")
    existing = safe_get_list(request.data, "carousel_images_existing")
    

    #  New carousel URLs uploaded from frontend
    # new_uploaded = request.data.getlist("carousel_images_new_urls")
    new_uploaded = safe_get_list(request.data, "carousel_images_new_urls")
    
    featured = safe_get_list(request.data, "featured_product_ids")
    

    portfolio.carousel_images = existing + new_uploaded
    portfolio.save(update_fields=["banner_image", "carousel_images"])

    serializer = PortfolioSerializer(portfolio, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()

    return Response(serializer.data)


@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def portfolio_collections(request):
    vendor = getattr(request.user, "vendor", None)
    if not vendor:
        return Response({"detail": "Vendor not found."}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        data = PortfolioService.get_vendor_collections(vendor)
        return Response(data, status=status.HTTP_200_OK)

    portfolio = get_object_or_404(Portfolio, vendor=vendor)
    serializer = PortfolioCollectionSerializer(data=request.data)
    if serializer.is_valid():
        collection = serializer.save(portfolio=portfolio)

        # Handle single image upload
        image_file = request.FILES.get('image')
        if image_file:
            upload_collection_image(collection, image_file)

        response_serializer = PortfolioCollectionSerializer(collection)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)






@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([permissions.IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def portfolio_collection_detail(request, id):
    vendor = getattr(request.user, "vendor", None)
    if not vendor:
        return Response({"detail": "Vendor not found."}, status=status.HTTP_404_NOT_FOUND)

    collection = get_object_or_404(PortfolioCollection, id=id, portfolio__vendor=vendor)

    if request.method == 'GET':
        serializer = PortfolioCollectionSerializer(collection)
        return Response(serializer.data)

    elif request.method in ['PUT', 'PATCH']:
        serializer = PortfolioCollectionSerializer(
            collection,
            data=request.data,
            partial=(request.method == 'PATCH')
        )

        if serializer.is_valid():
            collection = serializer.save()
            # Optional: handle image replacement
            image_file = request.FILES.get('image')
            if image_file:
                upload_collection_image(collection, image_file)

            response_serializer = PortfolioCollectionSerializer(collection)
            return Response(response_serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        collection.delete()
        return Response({"detail": "collection deleted successfully "}, status=status.HTTP_200_OK)
    
    


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated,IsSubscribed])
def trigger_sync(request):
    """
    Sync portfolio + products + collections to Elasticsearch
    """
    user = request.user
    

    if user.role != "vendor":
        return Response(
            {"error": "Only vendors can sync their portfolio."},
            status=status.HTTP_403_FORBIDDEN,
        )

    vendor = Vendor.objects.filter(user=user).first()
    if not vendor:
        return Response({"error": "Vendor not found"}, status=status.HTTP_404_NOT_FOUND)

    plan = PortfolioService.create_vendor_sync_plan(vendor)

    if not plan.can_sync():
        return Response(
            {
                "status": "blocked",
                "message": "Sync limit reached for today.",
                "remaining_syncs": plan.remaining_syncs,
                "extra_syncs_available": plan.extra_syncs_available,
            },
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    # Execute sync
    try:
        # FIXED: Wrap external sync call to avoid unhandled exceptions
        result = sync_vendor(vendor.id)
        plan.refresh_from_db()
        
        return Response(
            {
                "status": "success",
                "message": "Vendor synced successfully!",
                "synced_docs": result.get("synced_docs"),
                "remaining_syncs": plan.remaining_syncs,
                "extra_syncs_available": plan.extra_syncs_available,
            }
        )
    except Exception as e:
        logger.exception("trigger_sync failed for vendor %s: %s", vendor.id, e)
        return Response(
            {"detail": "Sync failed. Try again later."},
            status=status.HTTP_502_BAD_GATEWAY,
        )


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def sync_status(request):
    user = request.user
    if user.role != "vendor":
        return Response(
            {"error": "Only vendors can view sync status."},
            status=status.HTTP_403_FORBIDDEN,
        )

    vendor = Vendor.objects.filter(user=user).first()
    if not vendor:
        return Response({"error": "Vendor not found."}, status=status.HTTP_404_NOT_FOUND)

    sync_data = {
        "remaining_syncs": 0,
        "used_syncs_today": 0,
        "allowed_syncs_per_day": getattr(settings, "DEFAULT_SYNC_COUNT", 5),
        "extra_syncs_available": 0,
        "last_sync_at": None,
    }

    try:
        plan = PortfolioService.create_vendor_sync_plan(vendor)
        sync_data.update({
            "remaining_syncs": plan.remaining_syncs or 0,
            "used_syncs_today": plan.used_syncs_today or 0,
            "allowed_syncs_per_day": plan.allowed_syncs_per_day or getattr(settings, "DEFAULT_SYNC_COUNT", 5),
            "extra_syncs_available": plan.extra_syncs_available or 0,
            "last_sync_at": plan.last_sync_at.isoformat() if plan.last_sync_at else None,
        })
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.exception("Error loading sync plan: %s", e)
        sync_data["error"] = "Unable to load sync data; using defaults."

    return Response(sync_data)
