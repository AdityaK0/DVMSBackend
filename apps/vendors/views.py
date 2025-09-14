from rest_framework import generics, permissions
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from .models import Vendor
from rest_framework import generics, status, permissions
from .serializers import VendorSerializer, VendorListSerializer
from shared.permissions import IsVendorOrReadOnly
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes


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

class VendorCreateView(generics.CreateAPIView):
    queryset = Vendor.objects.all()
    serializer_class = VendorSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        user = self.request.user

        # Prevent customers from becoming vendors
        if user.role == "customer":
            raise ValidationError("You already have a customer account. Please create a new account for vendor access.")

        # Prevent vendor from creating duplicate vendor profile
        if hasattr(user, "vendor") and user.vendor is not None:
            raise ValidationError("Vendor profile already exists for this user.")

        # Only allow if role is vendor
        if user.role != "vendor":
            raise ValidationError("Only vendor accounts can create a vendor profile.")

        serializer.save(user=user,is_onboarded=True)

@api_view(['GET', 'PUT', 'PATCH'])
@permission_classes([IsVendorOrReadOnly])
def vendor_profile(request, pk=None):
    """
    Retrieve or update the vendor profile.
    - If `id` is provided, update that vendor (admin/dashboard).
    - Otherwise, update the profile of the logged-in user.
    """
    try:
        if id is not None:
            vendor = Vendor.objects.get(id=pk)
        else:
            vendor = Vendor.objects.get(user=request.user)
    except Vendor.DoesNotExist:
        return Response(
            {"detail": "Vendor profile not found."},
            status=status.HTTP_404_NOT_FOUND
        )

    if request.method == 'GET':
        serializer = VendorSerializer(vendor)
        return Response(serializer.data)

    elif request.method in ['PUT', 'PATCH']:
        partial = request.method == 'PATCH'
        serializer = VendorSerializer(vendor, data=request.data, partial=partial)
        print("Request DATA :: ",request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)