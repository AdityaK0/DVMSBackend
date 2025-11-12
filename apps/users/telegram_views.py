import hmac, hashlib, time, redis, jwt, requests
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from apps.users.models import User
from apps.vendors.models import Vendor
from django.core.cache import cache
from .service import process_telegram_update
from .tasks import process_telegram_celery
from .utils import *
from apps.core.models import BackgroundTask

r = redis.from_url(settings.REDIS_URL)

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



# @api_view(["POST"])
# @permission_classes([AllowAny])
# def telegram_webhook(request):

#     # ✅ verify bot secret
#     header_secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
#     if header_secret != settings.TELEGRAM_WEBHOOK_SECRET:
#         return Response({"error": "forbidden"}, status=403)

#     data = request.data

#     try:
#         # ✅ Send to Celery
#         process_telegram_celery.delay(data)
#     except Exception:
#         # ✅ Celery down? Fallback to direct execution
#         process_telegram_update(data)

#     return Response({"ok": True}) 



@api_view(["POST"])
@permission_classes([AllowAny])
def telegram_webhook(request):
    header_secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if header_secret != settings.TELEGRAM_WEBHOOK_SECRET:
        return Response({"error": "forbidden"}, status=403)

    data = request.data

    # ✅ store event as background task
    task = BackgroundTask.objects.create(
        task_type="TELEGRAM_LINK",
        status=BackgroundTask.Status.PENDING,
        result_data=data,
    )

    try:
        celery_id = process_telegram_celery.delay(task.id, data)
        task.celery_task_id = celery_id
        task.save()
    except:
        # fallback if celery unavailable
        process_telegram_update(data)
        task.status = BackgroundTask.Status.COMPLETED
        task.save()

    return Response({"ok": True})


@api_view(["POST"])
@permission_classes([AllowAny])
def request_otp(request):
    """Send OTP via Telegram"""
    phone = request.data.get("phone")
    user = User.objects.filter(phone=phone).first()
    if not user:
        return Response({"error": "User not found"}, status=404)
    if not user.telegram_chat_id:
        return Response({"error": "Telegram not linked"}, status=400)

    otp = generate_otp()
    store_otp(user.id, otp)
    send_telegram_message(user.telegram_chat_id, f"🔐 Your OTP is: {otp}\nValid for 5 minutes.")
    return Response({"success": True, "message": "OTP sent via Telegram."})


@api_view(["POST"])
@permission_classes([AllowAny])
def verify_otp(request):
    """Verify OTP"""
    phone = request.data.get("phone")
    otp = request.data.get("otp")
    user = User.objects.filter(phone=phone).first()
    if not user:
        return Response({"error": "User not found"}, status=404)

    if verify_otp_in_redis(user.id, otp):
        return Response({"success": True, "message": "OTP verified. Login successful."})
    else:
        return Response({"error": "Invalid or expired OTP."}, status=400)
