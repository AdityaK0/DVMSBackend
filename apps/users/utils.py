
from django.conf import settings
import jwt
import time
import hmac
import hashlib
import requests
import redis
import secrets
r = redis.from_url(getattr(settings, "REDIS_URL", "redis://localhost:6380/0"))


    
    

def send_telegram_message(chat_id, text):
    """Send a Telegram message with timeout + error logging"""
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": chat_id, "text": text}

    try:
        response = requests.post(url, json=data, timeout=60)  # ⬅️ timeout added
        result = response.json()

        if not result.get("ok"):
            print(f"⚠️ Telegram API error: {result}")
        return result

    except requests.exceptions.Timeout:
        print("⏳ Telegram timeout — message skipped")
        return None

    except Exception as e:
        print(f"❌ Telegram send error: {e}")
        return None    
    
def sign_vendor_token(vendor_id, ttl=600):
    payload = {"vendor_id": vendor_id, "exp": time.time() + ttl}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")

def verify_vendor_token(token):
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        return payload.get("vendor_id")
    except Exception:
        return None

def generate_otp():
    """Generate a cryptographically strong 6-digit OTP.

    Keeps the same return type and length but avoids predictable time-based patterns.
    """
    return f"{secrets.randbelow(10**6):06d}"

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