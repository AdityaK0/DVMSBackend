# apps/events/views.py
"""
Function-based views for events app (converted from ViewSets).
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import NotFound
from django.utils import timezone
from django.shortcuts import get_object_or_404

from apps.events.models import Event
from apps.events.serializers import (
    EventSerializer, EventCreateSerializer, EventUpdateSerializer,
    FestivalTemplateSerializer, PosterGenerationSerializer, PosterResponseSerializer,
    ProductRecommendationSerializer, CampaignLogSerializer, CampaignLogCreateSerializer,
    AnalyticsSerializer, AnalyticsUpdateSerializer
)
from apps.events.permissions import IsVendor  # keep vendor permission
from apps.events.festivals import get_all_festival_templates, get_festival_template
from apps.events.services.poster_builder import build_and_upload_poster
from apps.events.services.product_recommender import recommend_products, get_product_recommendation_data
from apps.events.services.campaign_logger import log_campaign
from apps.events.services.analytics_service import (
    get_or_create_analytics, get_analytics_summary, update_analytics
)


# ---------------------------------------------------------------------
# Helper: vendor-only base queryset
# ---------------------------------------------------------------------
def _vendor_events_queryset(user):
    """Return events queryset scoped to user's vendor."""
    vendor = getattr(user, "vendor", None)
    if not vendor:
        raise NotFound("Vendor profile not found.")
    return Event.objects.filter(vendor=vendor, is_deleted=False).order_by('-created_at')


# ---------------------------------------------------------------------
# /api/vendor/events/  (GET list, POST create)
# ---------------------------------------------------------------------
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated, IsVendor])
def events_list_create(request):
    """
    GET -> list events for vendor
    POST -> create an event (uses EventCreateSerializer)
    """
    if request.method == 'GET':
        queryset = _vendor_events_queryset(request.user)
        serializer = EventSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # POST -> create
    serializer = EventCreateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    vendor = getattr(request.user, "vendor", None)
    if not vendor:
        raise NotFound("Vendor profile not found.")

    serializer.save(vendor=vendor)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------
# /api/vendor/events/<pk>/  (GET retrieve, PUT update, PATCH partial_update, DELETE soft delete)
# ---------------------------------------------------------------------
@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated, IsVendor])
def event_detail_update_delete(request, pk):
    """
    GET    -> get event details
    PUT    -> full update (EventUpdateSerializer)
    PATCH  -> partial update (EventUpdateSerializer, partial=True)
    DELETE -> soft delete (calls event.soft_delete())
    """
    # fetch event scoped to vendor
    queryset = _vendor_events_queryset(request.user)
    event = get_object_or_404(queryset, pk=pk)

    if request.method == 'GET':
        serializer = EventSerializer(event)
        return Response(serializer.data, status=status.HTTP_200_OK)

    if request.method in ['PUT', 'PATCH']:
        partial = request.method == 'PATCH'
        serializer = EventUpdateSerializer(event, data=request.data, partial=partial)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response(EventSerializer(event).data, status=status.HTTP_200_OK)

    # DELETE -> soft delete
    if request.method == 'DELETE':
        event.soft_delete()
        return Response({"message": "Event deleted successfully."}, status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------
# /api/vendor/events/<pk>/duplicate/  (POST)
# ---------------------------------------------------------------------
@api_view(['POST'])
@permission_classes([IsAuthenticated, IsVendor])
def event_duplicate(request, pk):
    """
    Duplicate an event. Creates a copy with status='draft'.
    """
    queryset = _vendor_events_queryset(request.user)
    event = get_object_or_404(queryset, pk=pk)

    # Create a copy with same fields, set status to draft
    new_event = Event.objects.create(
        vendor=event.vendor,
        name=f"{event.name} (Copy)",
        description=event.description,
        start_date=event.start_date,
        end_date=event.end_date,
        status='draft',
        festival_template_id=event.festival_template_id,
        custom_message=event.custom_message,
        selected_products=event.selected_products.copy() if event.selected_products else []
    )

    serializer = EventSerializer(new_event)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------
# /api/vendor/events/<pk>/publish/  (POST)
# ---------------------------------------------------------------------
@api_view(['POST'])
@permission_classes([IsAuthenticated, IsVendor])
def event_publish(request, pk):
    """
    Publish an event:
    - Validate event has a title
    - Set status = 'active'
    - If start_date > now(), set start_date = now()
    - Create analytics entry for today
    """
    queryset = _vendor_events_queryset(request.user)
    event = get_object_or_404(queryset, pk=pk)

    if not event.name:
        return Response({"error": "Event must have a name to be published."},
                        status=status.HTTP_400_BAD_REQUEST)

    event.status = 'active'
    if event.start_date and event.start_date > timezone.now():
        event.start_date = timezone.now()
    event.save()

    # create analytics entry for today
    get_or_create_analytics(event)

    serializer = EventSerializer(event)
    return Response({
        "message": "Event published successfully.",
        "event": serializer.data
    }, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------
# /api/vendor/events/<pk>/poster/generate/  (POST)
# ---------------------------------------------------------------------
@api_view(['POST'])
@permission_classes([IsAuthenticated, IsVendor])
def event_generate_poster(request, pk):
    """
    Generate poster for an event using PosterGenerationSerializer.
    Expects: {"template_id": "diwali", "selected_products":[..], "custom_message": "..." }
    """
    queryset = _vendor_events_queryset(request.user)
    event = get_object_or_404(queryset, pk=pk)

    serializer = PosterGenerationSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    template_id = serializer.validated_data['template_id']
    selected_products = serializer.validated_data['selected_products']
    custom_message = serializer.validated_data.get('custom_message', '')

    festival_template = get_festival_template(template_id)
    if not festival_template:
        return Response({"error": f"Festival template '{template_id}' not found."},
                        status=status.HTTP_404_NOT_FOUND)

    if custom_message:
        event.custom_message = custom_message
        event.save(update_fields=['custom_message'])

    try:
        poster_url = build_and_upload_poster(
            event=event,
            festival_template=festival_template,
            selected_product_ids=selected_products
        )

        event.poster_url = poster_url
        event.festival_template_id = template_id
        if selected_products:
            event.selected_products = selected_products
        event.save(update_fields=['poster_url', 'festival_template_id', 'selected_products'])

        response_serializer = PosterResponseSerializer({'poster_url': poster_url})
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({"error": f"Failed to generate poster: {str(e)}"},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ---------------------------------------------------------------------
# /api/vendor/events/<pk>/campaign/send/  (POST)
# ---------------------------------------------------------------------
@api_view(['POST'])
@permission_classes([IsAuthenticated, IsVendor])
def event_campaign_send(request, pk):
    """
    Log a WhatsApp campaign (backend only logs; frontend opens wa.me link).
    """
    queryset = _vendor_events_queryset(request.user)
    event = get_object_or_404(queryset, pk=pk)

    serializer = CampaignLogCreateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        campaign_log = log_campaign(
            event=event,
            message_text=serializer.validated_data['message_text'],
            poster_url=serializer.validated_data.get('poster_url', ''),
            sent_to_phone=serializer.validated_data['sent_to_phone'],
            status=serializer.validated_data.get('status', 'sent')
        )
        response_serializer = CampaignLogSerializer(campaign_log)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response({"error": f"Failed to log campaign: {str(e)}"},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ---------------------------------------------------------------------
# /api/vendor/events/<pk>/analytics/  (GET)
# ---------------------------------------------------------------------
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsVendor])
def event_analytics(request, pk):
    """
    Return analytics summary (with optional ?days=30).
    """
    queryset = _vendor_events_queryset(request.user)
    event = get_object_or_404(queryset, pk=pk)

    days = int(request.query_params.get('days', 30))
    summary = get_analytics_summary(event, days=days)
    return Response(summary, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------
# /api/vendor/events/<pk>/analytics/update/  (POST)
# ---------------------------------------------------------------------
@api_view(['POST'])
@permission_classes([IsAuthenticated, IsVendor])
def event_analytics_update(request, pk):
    """
    Update analytics for an event using AnalyticsUpdateSerializer.
    Expected payload keys: date, views, clicks, shares, leads
    """
    queryset = _vendor_events_queryset(request.user)
    event = get_object_or_404(queryset, pk=pk)

    serializer = AnalyticsUpdateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        update_analytics(
            event=event,
            analytics_date=serializer.validated_data['date'],
            views=serializer.validated_data.get('views', 0),
            clicks=serializer.validated_data.get('clicks', 0),
            shares=serializer.validated_data.get('shares', 0),
            leads=serializer.validated_data.get('leads', 0)
        )
        return Response({"message": "Analytics updated successfully."}, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({"error": f"Failed to update analytics: {str(e)}"},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ---------------------------------------------------------------------
# /api/vendor/events/festivals/  (GET)
# ---------------------------------------------------------------------
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsVendor])
def festival_templates_list(request):
    """
    Return all festival templates (static data).
    """
    templates = get_all_festival_templates()
    serializer = FestivalTemplateSerializer(templates, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------
# /api/vendor/events/recommend-products/  (GET)
# ---------------------------------------------------------------------
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsVendor])
def product_recommendations_list(request):
    """
    Get recommended products for vendor.
    Query param: ?limit=10
    Priority logic kept inside recommend_products service.
    """
    vendor = getattr(request.user, "vendor", None)
    if not vendor:
        return Response({"error": "Vendor profile not found."}, status=status.HTTP_404_NOT_FOUND)

    try:
        limit = int(request.query_params.get('limit', 10))
    except (ValueError, TypeError):
        limit = 10

    products = recommend_products(vendor, limit=limit)
    product_data = get_product_recommendation_data(products)
    serializer = ProductRecommendationSerializer(product_data, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


# """
# Views for events app.
# """
# from rest_framework import viewsets, status
# from rest_framework.decorators import action
# from rest_framework.response import Response
# from rest_framework.permissions import IsAuthenticated
# from django.utils import timezone
# from django.shortcuts import get_object_or_404

# from apps.events.models import Event, CampaignLog, EventAnalytics
# from apps.events.serializers import (
#     EventSerializer, EventCreateSerializer, EventUpdateSerializer,
#     FestivalTemplateSerializer, PosterGenerationSerializer, PosterResponseSerializer,
#     ProductRecommendationSerializer, CampaignLogSerializer, CampaignLogCreateSerializer,
#     AnalyticsSerializer, AnalyticsUpdateSerializer
# )
# from apps.events.permissions import IsVendor, IsVendorOwner
# from apps.events.festivals import get_all_festival_templates, get_festival_template
# from apps.events.services.poster_builder import build_and_upload_poster
# from apps.events.services.product_recommender import recommend_products, get_product_recommendation_data
# from apps.events.services.campaign_logger import log_campaign
# from apps.events.services.analytics_service import (
#     get_or_create_analytics, get_analytics_summary, update_analytics
# )


# class EventViewSet(viewsets.ModelViewSet):
#     """
#     ViewSet for Event CRUD operations.
    
#     Endpoints:
#     - GET /api/vendor/events/ - List all events for vendor
#     - POST /api/vendor/events/ - Create new event
#     - GET /api/vendor/events/{id}/ - Get event details
#     - PUT /api/vendor/events/{id}/ - Update event
#     - PATCH /api/vendor/events/{id}/ - Partial update event
#     - DELETE /api/vendor/events/{id}/ - Soft delete event
#     - POST /api/vendor/events/{id}/duplicate/ - Duplicate event
#     - POST /api/vendor/events/{id}/publish/ - Publish event
#     - POST /api/vendor/events/{id}/poster/generate/ - Generate poster
#     - POST /api/vendor/events/{id}/campaign/send/ - Log campaign
#     - GET /api/vendor/events/{id}/analytics/ - Get analytics
#     - POST /api/vendor/events/{id}/analytics/update/ - Update analytics
#     """
#     permission_classes = [IsAuthenticated, IsVendor]
    
#     def get_queryset(self):
#         """Return events for the current vendor only"""
#         vendor = self.request.user.vendor
#         return Event.objects.filter(
#             vendor=vendor,
#             is_deleted=False
#         ).order_by('-created_at')
    
#     def get_serializer_class(self):
#         """Return appropriate serializer based on action"""
#         if self.action == 'create':
#             return EventCreateSerializer
#         elif self.action in ['update', 'partial_update']:
#             return EventUpdateSerializer
#         return EventSerializer
    
#     def perform_create(self, serializer):
#         """Set vendor from request.user"""
#         vendor = self.request.user.vendor
#         if not vendor:
#             from rest_framework.exceptions import NotFound
#             raise NotFound("Vendor profile not found.")
#         serializer.save(vendor=vendor)
    
#     def destroy(self, request, *args, **kwargs):
#         """Soft delete event"""
#         event = self.get_object()
#         event.soft_delete()
#         return Response(
#             {"message": "Event deleted successfully."},
#             status=status.HTTP_204_NO_CONTENT
#         )
    
#     @action(detail=True, methods=['post'])
#     def duplicate(self, request, pk=None):
#         """
#         Duplicate an event.
#         POST /api/vendor/events/{id}/duplicate/
#         """
#         event = self.get_object()
        
#         # Create a copy
#         new_event = Event.objects.create(
#             vendor=event.vendor,
#             title=f"{event.title} (Copy)",
#             description=event.description,
#             start_date=event.start_date,
#             end_date=event.end_date,
#             status='draft',  # Always set to draft for duplicates
#             festival_template_id=event.festival_template_id,
#             custom_message=event.custom_message,
#             selected_products=event.selected_products.copy() if event.selected_products else []
#         )
        
#         serializer = EventSerializer(new_event)
#         return Response(serializer.data, status=status.HTTP_201_CREATED)
    
#     @action(detail=True, methods=['post'])
#     def publish(self, request, pk=None):
#         """
#         Publish an event.
#         POST /api/vendor/events/{id}/publish/
        
#         Process:
#         - Validate event is complete
#         - Set status = active
#         - Update start_date = now() if not already started
#         - Create analytics entry for today
#         """
#         event = self.get_object()
        
#         # Validate event is complete
#         if not event.title:
#             return Response(
#                 {"error": "Event must have a title to be published."},
#                 status=status.HTTP_400_BAD_REQUEST
#             )
        
#         # Set status to active
#         event.status = 'active'
        
#         # Update start_date to now if event hasn't started yet
#         if event.start_date > timezone.now():
#             event.start_date = timezone.now()
        
#         event.save()
        
#         # Create analytics entry for today
#         get_or_create_analytics(event)
        
#         serializer = EventSerializer(event)
#         return Response(
#             {
#                 "message": "Event published successfully.",
#                 "event": serializer.data
#             },
#             status=status.HTTP_200_OK
#         )
    
#     @action(detail=True, methods=['post'])
#     def generate_poster(self, request, pk=None):
#         """
#         Generate poster for an event.
#         POST /api/vendor/events/{id}/poster/generate/
        
#         Input:
#         {
#             "template_id": "diwali",
#             "selected_products": [22, 18, 21],
#             "custom_message": "Flat 40% off!"
#         }
#         """
#         event = self.get_object()
        
#         serializer = PosterGenerationSerializer(data=request.data)
#         if not serializer.is_valid():
#             return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
#         template_id = serializer.validated_data['template_id']
#         selected_products = serializer.validated_data['selected_products']
#         custom_message = serializer.validated_data.get('custom_message', '')
        
#         # Get festival template
#         festival_template = get_festival_template(template_id)
#         if not festival_template:
#             return Response(
#                 {"error": f"Festival template '{template_id}' not found."},
#                 status=status.HTTP_404_NOT_FOUND
#             )
        
#         # Update event with custom message if provided
#         if custom_message:
#             event.custom_message = custom_message
#             event.save(update_fields=['custom_message'])
        
#         try:
#             # Build and upload poster
#             poster_url = build_and_upload_poster(
#                 event=event,
#                 festival_template=festival_template,
#                 selected_product_ids=selected_products
#             )
            
#             # Update event with poster URL and template
#             event.poster_url = poster_url
#             event.festival_template_id = template_id
#             if selected_products:
#                 event.selected_products = selected_products
#             event.save(update_fields=['poster_url', 'festival_template_id', 'selected_products'])
            
#             response_serializer = PosterResponseSerializer({'poster_url': poster_url})
#             return Response(response_serializer.data, status=status.HTTP_200_OK)
        
#         except Exception as e:
#             return Response(
#                 {"error": f"Failed to generate poster: {str(e)}"},
#                 status=status.HTTP_500_INTERNAL_SERVER_ERROR
#             )
    
#     @action(detail=True, methods=['post'])
#     def campaign_send(self, request, pk=None):
#         """
#         Log a WhatsApp campaign (does not send messages).
#         POST /api/vendor/events/{id}/campaign/send/
        
#         Frontend will open: https://wa.me/{phone}?text={encoded_msg}
#         Backend only logs the campaign.
#         """
#         event = self.get_object()
        
#         serializer = CampaignLogCreateSerializer(data=request.data)
#         if not serializer.is_valid():
#             return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
#         try:
#             campaign_log = log_campaign(
#                 event=event,
#                 message_text=serializer.validated_data['message_text'],
#                 poster_url=serializer.validated_data.get('poster_url', ''),
#                 sent_to_phone=serializer.validated_data['sent_to_phone'],
#                 status=serializer.validated_data.get('status', 'sent')
#             )
            
#             response_serializer = CampaignLogSerializer(campaign_log)
#             return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        
#         except Exception as e:
#             return Response(
#                 {"error": f"Failed to log campaign: {str(e)}"},
#                 status=status.HTTP_500_INTERNAL_SERVER_ERROR
#             )
    
#     @action(detail=True, methods=['get'])
#     def analytics(self, request, pk=None):
#         """
#         Get analytics for an event.
#         GET /api/vendor/events/{id}/analytics/
        
#         Returns analytics summary with daily breakdown.
#         """
#         event = self.get_object()
        
#         # Get days parameter (default 30)
#         days = int(request.query_params.get('days', 30))
        
#         # Get analytics summary
#         summary = get_analytics_summary(event, days=days)
        
#         return Response(summary, status=status.HTTP_200_OK)
    
#     @action(detail=True, methods=['post'])
#     def analytics_update(self, request, pk=None):
#         """
#         Update analytics for an event.
#         POST /api/vendor/events/{id}/analytics/update/
        
#         Frontend sends analytics events:
#         - user clicked WhatsApp
#         - user downloaded poster
#         - user viewed event page
#         etc.
#         """
#         event = self.get_object()
        
#         serializer = AnalyticsUpdateSerializer(data=request.data)
#         if not serializer.is_valid():
#             return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
#         try:
#             update_analytics(
#                 event=event,
#                 analytics_date=serializer.validated_data['date'],
#                 views=serializer.validated_data.get('views', 0),
#                 clicks=serializer.validated_data.get('clicks', 0),
#                 shares=serializer.validated_data.get('shares', 0),
#                 leads=serializer.validated_data.get('leads', 0)
#             )
            
#             return Response(
#                 {"message": "Analytics updated successfully."},
#                 status=status.HTTP_200_OK
#             )
        
#         except Exception as e:
#             return Response(
#                 {"error": f"Failed to update analytics: {str(e)}"},
#                 status=status.HTTP_500_INTERNAL_SERVER_ERROR
#             )


# class FestivalTemplateViewSet(viewsets.ViewSet):
#     """
#     ViewSet for festival templates (static data).
    
#     Endpoint:
#     - GET /api/vendor/events/festivals/ - List all festival templates
#     """
#     permission_classes = [IsAuthenticated, IsVendor]
    
#     def list(self, request):
#         """Return all festival templates"""
#         templates = get_all_festival_templates()
#         serializer = FestivalTemplateSerializer(templates, many=True)
#         return Response(serializer.data, status=status.HTTP_200_OK)


# class ProductRecommendationViewSet(viewsets.ViewSet):
#     """
#     ViewSet for product recommendations.
    
#     Endpoint:
#     - GET /api/vendor/events/recommend-products/ - Get recommended products
#     """
#     permission_classes = [IsAuthenticated, IsVendor]
    
#     def list(self, request):
#         """
#         Get recommended products for vendor.
        
#         Logic priority:
#         1. Featured products
#         2. Most viewed
#         3. Highest stock
#         4. Random active products
#         """
#         vendor = request.user.vendor
#         if not vendor:
#             return Response(
#                 {"error": "Vendor profile not found."},
#                 status=status.HTTP_404_NOT_FOUND
#             )
        
#         # Get limit from query params (default 10)
#         limit = int(request.query_params.get('limit', 10))
        
#         # Get recommended products
#         products = recommend_products(vendor, limit=limit)
        
#         # Convert to recommendation data format
#         product_data = get_product_recommendation_data(products)
        
#         serializer = ProductRecommendationSerializer(product_data, many=True)
#         return Response(serializer.data, status=status.HTTP_200_OK)
