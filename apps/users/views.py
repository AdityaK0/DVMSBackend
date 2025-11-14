from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny,IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from .serializers import (
    UserRegistrationSerializer, UserLoginSerializer, UserProfileUpdateSerializer,
    UserSerializer, AddressSerializer
)
from .models import Address
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from .throttles import LoginRateThrottle
from apps.vendors.serializers import VendorSerializer
from apps.vendors.models import Vendor


import logging
logger = logging.getLogger(__name__)

User = get_user_model()


def generate_otp():
    return str(int(time.time()))[-6:]

class UserRegistrationView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]

class UserLoginView(generics.GenericAPIView):
    serializer_class = UserLoginSerializer
    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle]  
    

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': UserSerializer(user).data
        })

class UserProfileView(generics.RetrieveAPIView):
    # FIXED: Ensure only authenticated users can hit this endpoint
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer
    
    def get_object(self):
        return self.request.user
    
# myapp/views.py

# URL suggests users can update other profiles via PK
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def user_profile_update_fbv(request,pk=None):
    """
    Updates the profile of the currently authenticated user.
    """
    # Retrieve the user instance from the request
    user = request.user
# Line 57: Replace print with logger
# print(request.data)
    logger.debug(f"Profile update request for user {request.user.id}: {request.data}")
    # Pass the instance to the serializer
    # For PATCH requests, pass partial=True to allow partial updates
    serializer = UserProfileUpdateSerializer(
        user,
        data=request.data,
        partial=True if request.method == 'PATCH' else False
    )

    # Validate the data
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    
    # Return errors if validation fails
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AddressListCreateView(generics.ListCreateAPIView):
    serializer_class = AddressSerializer
    
    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class AddressDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = AddressSerializer
    
    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)
    

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout(request):
    try:
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response(
                {"error": "Refresh token is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        token = RefreshToken(refresh_token)
        token.blacklist()  # ✅ only works if blacklist app enabled

        return Response({"message": "Logout successful!"}, status=status.HTTP_200_OK) 
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)



@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me_view(request):
    """
    Returns complete authenticated user context:
    - user info
    - vendor info
    - addresses
    """
    user = request.user

    # Try to fetch vendor
    vendor = Vendor.objects.filter(user=user).first()

    data = {
        "user": UserSerializer(user).data,
        "vendor": None
    }

    if vendor:
        data["vendor"] = VendorSerializer(vendor).data

    return Response(data, status=status.HTTP_200_OK)