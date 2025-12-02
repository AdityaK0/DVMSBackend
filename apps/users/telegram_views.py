import hmac, hashlib, time, jwt, requests
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from apps.users.models import User
from apps.vendors.models import Vendor
from django.core.cache import cache
from .telegram_services import TelegramServices
# from .tasks import process_telegram_celery
from .utils import *
from apps.core.models import BackgroundTask


# ---------- Helper functions ----------


# ---------- API endpoints ----------

@api_view(["GET"])
@permission_classes([AllowAny])
def generate_telegram_link(request):
    """Generate Telegram deep link for current vendor."""
    user = request.user
    if not user.is_authenticated:
        return Response({"error": "Login required"}, status=401)
    token = sign_vendor_token(user.id)
    deep_link = f"https://t.me/{settings.TELEGRAM_BOT_USERNAME}?start={token}"
    return Response({"telegram_link": deep_link})




@api_view(["POST"])
@permission_classes([AllowAny])
def telegram_webhook(request):
    header_secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if header_secret != settings.TELEGRAM_WEBHOOK_SECRET:
        return Response({"error": "forbidden"}, status=403)

    data = request.data
    
    TelegramServices.process_telegram_update(data)
    

    return Response({"ok": True})


@api_view(["POST"])
@permission_classes([AllowAny])
def request_otp(request):
    """Send OTP via Telegram for a vendor identified by phone."""
    phone = request.data.get("phone")
    if not phone:
        return Response({"error": "Phone number is required"}, status=400)

    vendor = Vendor.objects.filter(business_phone=phone).select_related("user").first()
    if not vendor:
        return Response({"error": "Vendor not found"}, status=404)

    if  vendor.telegram_chat_id and  vendor.is_verified:
        return Response({"error": "Telegram not linked"}, status=400)

    otp = generate_otp()
    # Reuse existing HMAC-based OTP storage helper, keyed by vendor.id
    
    store_otp(vendor.id, otp)
    send_telegram_message(
        vendor.telegram_chat_id,
        f" Your OTP is: {otp}\nValid for 5 minutes.",
    )
    return Response({"success": True, "message": "OTP sent via Telegram."})


@api_view(["POST"])
@permission_classes([AllowAny])
def verify_otp(request):
    """Verify OTP sent via Telegram for a vendor identified by phone."""
    phone = request.data.get("phone")
    otp = request.data.get("otp")

    if not phone or not otp:
        return Response({"error": "Phone number and OTP are required"}, status=400)

    vendor = Vendor.objects.filter(business_phone=phone).first()
    if not vendor:
        return Response({"error": "Vendor not found"}, status=404)

    if verify_otp_in_redis(vendor.id, otp):
        return Response({"success": True, "message": "OTP verified. Login successful."})
    else:
        return Response({"error": "Invalid or expired OTP."}, status=400)
