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
from .models import  CustomerMessage, Customer, ActivityLog
from .serializers import (
    DashboardStatsSerializer, 
    ActivityLogSerializer,
    CustomerSerializer,
    CustomerMessageSerializer
)
from .service import *
from apps.dashboard.service import get_customer_stats_cached
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Invoice
from .serializers import InvoiceSerializer

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone

def calculate_percentage_change(current, previous):
    """Calculate percentage change between current and previous values"""
    if previous == 0:
        return 100.0 if current > 0 else 0.0
    return round(((current - previous) / previous) * 100, 1)


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
    
    
    customer_stats = get_customer_stats_cached(vendor)
    total_count = customer_stats.get("total_customers")
    active_customers = customer_stats.get("total_active_customers")
    
    # -- below i commented cause this was scanning whole table to get count so took the counts from cache 
    
    # total_count = customers.count() 
    # active_customers = customers.filter(is_active=True).count()

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

    return Response({'product_stats': get_product_stats_cached(vendor)})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def customer_stats(request):
    vendor = getattr(request.user, 'vendor', None)
    if not vendor:
        return Response({'error': 'Vendor not found'}, status=status.HTTP_403_FORBIDDEN)
        
    return Response({'customer_stats': get_customer_stats_cached(vendor)})


# @api_view(['GET'])
# @permission_classes([IsAuthenticated])
# def recent_activities(request):
#     vendor = getattr(request.user, 'vendor', None)
#     if not vendor:
#         return Response({'error': 'Vendor not found'}, status=status.HTTP_403_FORBIDDEN)
        
#     return Response(get_activity_data(vendor))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_summary(request):
    vendor = getattr(request.user, 'vendor', None)
    if not vendor:
        return Response({'error': 'Vendor not found'}, status=status.HTTP_403_FORBIDDEN)
        
    return Response(get_dashboard_summary(vendor))





@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_invoices(request):

    if not hasattr(request.user, "vendor"):
        return Response(
            {"error": "Only vendors can access invoices"},
            status=status.HTTP_403_FORBIDDEN
        )

    vendor = request.user.vendor

    page = int(request.GET.get("page", 1))
    page_size = int(request.GET.get("page_size", 10))
    search = request.GET.get("search", "").strip()
    pending_only = request.GET.get("pending_only", "false") == "true"

    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")

    data = get_vendor_invoices(
        vendor=vendor,
        page=page,
        page_size=page_size,
        search=search,
        pending_only=pending_only,
        start_date=start_date,
        end_date=end_date
    )

    return Response(data)



@api_view(['GET'])
def get_invoice_by_id(request, invoice_id):
    try:
        invoice = Invoice.objects.get(id=invoice_id)
    except Invoice.DoesNotExist:
        return Response({"error": "Invoice not found"}, status=404)

    serializer = InvoiceSerializer(invoice)
    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_invoice(request):

    if not hasattr(request.user, "vendor"):
        return Response(
            {"error": "Only vendors can create invoices"},
            status=status.HTTP_403_FORBIDDEN
        )

    vendor = request.user.vendor
    data = request.data

    serializer = InvoiceSerializer(data=data)

    if serializer.is_valid():
        serializer.save(vendor=vendor)
        return Response(serializer.data, status=201)

    return Response(serializer.errors, status=400)

from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404

from .models import Invoice, InvoiceChangeLog
from .serializers import InvoiceSerializer, InvoiceChangeLogSerializer



@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def update_invoice(request, invoice_id):
    # Ensure vendor user
    if not hasattr(request.user, "vendor"):
        return Response(
            {"error": "Only vendors can update invoices"},
            status=status.HTTP_403_FORBIDDEN,
        )

    vendor = request.user.vendor

    # Vendor-scoped invoice
    invoice = get_object_or_404(Invoice, id=invoice_id, vendor=vendor)

    # Snapshot old data before update
    old_data = InvoiceSerializer(invoice).data

    serializer = InvoiceSerializer(invoice, data=request.data, partial=True)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # Save invoice (mutates `invoice` instance)
    serializer.save()

    # Refresh new data
    new_data = serializer.data

    # Build changes diff
    changes = build_invoice_changes(old_data, new_data)

    # If something actually changed, create log
    if changes:
        InvoiceChangeLog.objects.create(
            invoice=invoice,
            vendor=vendor,
            changed_by=request.user,
            change_type="update",
            changes=changes,
        )

    return Response(new_data, status=status.HTTP_200_OK)




@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_invoice(request, invoice_id):

    if not hasattr(request.user, "vendor"):
        return Response(
            {"error": "Unauthorized"},
            status=status.HTTP_403_FORBIDDEN
        )

    vendor = request.user.vendor

    try:
        invoice = Invoice.objects.get(id=invoice_id, vendor=vendor)
    except Invoice.DoesNotExist:
        return Response({"error": "Invoice not found"}, status=404)

    invoice.delete()
    return Response({"success": "Invoice deleted successfully"})





import csv
from io import TextIOWrapper

@api_view(['POST'])
def upload_invoices_csv(request):
    file = request.FILES.get('file')

    if not file:
        return Response({"error": "No file provided"}, status=400)

    decoded_file = TextIOWrapper(file, encoding='utf-8')
    reader = csv.DictReader(decoded_file)

    created = 0

    for row in reader:
        Invoice.objects.create(
            customer_name=row.get("customer_name"),
            customer_phone=row.get("customer_phone"),
            total_amount=float(row.get("total_amount", 0)),
            paid_amount=float(row.get("paid_amount", 0)),
            pending_amount=float(row.get("pending_amount", 0)),
            is_udhaari=row.get("is_udhaari", "false") == "true",
            invoice_date=row.get("invoice_date"),
            items=[],
        )
        created += 1

    return Response({"message": f"{created} invoices uploaded successfully"})



# dashboard/views.py

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def invoice_history(request, invoice_id):
    if not hasattr(request.user, "vendor"):
        return Response(
            {"error": "Only vendors can view invoice history"},
            status=status.HTTP_403_FORBIDDEN,
        )

    vendor = request.user.vendor

    invoice = get_object_or_404(Invoice, id=invoice_id, vendor=vendor)

    logs = invoice.change_logs.all().order_by("-created_at")

    serializer = InvoiceChangeLogSerializer(logs, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)
