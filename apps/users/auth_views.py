# views.py
from django.conf import settings
from django.contrib.auth import authenticate
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny,IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
import redis
import random
import requests
from datetime import datetime
from .serializers import *
from .utils import send_telegram_message,generate_otp
from django.contrib.auth import get_user_model
from .serializers import UserSerializer
from apps.vendors.models import Vendor
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from .throttles import LoginRateThrottle


import logging
logger = logging.getLogger(__name__)

User = get_user_model()




r = redis.from_url(settings.REDIS_URL)


import requests
from django.conf import settings



# def send_telegram_message(telegram_chat_id, text):
#     """Send message via Telegram Bot"""
#     url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
#     data = {"telegram_chat_id": telegram_chat_id, "text": text}
#     try:
#         response = requests.post(url, json=data)
#         return response.json()
#     except Exception as e:
#         print(f"Telegram error: {e}")
#         return None

# def send_telegram_message(chat_id, text):
#     """Send message via Telegram Bot"""
#     url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
#     data = {"chat_id": chat_id, "text": text}
#     try:
#         response = requests.post(url, json=data)
#         return response.json()
#     except Exception as e:
#         print(f"Telegram error: {e}")
#         return None



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
    
    # Generate 6-digit OTP
    otp = generate_otp()
    
    # Store OTP in Redis with 5 minute expiry
    redis_key = f"otp:{phone_number}"
    r.setex(redis_key, 300, otp)  # 300 seconds = 5 minutes
    
    # Get vendor details
    user = vendor.user
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    print("came till message send before procees :) ",otp)
    
    # Send OTP via Telegram
    message = f"""🔐 Login OTP Request

Hello {vendor.business_name or user.get_full_name() or user.username}!

Your login OTP is: *{otp}*

📱 Phone: {phone_number}
👤 Username: {user.username}
⏰ Time: {current_time}

⚠️ This OTP will expire in 5 minutes.
Do not share this OTP with anyone.

If you didn't request this, please ignore this message."""
    
    telegram_response = send_telegram_message(vendor.telegram_chat_id, message)
    
    if not telegram_response:
        return Response(
            {'error': 'Failed to send OTP. Please try again.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    return Response({
        'message': 'OTP sent successfully to your Telegram',
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
    
    # Get OTP from Redis
    redis_key = f"otp:{phone_number}"
    stored_otp = r.get(redis_key)
    
    if not stored_otp:
        return Response(
            {'error': 'OTP expired or not found. Please request a new OTP.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Verify OTP
    if stored_otp.decode('utf-8') != otp:
        return Response(
            {'error': 'Invalid OTP'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    # Get vendor and user
    try:
        vendor = Vendor.objects.get(business_phone=phone_number)
        user = vendor.user
    except Vendor.DoesNotExist:
        return Response(
            {'error': 'Vendor not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    if not user.is_active:
        return Response(
            {'error': 'User account is disabled'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Delete OTP from Redis after successful verification
    r.delete(redis_key)
    
    # Generate tokens
    refresh = RefreshToken.for_user(user)
    
    return Response({
        'refresh': str(refresh),
        'access': str(refresh.access_token),
        'user': UserSerializer(user).data,
        'message': 'Login successful'
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
    
    redis_key = f"otp:{phone_number}:final"
    stored_otp = r.get(redis_key)

    if not stored_otp:
        return Response(
            {'error': 'OTP expired or not found. Please request a new OTP.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if stored_otp.decode('utf-8') != otp:
        return Response(
            {'error': 'Invalid OTP'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    # Look up vendor
    try:
        vendor = Vendor.objects.get(business_phone=phone_number)
    except Vendor.DoesNotExist:
        return Response(
            {'error': 'Vendor not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    # Mark verified
    vendor.is_verified = True
    vendor.save()

    # Remove OTP
    r.delete(redis_key)

    return Response({
        'success': True,
        'message': 'Vendor linked successfully',
    }, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def resend_final_otp(request):
    phone = request.data.get("phone")

    if not phone:
        return Response({"error": "Phone number required"}, status=400)

    try:
        vendor = Vendor.objects.get(business_phone=phone)
    except Vendor.DoesNotExist:
        return Response({"error": "Vendor not found"}, status=404)

    # Chat ID required
    if not vendor.telegram_chat_id:
        return Response({"error": "Telegram not linked yet"}, status=400)

    # Generate OTP
    otp = generate_otp()

    redis_key = f"otp:{phone}:final"
    r.setex(redis_key, 300, otp)  # 5 minutes expiry

    # Send OTP to Telegram
    send_telegram_message(vendor.telegram_chat_id, f"Your final verification OTP is: {otp}")

    return Response({"success": True, "message": "Final OTP sent"}, status=200)



# api_view(['POST'])
# @permission_classes([IsAuthenticated])
# def verify_final_otp_login_view(request):
#     phone_number = request.data.get('phone')
#     otp = request.data.get('otp')

#     if not phone_number or not otp:
#         return Response({'error': 'Phone and OTP required'}, status=400)

#     redis_key = f"otp:{phone_number}:final"
#     stored_otp = cache.get(redis_key)

#     if not stored_otp:
#         return Response({'error': 'OTP expired or not found'}, status=400)

#     if stored_otp != otp:
#         return Response({'error': 'Invalid OTP'}, status=401)

#     # Get vendor
#     try:
#         vendor = Vendor.objects.get(business_phone=phone_number)
#     except Vendor.DoesNotExist:
#         return Response({'error': 'Vendor not found'}, status=404)

#     vendor.is_verified = True
#     vendor.save()

#     # Delete OTP
#     cache.delete(redis_key)

#     return Response({
#         "success": True,
#         "message": "Vendor linked successfully",
#         "vendor_id": vendor.id
#     }, status=200)