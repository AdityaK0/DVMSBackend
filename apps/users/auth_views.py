# views.py
from django.conf import settings
from django.contrib.auth import authenticate
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny,IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from datetime import datetime
from .serializers import *
from .utils import send_telegram_message,generate_otp
from django.contrib.auth import get_user_model
from .serializers import UserSerializer
from apps.vendors.models import Vendor
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from .throttles import LoginRateThrottle
from .telegram_services import TelegramServices


import logging
logger = logging.getLogger(__name__)

User = get_user_model()





@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([LoginRateThrottle])
def user_login_view(request):
    """Traditional username/password login"""
    username = request.data.get('username')
    password = request.data.get('password')
    
    if not username or not password:
        return Response(
            {'error': 'Username and password are required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    user = authenticate(username=username, password=password)
    
    if not user:
        return Response(
            {'error': 'Invalid credentials'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    if not user.is_active:
        return Response(
            {'error': 'User account is disabled'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Generate tokens
    refresh = RefreshToken.for_user(user)
    
    return Response({
        'refresh': str(refresh),
        'access': str(refresh.access_token),
        'user': UserSerializer(user).data
    }, status=status.HTTP_200_OK)


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([LoginRateThrottle])
def request_otp_view(request):
    """Request OTP via Telegram for vendor login"""
    phone_number = request.data.get('phone')
    
    if not phone_number:
        return Response(
            {'error': 'Phone number is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Check if phone number exists in vendor profile
    try:
        vendor = Vendor.objects.get(business_phone=phone_number)
    except Vendor.DoesNotExist:
        return Response(
            {'error': 'Phone number not registered as vendor'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check if vendor has telegram_chat_id
    if not vendor.telegram_chat_id:
        return Response(
            {'error': 'Telegram chat ID not configured. Please contact support.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Use TelegramServices to send OTP
    result = TelegramServices.send_login_otp(phone_number, vendor)
    
    if not result['success']:
        return Response(
            {'error': result['message']},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    return Response({
        'message': result['message'],
        'phone_number': phone_number,
        'expires_in': 300  # seconds
    }, status=status.HTTP_200_OK)



@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([LoginRateThrottle])
def verify_otp_login_view(request):
    """Verify OTP and login"""
    phone_number = request.data.get('phone')
    otp = request.data.get('otp')
    
    if not phone_number or not otp:
        return Response(
            {'error': 'Phone number and OTP are required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Use TelegramServices to verify OTP
    success, message, vendor = TelegramServices.verify_login_otp(phone_number, otp)
    
    if not success:
        status_code = status.HTTP_400_BAD_REQUEST
        if message == 'Invalid OTP':
            status_code = status.HTTP_401_UNAUTHORIZED
        elif message == 'Vendor not found':
            status_code = status.HTTP_404_NOT_FOUND
        
        return Response(
            {'error': message},
            status=status_code
        )
    
    user = vendor.user
    
    if not user.is_active:
        return Response(
            {'error': 'User account is disabled'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Generate tokens
    refresh = RefreshToken.for_user(user)
    
    return Response({
        'refresh': str(refresh),
        'access': str(refresh.access_token),
        'user': UserSerializer(user).data,
        'message': message
    }, status=status.HTTP_200_OK)



# urls.py configuration
"""
from django.urls import path
from . import views

urlpatterns = [
    path('api/login/', views.user_login_view, name='user-login'),
    path('api/login/otp/request/', views.request_otp_view, name='request-otp'),
    path('api/login/otp/verify/', views.verify_otp_login_view, name='verify-otp'),
]
"""

    

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([LoginRateThrottle])
def verify_final_otp_login_view(request):
    phone_number = request.data.get('phone')
    otp = request.data.get('otp')
    
    if not phone_number or not otp:
        return Response(
            {'error': 'Phone number and OTP are required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Use TelegramServices to verify final OTP
    success, message, vendor = TelegramServices.verify_final_otp(phone_number, otp)
    
    if not success:
        status_code = status.HTTP_400_BAD_REQUEST
        if message == 'Invalid OTP':
            status_code = status.HTTP_401_UNAUTHORIZED
        elif message == 'Vendor not found':
            status_code = status.HTTP_404_NOT_FOUND
        
        return Response(
            {'error': message},
            status=status_code
        )
    
    return Response({
        'success': True,
        'message': message,
    }, status=status.HTTP_200_OK)



@api_view(["POST"])
@permission_classes([IsAuthenticated])
def resend_final_otp(request):
    phone = request.data.get("phone")

    if not phone:
        return Response({"error": "Phone number required"}, status=400)

    # Use TelegramServices to resend final OTP
    success, message = TelegramServices.resend_final_otp(phone)
    
    if not success:
        status_code = 404 if message == 'Vendor not found' else 400
        return Response({"error": message}, status=status_code)

    return Response({"success": True, "message": message}, status=200)

