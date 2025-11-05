from rest_framework import generics, permissions
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from .models import Vendor
from rest_framework import generics, status, permissions
from .serializers import VendorSerializer, VendorListSerializer,VendorUpdate
from shared.permissions import IsVendorOrReadOnly
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from apps.users.models import Address
from apps.users.serializers import AddressSerializer


from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError
from apps.utils.upload_image import upload_vendor_logo
from apps.utils.default_creation import create_default_categories_for_vendor
from django.utils.text import slugify
from apps.portfolio.models import PortfolioSyncPlan




class VendorListView(generics.ListAPIView):
    queryset = Vendor.objects.filter(is_active=True)
    serializer_class = VendorListSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['business_name', 'business_description']
    ordering_fields = ['business_name', 'created_at']
    filterset_fields = ['is_verified']

class VendorDetailView(generics.RetrieveAPIView):
    queryset = Vendor.objects.filter(is_active=True)
    serializer_class = VendorSerializer
    permission_classes = [permissions.AllowAny]



# @api_view(['POST'])
# @permission_classes([IsAuthenticated])
# def create_vendor(request):
#     user = request.user
    
#     # Validation checks
#     if user.role == "customer":
#         return Response(
#             {"error": "You already have a customer account. Please create a new account for vendor access."},
#             status=status.HTTP_400_BAD_REQUEST
#         )
    
#     if hasattr(user, "vendor") and user.vendor is not None:
#         return Response(
#             {"error": "Vendor profile already exists for this user."},
#             status=status.HTTP_400_BAD_REQUEST
#         )
    
#     if user.role != "vendor":
#         return Response(
#             {"error": "Only vendor accounts can create a vendor profile."},
#             status=status.HTTP_400_BAD_REQUEST
#         )
    
#     try:
#         # Extract vendor data
#         vendor_data = {
#             'business_name': request.data.get('business_name'),
#             'business_type': request.data.get('business_type'),
#             'business_email': request.data.get('business_email'),
#             'business_description': request.data.get('business_description'),
#             'business_phone': request.data.get('business_phone'),
#             'website': request.data.get('website', ''),
#             'gstin': request.data.get('gstin', ''),
#             'user': user,
#             'is_onboarded': True
#         }
        
#         # Create vendor
#         vendor = Vendor.objects.create(**vendor_data)
        
#         # Extract and create address linked to user
#         address_data = {
#             'street_address': request.data.get('street'),  # Map 'street' to 'street_address'
#             'city': request.data.get('city'),
#             'state': request.data.get('state'),
#             'postal_code': request.data.get('zip_code'),  # Map 'zip_code' to 'postal_code'
#             'zip_code': request.data.get('zip_code'),     # Also keep zip_code field
#             'country': request.data.get('country'),
#             'user': user,  # Link to user, not vendor
#             'address_type': 'both',  # Default address type
#             'is_default': True  # First address is default
#         }
        
#         address = Address.objects.create(**address_data)
        
#         # Serialize response
#         serializer = VendorSerializer(vendor)
#         return Response(serializer.data, status=status.HTTP_201_CREATED)
        
#     except Exception as e:
#         return Response(
#             {"error": str(e)},
#             status=status.HTTP_400_BAD_REQUEST
#         )
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_vendor(request):
    user = request.user

    # Validation checks
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
        # Get existing vendor
        vendor = getattr(user, 'vendor', None)
        if vendor is None:
            # Safety fallback (optional)
            return Response(
                {"error": "Vendor profile not found for this user."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update vendor details from request
        vendor.business_name = request.data.get('business_name', vendor.business_name)
        vendor.business_type = request.data.get('business_type', vendor.business_type)
        vendor.business_email = request.data.get('business_email', vendor.business_email)
        vendor.business_description = request.data.get('business_description', vendor.business_description)
        vendor.business_phone = request.data.get('business_phone', vendor.business_phone)
        vendor.website = request.data.get('website', vendor.website)
        vendor.gstin = request.data.get('gstin', vendor.gstin)
        vendor.is_onboarded = True  # mark as onboarded
        logo_file = request.FILES.get('logo')
        if logo_file:
            upload_vendor_logo(vendor, logo_file)
        vendor.save()

        vendor.business_name_slug = slugify(f"{vendor.business_name}-{vendor.id}")

        # Create or update Address linked to this user
        address, created = Address.objects.get_or_create(
            user=user,
            defaults={
                'street_address': request.data.get('street', ''),
                'city': request.data.get('city', ''),
                'state': request.data.get('state', ''),
                'postal_code': request.data.get('zip_code', ''),
                'zip_code': request.data.get('zip_code', ''),
                'country': request.data.get('country', ''),
                'is_default': True,
                'address_type': 'both'
            }
        )

        if not created:
            # Update existing address if already exists
            address.street_address = request.data.get('street', address.street_address)
            address.city = request.data.get('city', address.city)
            address.state = request.data.get('state', address.state)
            address.postal_code = request.data.get('zip_code', address.postal_code)
            address.zip_code = request.data.get('zip_code', address.zip_code)
            address.country = request.data.get('country', address.country)
            address.is_default = True
            address.address_type = 'both'
            address.save()

        # Serialize response
        serializer = VendorSerializer(vendor)
        create_default_categories_for_vendor(vendor)
        return Response(serializer.data, status=status.HTTP_200_OK)

    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )        
        
@api_view(['GET', 'PUT', 'PATCH'])
@permission_classes([IsAuthenticated, IsVendorOrReadOnly])
def vendor_profile(request, pk=None):
    """
    Single endpoint to retrieve or update vendor profile and address.
    - GET: Returns full vendor profile with address
    - PUT/PATCH: Updates any provided fields (all fields optional)
    """
    try:
        if pk is not None:
            vendor = Vendor.objects.get(id=pk)
        else:
            vendor = Vendor.objects.get(user=request.user)
    except Vendor.DoesNotExist:
        return Response(
            {"detail": "Vendor profile not found."},
            status=status.HTTP_404_NOT_FOUND
        )

    if request.method == 'GET':
        # Use full VendorSerializer for GET requests
        serializer = VendorSerializer(vendor)
        return Response(serializer.data)

    elif request.method in ['PUT', 'PATCH']:
        # Both PUT and PATCH work the same way - update only provided fields
        serializer = VendorUpdate(
            vendor, 
            data=request.data, 
            partial=True,  # Always allow partial updates
            context={'request': request}
        )
        
        if serializer.is_valid():
            updated_vendor = serializer.save()
            
            # Return updated vendor data using full VendorSerializer
            response_serializer = VendorSerializer(updated_vendor)
            return Response(response_serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    



