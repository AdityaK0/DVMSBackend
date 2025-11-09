import hmac, hashlib, time, redis, jwt, requests
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from apps.users.models import User

r = redis.from_url(settings.REDIS_URL)

# ---------- Helper functions ----------

def sign_vendor_token(vendor_id, ttl=600):
    payload = {"vendor_id": vendor_id, "exp": time.time() + ttl}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")

def verify_vendor_token(token):
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        return payload.get("vendor_id")
    except Exception:
        return None

def send_telegram_message(chat_id, text):
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": chat_id, "text": text}
    requests.post(url, json=data)

def generate_otp():
    return str(int(time.time()))[-6:]  # simple 6-digit OTP

def store_otp(vendor_id, otp, ttl=300):
    h = hmac.new(settings.JWT_SECRET.encode(), otp.encode(), hashlib.sha256).hexdigest()
    r.setex(f"otp:{vendor_id}", ttl, h)

def verify_otp_in_redis(vendor_id, otp):
    h = r.get(f"otp:{vendor_id}")
    if not h:
        return False
    expected = hmac.new(settings.JWT_SECRET.encode(), otp.encode(), hashlib.sha256).hexdigest()
    if h.decode() == expected:
        r.delete(f"otp:{vendor_id}")
        return True
    return False

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
    """Webhook for Telegram messages"""
    data = request.data
    msg = data.get("message") or {}
    text = msg.get("text", "")
    chat = msg.get("chat", {})
    chat_id = chat.get("id")

    if text.startswith("/start"):
        parts = text.split()
        if len(parts) == 2:
            token = parts[1]
            vendor_id = verify_vendor_token(token)
            if vendor_id:
                user = User.objects.filter(id=vendor_id).first()
                if user:
                    user.telegram_chat_id = chat_id
                    user.save()
                    send_telegram_message(chat_id, "✅ Telegram successfully linked to your account!")
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
