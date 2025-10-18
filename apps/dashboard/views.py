from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Count
from django.utils import timezone
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from django.core.cache import cache
from apps.products.models import Product
from .models import Event, CustomerMessage, Customer, ActivityLog
from .serializers import (
    DashboardStatsSerializer, 
    ActivityLogSerializer,
    EventSerializer,
    CustomerSerializer,
    CustomerMessageSerializer
)
from .service import *

def calculate_percentage_change(current, previous):
    """Calculate percentage change between current and previous values"""
    if previous == 0:
        return 100.0 if current > 0 else 0.0
    return round(((current - previous) / previous) * 100, 1)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_stats(request):
    """
    Get dashboard statistics for vendor
    
    Returns:
        - total_products: Current count of active products
        - products_change_percentage: % change from last month
        - active_customers: Current count of active customers
        - customers_change_percentage: % change from last month
        - events_this_month: Events created this month
        - events_change: Difference from last month
        - messages_sent: Total messages sent
        - messages_change_percentage: % change from last month
    """
    try:
        vendor = request.user.vendor
    except AttributeError:
        return Response(
            {'error': 'User is not associated with a vendor'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    now = timezone.now()
    last_month = now - relativedelta(months=1)
    current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Total Products
    total_products = Product.objects.filter(
        vendor=vendor, 
        is_active=True,
        is_archived=False
    ).count()
    
    products_last_month = Product.objects.filter(
        vendor=vendor,
        is_active=True,
        is_archived=False,
        created_at__lte=last_month
    ).count()
    
    products_change = calculate_percentage_change(
        total_products, 
        products_last_month
    )

    # Active Customers
    active_customers = Customer.objects.filter(
        vendor=vendor,
        is_active=True
    ).count()
    
    customers_last_month = Customer.objects.filter(
        vendor=vendor,
        is_active=True,
        registered_at__lte=last_month
    ).count()
    
    customers_change = calculate_percentage_change(
        active_customers,
        customers_last_month
    )

    # Events This Month
    events_this_month = Event.objects.filter(
        vendor=vendor,
        created_at__gte=current_month_start,
        is_active=True
    ).count()
    
    last_month_start = (now - relativedelta(months=1)).replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )
    last_month_end = current_month_start - timedelta(seconds=1)
    
    events_last_month = Event.objects.filter(
        vendor=vendor,
        created_at__gte=last_month_start,
        created_at__lte=last_month_end,
        is_active=True
    ).count()
    
    events_change = events_this_month - events_last_month

    # Messages Sent
    messages_sent = CustomerMessage.objects.filter(
        vendor=vendor
    ).count()
    
    messages_last_month = CustomerMessage.objects.filter(
        vendor=vendor,
        sent_at__lte=last_month
    ).count()
    
    messages_change = calculate_percentage_change(
        messages_sent,
        messages_last_month
    )

    stats = {
        'total_products': total_products,
        'products_change_percentage': products_change,
        'active_customers': active_customers,
        'customers_change_percentage': customers_change,
        'events_this_month': events_this_month,
        'events_change': events_change,
        'messages_sent': messages_sent,
        'messages_change_percentage': messages_change,
    }

    serializer = DashboardStatsSerializer(stats)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def recent_activity(request):
    """
    Get recent activities for vendor
    
    Query Parameters:
        - limit (int): Number of activities to return (default: 10)
    
    Returns:
        List of recent activity logs with icon and time_ago
    """
    try:
        vendor = request.user.vendor
    except AttributeError:
        return Response(
            {'error': 'User is not associated with a vendor'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    limit = int(request.query_params.get('limit', 10))
    
    # Validate limit
    if limit < 1 or limit > 100:
        limit = 10
    
    activities = ActivityLog.objects.filter(
        vendor=vendor
    ).select_related('vendor')[:limit]
    
    serializer = ActivityLogSerializer(activities, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_event(request):
    """
    Create a new event
    
    Required fields:
        - name: Event name
        - start_date: Event start datetime
        - end_date: Event end datetime
    
    Optional fields:
        - description: Event description
        - event_type: Type of event
        - status: Event status (default: draft)
    """
    try:
        vendor = request.user.vendor
    except AttributeError:
        return Response(
            {'error': 'User is not associated with a vendor'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    serializer = EventSerializer(data=request.data)
    if serializer.is_valid():
        event = serializer.save(vendor=vendor)
        
        # Log activity
        ActivityLog.objects.create(
            vendor=vendor,
            activity_type='event_created',
            description=f'Event "{event.name}" created',
            metadata={'event_id': event.id, 'event_name': event.name}
        )
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_customer(request):
    """
    Register a new customer for the vendor.
    """
    user = request.user
    vendor = getattr(user, "vendor", None)
    if not vendor:
        return Response(
            {"error": "User is not associated with a vendor"},
            status=status.HTTP_403_FORBIDDEN,
        )

    serializer = CustomerSerializer(data=request.data)
    if serializer.is_valid():
        email = serializer.validated_data.get("email")

        # Check if customer already exists for this vendor
        if Customer.objects.filter(vendor=vendor, email=email).exists():
            return Response(
                {"error": f"Customer with email '{email}' already exists."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        customer = serializer.save(vendor=vendor)

        # Log activity
        ActivityLog.objects.create(
            vendor=vendor,
            activity_type="customer_registered",
            description=f'Customer "{customer.name}" registered',
            metadata={"customer_id": customer.id, "customer_email": customer.email},
        )

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

@api_view(['PATCH', 'PUT'])
@permission_classes([IsAuthenticated])
def update_customer(request, customer_id):
    """
    Update an existing customer for the vendor.

    Allowed fields: name, email, phone, is_active
    """
    user = request.user
    vendor = getattr(user, "vendor", None)
    if not vendor:
        return Response(
            {"error": "User is not associated with a vendor"},
            status=status.HTTP_403_FORBIDDEN,
        )

    try:
        customer = Customer.objects.get(id=customer_id, vendor=vendor)
    except Customer.DoesNotExist:
        return Response(
            {"error": "Customer not found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    serializer = CustomerSerializer(customer, data=request.data, partial=True)
    if serializer.is_valid():
        new_email = serializer.validated_data.get("email")
        if new_email and new_email != customer.email:
            # Check unique constraint per vendor
            if Customer.objects.filter(vendor=vendor, email=new_email).exclude(id=customer.id).exists():
                return Response(
                    {"error": f"Customer with email '{new_email}' already exists."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        updated_customer = serializer.save()

        # Log activity
        ActivityLog.objects.create(
            vendor=vendor,
            activity_type="customer_updated",
            description=f'Customer "{updated_customer.name}" updated',
            metadata={"customer_id": updated_customer.id, "customer_email": updated_customer.email},
        )

        return Response(serializer.data, status=status.HTTP_200_OK)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_customer(request, customer_id):
    """
    Delete a customer for the vendor.
    """
    user = request.user
    vendor = getattr(user, "vendor", None)
    if not vendor:
        return Response(
            {"error": "User is not associated with a vendor"},
            status=status.HTTP_403_FORBIDDEN,
        )

    try:
        customer = Customer.objects.get(id=customer_id, vendor=vendor)
    except Customer.DoesNotExist:
        return Response(
            {"error": "Customer not found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    # Optional: log before deletion
    ActivityLog.objects.create(
        vendor=vendor,
        activity_type="customer_deleted",
        description=f'Customer "{customer.name}" deleted',
        metadata={"customer_id": customer.id, "customer_email": customer.email},
    )

    customer.delete()  # Hard delete
    return Response(
        {"message": f"Customer '{customer.name}' has been deleted."},
        status=status.HTTP_200_OK,
    )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_message(request):
    """
    Send a message/campaign to customers
    
    Required fields:
        - subject: Message subject
        - message: Message content
        - recipient_count: Number of recipients
    
    Optional fields:
        - message_type: Type of message (default: notification)
    """
    try:
        vendor = request.user.vendor
    except AttributeError:
        return Response(
            {'error': 'User is not associated with a vendor'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    serializer = CustomerMessageSerializer(data=request.data)
    if serializer.is_valid():
        message = serializer.save(vendor=vendor)
        
        # Log activity
        ActivityLog.objects.create(
            vendor=vendor,
            activity_type='message_sent',
            description=f'Campaign message sent to {message.recipient_count} customers',
            metadata={
                'message_id': message.id,
                'subject': message.subject,
                'recipient_count': message.recipient_count
            }
        )
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_events(request):
    """
    Get all events for vendor
    
    Query Parameters:
        - status: Filter by status (draft, scheduled, active, completed, cancelled)
        - limit: Number of events to return (default: all)
    """
    try:
        vendor = request.user.vendor
    except AttributeError:
        return Response(
            {'error': 'User is not associated with a vendor'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    events = Event.objects.filter(vendor=vendor)
    
    # Filter by status if provided
    event_status = request.query_params.get('status')
    if event_status:
        events = events.filter(status=event_status)
    
    # Limit results if specified
    limit = request.query_params.get('limit')
    if limit:
        try:
            events = events[:int(limit)]
        except ValueError:
            pass
    
    serializer = EventSerializer(events, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

from django.core.paginator import Paginator
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import Customer
from .serializers import CustomerSerializer


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_customers(request):
    """Get all customers for the current vendor"""
    
    # Ensure user is a vendor
    if not hasattr(request.user, 'vendor'):
        return Response(
            {"error": "Only vendors can access this endpoint"},
            status=status.HTTP_403_FORBIDDEN
        )

    vendor = request.user.vendor
    if not vendor:
        vendor = request.user

    customers = Customer.objects.filter(vendor=vendor).order_by('-created_at')

    # Pagination
    try:
        page = int(request.GET.get('page', 1))
    except (TypeError, ValueError):
        page = 1
        
    try:
        page_size = int(request.GET.get('page_size', 10))
    except (TypeError, ValueError):
        page_size = 10
    paginator = Paginator(customers, page_size)
    page_obj = paginator.get_page(page)

    serializer = CustomerSerializer(
        page_obj.object_list,
        many=True,
        context={'request': request}
    )

    total_count = customers.count()
    active_customers = customers.filter(is_active=True).count()

    return Response({
        'results': serializer.data,
        'count': total_count,
        'active_customers': active_customers,
        'total_pages': paginator.num_pages,
        'current_page': int(page),
        'has_next': page_obj.has_next(),
        'has_previous': page_obj.has_previous(),
    }, status=status.HTTP_200_OK)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_activity(request, activity_id):
    """
    Delete a specific activity log
    
    Path Parameters:
        - activity_id: ID of the activity to delete
    """
    try:
        vendor = request.user.vendor
    except AttributeError:
        return Response(
            {'error': 'User is not associated with a vendor'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        activity = ActivityLog.objects.get(id=activity_id, vendor=vendor)
        activity.delete()
        return Response(
            {'message': 'Activity deleted successfully'},
            status=status.HTTP_204_NO_CONTENT
        )
    except ActivityLog.DoesNotExist:
        return Response(
            {'error': 'Activity not found'},
            status=status.HTTP_404_NOT_FOUND
        )
        
        
 
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def product_stats(request):
    vendor = getattr(request.user, 'vendor', None)
    if not vendor:
        return Response({'error': 'Vendor not found'}, status=status.HTTP_403_FORBIDDEN)

    return Response({'product_stats': get_product_stats(vendor)})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def customer_stats(request):
    vendor = getattr(request.user, 'vendor', None)
    if not vendor:
        return Response({'error': 'Vendor not found'}, status=status.HTTP_403_FORBIDDEN)
        
    return Response({'customer_stats': get_customer_stats(vendor)})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def recent_activities(request):
    vendor = getattr(request.user, 'vendor', None)
    if not vendor:
        return Response({'error': 'Vendor not found'}, status=status.HTTP_403_FORBIDDEN)
        
    return Response(get_activity_data(vendor))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_summary(request):
    vendor = getattr(request.user, 'vendor', None)
    if not vendor:
        return Response({'error': 'Vendor not found'}, status=status.HTTP_403_FORBIDDEN)
        
    return Response(get_dashboard_summary(vendor))