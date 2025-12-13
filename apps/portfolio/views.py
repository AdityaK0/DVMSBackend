from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
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
from django.db.models import Prefetch
from apps.products.models import Product
from apps.core.authentication import get_request_vendor
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
    vendor = get_request_vendor(request)
    
    if not vendor:
        print("failed to fetch from the vendor ")
        vendor = request.user.vendor
    
    portfolio = PortfolioService.get_portfolio(vendor)    
    
    # portfolio = Portfolio.objects.select_related(
    #     "vendor", "vendor__user","sync_plan"
    # ).prefetch_related(
    #     Prefetch(
    #         "featured_products",
    #         queryset=Product.objects.select_related("category", "vendor")
    #     )
    # ).get(vendor=vendor)

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
            

        response_serializer = PortfolioCollectionSerializer(collection)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([permissions.IsAuthenticated])
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

            response_serializer = PortfolioCollectionSerializer(collection)
            return Response(response_serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        collection.delete()
        return Response({"detail": "collection deleted successfully "}, status=status.HTTP_200_OK)
    
    


# @api_view(["POST"])
# @permission_classes([permissions.IsAuthenticated,IsSubscribed])
# def trigger_sync(request):
#     """
#     Sync portfolio + products + collections to Elasticsearch
#     """
    
    
#     user = request.user
    

#     if user.role != "vendor":
#         return Response(
#             {"error": "Only vendors can sync their portfolio."},
#             status=status.HTTP_403_FORBIDDEN,
#         )

#     vendor = Vendor.objects.filter(user=user).first()
#     if not vendor:
#         return Response({"error": "Vendor not found"}, status=status.HTTP_404_NOT_FOUND)

#     plan = PortfolioService.get_vendor_sync_plan(vendor)

#     if not plan.can_sync():
#         return Response(
#             {
#                 "status": "blocked",
#                 "message": "Sync limit reached for today.",
#                 "remaining_syncs": plan.remaining_syncs,
#                 "extra_syncs_available": plan.extra_syncs_available,
#             },
#             status=status.HTTP_429_TOO_MANY_REQUESTS,
#         )

#     # Execute sync
#     try:
#         # FIXED: Wrap external sync call to avoid unhandled exceptions
#         result = sync_vendor(vendor.id)
#         plan.refresh_from_db()
        
#         return Response(
#             {
#                 "status": "success",
#                 "message": "Vendor synced successfully!",
#                 "synced_docs": result.get("synced_docs"),
#                 "remaining_syncs": plan.remaining_syncs,
#                 "extra_syncs_available": plan.extra_syncs_available,
#             }
#         )
#     except Exception as e:
#         logger.exception("trigger_sync failed for vendor %s: %s", vendor.id, e)
#         return Response(
#             {"detail": "Sync failed. Try again later."},
#             status=status.HTTP_502_BAD_GATEWAY,
#         )


from django.conf import settings
import requests
import boto3
import json

@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated,IsSubscribed])
def trigger_sync(request):
    """
    Sync portfolio + products + collections to SQLite.
    
    Logic:
    - If settings.ENVIRONMENT == 'development': 
        Calls FastAPI local build endpoint (http://localhost:8001/internal/build).
    - If settings.ENVIRONMENT == 'production': 
        Invokes AWS Lambda 'lambda_sqlite_builder' asynchronously.
    """
    
    user = request.user

    # 1. Authorization check
    if hasattr(user, 'role') and user.role != "vendor":
        return Response(
            {"error": "Only vendors can sync their portfolio."},
            status=status.HTTP_403_FORBIDDEN,
        )

    # 2. Resolve Vendor
    # Note: Adjust logic if your user->vendor relationship is different
    vendor = Vendor.objects.filter(user=user).first()
    if not vendor:
        return Response({"error": "Vendor not found"}, status=status.HTTP_404_NOT_FOUND)

    # 3. Check Subscription / Limits (Preserve existing logic)
    plan = PortfolioService.get_vendor_sync_plan(vendor)

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

    # 4. Trigger Sync based on Environment
    # Default to 'production' if not set
    env = getattr(settings, 'ENVIRONMENT', 'production')
    vendor_slug = vendor.handle

    try:
        if env == 'development':
            # === LOCAL BUILD (via FastAPI) ===
            fastapi_url = getattr(settings, 'FASTAPI_URL', "http://localhost:8001")
            url = f"{fastapi_url}/internal/build"
            
            logger.info(f"Triggering local build for {vendor_slug} at {url}")
            
            # Call FastAPI
            resp = requests.post(
                url, 
                json={"vendor_slug": vendor_slug},
                timeout=5
            )
            resp.raise_for_status()
            
            message = "Local build triggered successfully."
            mode = "local_fastapi"

        else:
            # === AWS LAMBDA BUILD ===
            logger.info(f"Triggering AWS Lambda for {vendor_slug}")
            
            
            # no need to pass aws credentials as iam role is assigned to the ec2 instance 
            client = boto3.client(
                'lambda',
                region_name=settings.AWS_S3_REGION_NAME
            )

            
            payload = {"vendor_slug": vendor_slug}
            
            client.invoke(
                FunctionName='fordgeindia-datasyncer', 
                InvocationType='Event',  # Async execution
                Payload=json.dumps(payload)
            )
            
            message = "Publishing started (AWS Lambda)."
            mode = "aws_lambda"

        # 5. Consume Sync Limit (if successful)
        plan.consume_sync()
        plan.refresh_from_db()

        return Response(
            {
                "status": "success",
                "message": message,
                "mode": mode,
                "remaining_syncs": plan.remaining_syncs,
            }
        )

    except Exception as e:
        logger.exception("trigger_sync failed for vendor %s: %s", vendor.id, e)
        return Response(
            {"detail": f"Sync failed: {str(e)}"},
            status=status.HTTP_502_BAD_GATEWAY,
        )
