from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes,parser_classes

from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Q
from rest_framework.parsers import MultiPartParser, FormParser
from apps.vendors.models import Vendor
from apps.products.models import Product
from .models import (
    Portfolio, PortfolioCollection, PortfolioTestimonial,
    PortfolioAnalytics
)
from .serializers import (
    PortfolioSerializer, PortfolioCollectionSerializer,
    PortfolioTestimonialSerializer, PortfolioContactInquirySerializer
)
from apps.utils.upload_image import upload_collection_image
from scripts.es.sync_vendor_to_es import sync_vendor
from .service import PortfolioService



# ---- product service currently importing but later on had to go on cache due to public api

from apps.products.service import get_vendor_products_combined,get_filtered_products,get_product_details


# ---------- Public: vendor portfolio summary ----------
# @api_view(['GET'])
# @permission_classes([permissions.AllowAny])
# def public_vendor_portfolio(request, business_name):
#     # vendor = get_object_or_404(Vendor, business_name_slug__iexact=business_name, is_active=True)
#     vendor = (
#     Vendor.objects
#     .select_related('user')      # includes User in same query
#     .prefetch_related('user__addresses')  # fetches Address list in one go
#     .get(business_name_slug__iexact=business_name, is_active=True)
#     )

    
    
#     portfolio = get_object_or_404(Portfolio, vendor=vendor, is_public=True)
    
#     portfolio.view_count = (portfolio.view_count or 0) + 1
#     portfolio.last_viewed = timezone.now()
#     portfolio.save(update_fields=['view_count', 'last_viewed'])

#     today = timezone.now().date()
#     analytics, created = PortfolioAnalytics.objects.get_or_create(
#         portfolio=portfolio, date=today,
#         defaults={'page_views': 1, 'unique_visitors': 1}
#     )
#     if not created:
#         analytics.page_views = (analytics.page_views or 0) + 1
#         analytics.save(update_fields=['page_views'])

#     total_collections = PortfolioCollection.objects.filter(portfolio=portfolio, is_active=True).count()
#     total_testimonials = PortfolioTestimonial.objects.filter(portfolio=portfolio, is_approved=True).count()
#     featured_products = portfolio.get_featured_products()[:8]
#     data = {
#         "id": portfolio.id,
#         "business_name":vendor.business_name,
#         "display_name": portfolio.display_name,
#         "tagline": portfolio.tagline,
#         "slug": portfolio.slug,
#         "about_us": portfolio.about_us,
#         "theme_color": portfolio.theme_color,
#         "accent_color": portfolio.accent_color,
#         "layout_style": portfolio.layout_style,
#         "show_pricing": portfolio.show_pricing,
#         "show_contact_form": portfolio.show_contact_form,
#         "is_public": portfolio.is_public,
#         "view_count": portfolio.view_count,
#         "total_collections": total_collections,
#         "total_testimonials": total_testimonials,
#         "featured_products": PortfolioProductSerializer(featured_products, many=True).data,
#         "banner_image": portfolio.banner_image.url if portfolio.banner_image else None,
#         "logo": portfolio.logo.url if portfolio.logo else None,
#         "gallery_images": portfolio.gallery_images or [], # need implement instead of testimonal
#         "contact_email": vendor.business_email,
#         "contact_phone": vendor.business_phone,
#         "address":AddressSerializer(vendor.user.addresses.all(), many=True).data,
#         "whatsapp_number":vendor.whatsapp_number if vendor.whatsapp_number else None,    
#         "social_links": {
#             "facebook": portfolio.facebook_url,
#             "instagram": portfolio.instagram_url,
#             "twitter": portfolio.twitter_url,
#             "linkedin": portfolio.linkedin_url,
#             "youtube": portfolio.youtube_url,
#         },
#         "featured_products":ProductListSerializer(portfolio.featured_products.all(), many=True).data,
#         "created_at": portfolio.created_at,
#         "updated_at": portfolio.updated_at,
#     }

#     return Response(data, status=status.HTTP_200_OK)



@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def public_vendor_portfolio(request, business_name):
    portfolio_data = PortfolioService.get_public_vendor_portfolio(business_name)
    return Response(portfolio_data, status=status.HTTP_200_OK)

# ---------- Public: product listing / search ----------
@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def public_portfolio_products(request, business_name):
    try:
        vendor = get_object_or_404(Vendor, business_name_slug__iexact=business_name, is_active=True)
    except:
        return Response(
        {"error": "business not found seems like may be url need to observed"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    if not vendor:
        return Response(
        {"error": "May be business name issue Only vendors can access this endpoint"},
        status=status.HTTP_403_FORBIDDEN
    )
    query = request.GET.get("search","").strip()
    page = int(request.GET.get('page', 1))
    page_size = int(request.GET.get('page_size', 10))

    # data = get_vendor_products_data(vendor, request=request, page=page, page_size=page_size)
    data =  get_vendor_products_combined(
            vendor,
            request=request,
            page=page,
            page_size=page_size,
            query=query,
            include_private=False,
        )
            
    return Response(data)



@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def public_portfolio_filter(request,business_name):
    
    try:
        vendor = get_object_or_404(Vendor, business_name_slug__iexact=business_name, is_active=True)
    except:
        return Response(
        {"error": "business not found seems like may be url need to observed"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    if not vendor:
        return Response(
        {"error": "May be business name issue Only vendors can access this endpoint"},
        status=status.HTTP_403_FORBIDDEN
    )
        
        
    data = get_filtered_products(vendor, request.GET, request=request)
    return Response(data)
    
@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def public_portfolio_products_detail(request, business_name,id):
    try:
        try:
            vendor = get_object_or_404(Vendor, business_name_slug__iexact=business_name, is_active=True)
        except:
            return Response(
            {"error": "business not found seems like may be url need to observed"},
                status=status.HTTP_403_FORBIDDEN
            )

        if not vendor:
            return Response(
            {"error": "May be business name issue Only vendors can access this endpoint"},
            status=status.HTTP_403_FORBIDDEN
        )
        product = get_product_details(vendor=vendor,id=id)
        
        return Response(product)





    except Exception as e:
        # Log the full error for debugging

        return Response(
            {"detail": "An unexpected error occurred.", "error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )



@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def public_portfolio_collections(request,business_name):
    try:
        try:
            vendor = get_object_or_404(Vendor, business_name_slug__iexact=business_name, is_active=True)
        except:
            return Response(
            {"error": "business not found seems like may be url need to observed"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if not vendor:
            return Response(
            {"error": "May be business name issue Only vendors can access this endpoint"},
            status=status.HTTP_403_FORBIDDEN
        )

        data = PortfolioService.get_vendor_collections(vendor)
        return Response(data, status=status.HTTP_200_OK)

    except Exception as e:
        # Log the full error for debugging

        return Response(
            {"detail": "An unexpected error occurred.", "error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

        # collection = serializer.save(portfolio=portfolio)

        # # Handle single image upload
        # image_file = request.FILES.get('image')
        # if image_file:
        #     upload_collection_image(collection, image_file)

        # response_serializer = PortfolioCollectionSerializer(collection)
        # return Response(response_serializer.data, status=status.HTTP_201_CREATED)



    


# ---------- Public: contact / inquiry ----------
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def portfolio_contact(request, business_name):
    vendor = get_object_or_404(Vendor, business_name__iexact=business_name, is_active=True)
    portfolio = get_object_or_404(Portfolio, vendor=vendor, is_public=True)

    data = request.data.copy()
    data['portfolio'] = portfolio.id

    product_id = data.get('product_id') or data.get('product')
    if product_id:
        try:
            product = Product.objects.get(id=product_id, vendor=vendor, is_active=True)
            data['product'] = product.id
        except Product.DoesNotExist:
            data['product'] = None

    serializer = PortfolioContactInquirySerializer(data=data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    inquiry = serializer.save(
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT', '')
    )

    try:
        if portfolio.contact_email:
            subject = f"New inquiry for {portfolio.display_name}: {inquiry.subject}"
            message = (
                f"Name: {inquiry.name}\nEmail: {inquiry.email}\nPhone: {inquiry.phone}\n\n"
                f"Message:\n{inquiry.message}\n\n"
                f"Product: {inquiry.product.id if inquiry.product else 'N/A'}"
            )
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [portfolio.contact_email], fail_silently=True)
    except Exception:
        pass

    return Response(PortfolioContactInquirySerializer(inquiry).data, status=status.HTTP_201_CREATED)


# ---------- Vendor: manage portfolio ----------
@api_view(['GET', 'PUT', 'PATCH'])
@permission_classes([permissions.IsAuthenticated])
def vendor_portfolio_manage(request):
    vendor = getattr(request.user, "vendor", None)
    if not vendor:
        return Response({"detail": "Vendor not found."}, status=status.HTTP_404_NOT_FOUND)

    portfolio, _ = Portfolio.objects.get_or_create(  # we can create portfolio when the vendor onboarding is done - BG process ? i don't think so
        vendor=vendor,
        defaults={
            "display_name": vendor.business_name or f"{vendor.pk}-portfolio",
            "slug": vendor.business_name.lower().replace(' ', '-')[:90],
            "business_name_slug":vendor.business_name_slug
        }
    )
    if request.method == 'GET':
        serializer = PortfolioSerializer(portfolio)
        return Response(serializer.data)

    serializer = PortfolioSerializer(portfolio, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def portfolio_collections(request):
    vendor = getattr(request.user, "vendor", None)
    if not vendor:
        return Response({"detail": "Vendor not found."}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        data = get_vendor_collections(vendor)
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
                print(image_file)
                upload_collection_image(collection, image_file)

            response_serializer = PortfolioCollectionSerializer(collection)
            return Response(response_serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        collection.delete()
        return Response({"detail": "collection deleted successfully "}, status=status.HTTP_200_OK)
    
    


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
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

    plan, _ = PortfolioService.create_vendor_sync_plan(vendor)

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

    # ✅ Execute sync
    result = sync_vendor(vendor.id)

    return Response(
        {
            "status": "success",
            "message": "Vendor synced successfully!",
            "synced_docs": result["synced_docs"],
            "remaining_syncs": plan.remaining_syncs,
            "extra_syncs_available": plan.extra_syncs_available,
        }
    )



@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def sync_status(request):
    """
    Returns remaining syncs, used syncs and extra syncs for vendor
    """
    user = request.user

    if user.role != "vendor":
        return Response(
            {"error": "Only vendors can view sync status."},
            status=status.HTTP_403_FORBIDDEN,
        )

    vendor = Vendor.objects.filter(user=user).first()
    if not vendor:
        return Response({"error": "Vendor not found."}, status=status.HTTP_404_NOT_FOUND)

    plan, _ = PortfolioService.create_vendor_sync_plan(vendor)

    return Response(
        {
            "remaining_syncs": plan.remaining_syncs,
            "used_syncs_today": plan.used_syncs_today,
            "allowed_syncs_per_day": plan.allowed_syncs_per_day,
            "extra_syncs_available": plan.extra_syncs_available,
            "last_sync_at": plan.last_sync_at,
        }
    )

# @api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
# @permission_classes([permissions.IsAuthenticated])
# @parser_classes([MultiPartParser, FormParser])
# def portfolio_collection_detail(request, id):
#     """Retrieve, update, or delete a specific collection."""
#     vendor = getattr(request.user, "vendor", None)
#     if not vendor:
#         return Response({"detail": "Vendor not found."}, status=status.HTTP_404_NOT_FOUND)

#     collection = get_object_or_404(PortfolioCollection, id=id, portfolio__vendor=vendor)

#     # GET - single collection detail
#     if request.method == 'GET':
#         serializer = PortfolioCollectionSerializer(collection)
#         return Response(serializer.data)

#     # PUT/PATCH - update collection
#     elif request.method in ['PUT', 'PATCH']:
#         serializer = PortfolioCollectionSerializer(
#             collection,
#             data=request.data,
#             partial=(request.method == 'PATCH')
#         )
#         if serializer.is_valid():
#             serializer.save()
#             return Response(serializer.data)
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

#     # DELETE - delete collection
#     elif request.method == 'DELETE':
#         collection.delete()
#         return Response(status=status.HTTP_204_NO_CONTENT)



# ---------- Vendor: testimonials ----------
@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticated])
def portfolio_testimonials(request):
    vendor = getattr(request.user, "vendor", None)
    if not vendor:
        return Response({"detail": "Vendor not found."}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        testimonials = PortfolioTestimonial.objects.filter(portfolio__vendor=vendor).order_by('order', '-created_at')
        serializer = PortfolioTestimonialSerializer(testimonials, many=True)
        return Response(serializer.data)

    portfolio = get_object_or_404(Portfolio, vendor=vendor)
    serializer = PortfolioTestimonialSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(portfolio=portfolio)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ---------- Vendor: analytics ----------
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def portfolio_analytics(request):
    vendor = getattr(request.user, "vendor", None)
    if not vendor:
        return Response({"detail": "Vendor account required."}, status=status.HTTP_403_FORBIDDEN)

    portfolio = get_object_or_404(Portfolio, vendor=vendor)

    today = timezone.now().date()
    seven_days = [today - timezone.timedelta(days=i) for i in range(0, 7)]
    analytics_qs = PortfolioAnalytics.objects.filter(portfolio=portfolio, date__in=seven_days).order_by('date')

    daily = [
        {"date": a.date, "page_views": a.page_views, "unique_visitors": a.unique_visitors}
        for a in analytics_qs
    ]

    total_views = sum(a.page_views for a in analytics_qs)
    total_unique = sum(a.unique_visitors for a in analytics_qs)

    resp = {
        "portfolio_id": portfolio.id,
        "display_name": portfolio.display_name,
        "daily": daily,
        "total_views_last_7_days": total_views,
        "total_unique_last_7_days": total_unique,
    }
    return Response(resp, status=status.HTTP_200_OK)
