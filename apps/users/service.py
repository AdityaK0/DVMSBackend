

from django.core.cache import cache
from apps.vendors.models import Vendor
from .utils import send_telegram_message
from django.conf import settings
import random
import redis
import logging
from .serializers import UserSerializer
from apps.core.cache_decorators import redis_cached

logger = logging.getLogger(__name__)


r = redis.from_url(getattr(settings, "REDIS_URL", "redis://localhost:6380/0"))


RATE_LIMIT_SECONDS = 5
MAX_FAIL_ATTEMPTS = 5
BLOCK_DURATION = 86400


def process_telegram_update(data):
    msg = data.get("message") or {}
    text = (msg.get("text") or "").strip()
    chat_id = msg.get("chat", {}).get("id")
    first_name = msg.get("chat", {}).get("first_name")
    update_id = data.get("update_id")
    if not chat_id:
        return
    
    # Block brute-force if this chat is temporarily blocked
    if cache.get(f"tg_block:{chat_id}"):
        return
    print("Processing chat:", chat_id, "|", text)

    # Prevent duplicate Telegram retry
    if cache.get(f"tg_update:{update_id}"):
        return
    cache.set(f"tg_update:{update_id}", True, timeout=60)
    # print("HOOK CALLED HERE 3")
    
    # Already linked
    vendor = Vendor.objects.filter(telegram_chat_id=chat_id).first()
    if vendor and vendor.is_verified:
        send_telegram_message(chat_id, "✅ The Chat is already linked use another number.")
        return
    elif vendor and not vendor.is_verified:
        send_telegram_message(chat_id, "Account is linked but final OTP is not verified. Please verify OTP.")
        return

    # Validate command
    if not text.lower().startswith("link"):
        send_telegram_message(chat_id, "Format: link <vendor_id> <phone> <secret>")
        return

    parts = text.split()
    if len(parts) != 4:
        send_telegram_message(chat_id, "⚠️ Format: link <vendor_id> <phone> <secret>")
        return

    _, vendor_id, phone, secret = parts

    vendor = Vendor.objects.filter(
        id=vendor_id,
        business_phone=phone,
        secret=secret
    ).first()

    if not vendor:
        fails = cache.get(f"tg_fails:{chat_id}", 0) + 1
        cache.set(f"tg_fails:{chat_id}", fails, timeout=BLOCK_DURATION)

        if fails >= MAX_FAIL_ATTEMPTS:
            cache.set(f"tg_block:{chat_id}", True, timeout=BLOCK_DURATION)
            send_telegram_message(chat_id, "⛔ Too many attempts. Blocked for 24h.")
        else:
            send_telegram_message(chat_id, f"❌ Invalid. Attempts left: {MAX_FAIL_ATTEMPTS - fails}")
        return

    # -----------------------------
    # 🎉 SUCCESS — TELEGRAM LINKED
    # -----------------------------
    vendor.telegram_chat_id = chat_id
    vendor.save()
    cache.delete(f"tg_fails:{chat_id}")

    # send_telegram_message(chat_id, f"Wow {first_name} \nTelegram linked to your account! now need to add the final OTP on integration side")

    # -----------------------------
    # 🔐 SEND FINAL OTP AUTOMATICALLY
    # -----------------------------
    otp = str(random.randint(100000, 999999))
    redis_key = f"otp:{vendor.business_phone}:final"
    r.setex(redis_key, 300, otp)  # 5 minutes expiry

    message = (
        f"🎉 Wow {first_name}!\n\n"
        "Your Telegram has been successfully linked to your account.\n\n"
        f"🔐 To complete the final verification, here is your OTP: *{otp}*\n\n"
        "Please enter this OTP in your dashboard to finish the Telegram integration."
    )
    send_telegram_message(chat_id, message)

from apps.users.models import User

class UserService:
    
    @staticmethod
    @redis_cached("user:context", "user_id", ttl=60 * 15)  # ✅ Standardized key: user:context:{user_id}
    def get_user(user_id):
        """
        Returns complete authenticated user context:
        - user info
        - addresses
        """ 
        user = (
            User.objects
            .select_related("vendor")
            .prefetch_related(
                "addresses",
                "vendor__user__addresses"
            )
            .get(id=user_id)
        )

        data = {
            "user": UserSerializer(user).data,
        }
        return data
