"""
Telegram and OTP service layer for vendor authentication.

This module encapsulates all Telegram-related business logic and auth/OTP cache operations.
It provides two main classes:
- AuthCache: Handles all Redis and Django cache operations for OTP and rate limiting
- TelegramServices: Contains business logic for Telegram webhook processing and OTP flows
"""

import random
import logging
import redis
from django.conf import settings
from django.core.cache import cache
from apps.vendors.models import Vendor
from .utils import send_telegram_message, generate_otp
from apps.core.events import VendorUpdated
logger = logging.getLogger(__name__)

# Constants for rate limiting and blocking
RATE_LIMIT_SECONDS = 5
MAX_FAIL_ATTEMPTS = 5
BLOCK_DURATION = 86400  # 24 hours in seconds


class AuthCache:
    """
    Encapsulates all auth/OTP-related cache and Redis operations.
    
    Uses Redis for OTP storage (with TTL) and Django's cache backend 
    (LocMemCache) for rate limiting, blocking, and duplicate update prevention.
    
    Key naming conventions:
    - Redis: otp:{phone}, otp:{phone}:final
    - Django cache: tg_block:{chat_id}, tg_fails:{chat_id}, tg_update:{update_id}
    """
    
    def __init__(self):
        """Initialize Redis client using the same pattern as existing code."""
        self.r = redis.from_url(getattr(settings, "REDIS_URL", "redis://localhost:6380/0"))
    
    # ==================== Login OTP Methods ====================
    
    def set_login_otp(self, phone: str, otp: str, ttl: int = 300) -> None:
        """
        Store login OTP in Redis.
        
        Args:
            phone: Vendor's business phone number
            otp: 6-digit OTP code
            ttl: Time-to-live in seconds (default: 300 = 5 minutes)
        """
        key = f"otp:{phone}"
        self.r.setex(key, ttl, otp)
    
    def get_login_otp(self, phone: str) -> str | None:
        """
        Retrieve login OTP from Redis.
        
        Args:
            phone: Vendor's business phone number
            
        Returns:
            OTP string if found, None otherwise
        """
        key = f"otp:{phone}"
        otp = self.r.get(key)
        return otp.decode('utf-8') if otp else None
    
    def delete_login_otp(self, phone: str) -> None:
        """
        Delete login OTP from Redis.
        
        Args:
            phone: Vendor's business phone number
        """
        key = f"otp:{phone}"
        self.r.delete(key)
    
    # ==================== Final OTP Methods ====================
    
    def set_final_otp(self, phone: str, otp: str, ttl: int = 300) -> None:
        """
        Store final verification OTP in Redis.
        
        Args:
            phone: Vendor's business phone number
            otp: 6-digit OTP code
            ttl: Time-to-live in seconds (default: 300 = 5 minutes)
        """
        key = f"otp:{phone}:final"
        self.r.setex(key, ttl, otp)
    
    def get_final_otp(self, phone: str) -> str | None:
        """
        Retrieve final verification OTP from Redis.
        
        Args:
            phone: Vendor's business phone number
            
        Returns:
            OTP string if found, None otherwise
        """
        key = f"otp:{phone}:final"
        otp = self.r.get(key)
        return otp.decode('utf-8') if otp else None
    
    def delete_final_otp(self, phone: str) -> None:
        """
        Delete final verification OTP from Redis.
        
        Args:
            phone: Vendor's business phone number
        """
        key = f"otp:{phone}:final"
        self.r.delete(key)
    
    # ==================== Rate Limiting & Blocking Methods ====================
    # These use Django's cache (LocMemCache) for in-memory tracking
    
    def increment_fail_attempts(self, chat_id: int, ttl: int = BLOCK_DURATION) -> int:
        """
        Increment failed login attempts for a chat ID.
        
        Args:
            chat_id: Telegram chat ID
            ttl: Time-to-live for the counter (default: 24 hours)
            
        Returns:
            New fail count
        """
        key = f"tg_fails:{chat_id}"
        fails = cache.get(key, 0) + 1
        cache.set(key, fails, timeout=ttl)
        return fails
    
    def clear_fail_attempts(self, chat_id: int) -> None:
        """
        Clear failed login attempts for a chat ID.
        
        Args:
            chat_id: Telegram chat ID
        """
        key = f"tg_fails:{chat_id}"
        cache.delete(key)
    
    def is_blocked(self, chat_id: int) -> bool:
        """
        Check if a chat ID is temporarily blocked.
        
        Args:
            chat_id: Telegram chat ID
            
        Returns:
            True if blocked, False otherwise
        """
        key = f"tg_block:{chat_id}"
        return bool(cache.get(key))
    
    def block_chat(self, chat_id: int, ttl: int = BLOCK_DURATION) -> None:
        """
        Block a chat ID temporarily.
        
        Args:
            chat_id: Telegram chat ID
            ttl: Block duration in seconds (default: 24 hours)
        """
        key = f"tg_block:{chat_id}"
        cache.set(key, True, timeout=ttl)
    
    # ==================== Duplicate Update Prevention ====================
    
    def has_processed_update(self, update_id: int) -> bool:
        """
        Check if a Telegram update has already been processed.
        
        Args:
            update_id: Telegram update ID
            
        Returns:
            True if already processed, False otherwise
        """
        key = f"tg_update:{update_id}"
        return bool(cache.get(key))
    
    def mark_update_processed(self, update_id: int, ttl: int = 60) -> None:
        """
        Mark a Telegram update as processed to prevent duplicate handling.
        
        Args:
            update_id: Telegram update ID
            ttl: Time-to-live in seconds (default: 60)
        """
        key = f"tg_update:{update_id}"
        cache.set(key, True, timeout=ttl)


class TelegramServices:
    """
    Business logic for Telegram webhook processing and OTP flows.
    
    Handles:
    - Telegram webhook updates (link command processing)
    - Login OTP generation and verification
    - Final OTP generation and verification
    - Rate limiting and brute-force protection
    """
    
    auth_cache = AuthCache()
    
    @classmethod
    def process_telegram_update(cls, data: dict) -> None:

        """
        Process incoming Telegram webhook update.
        
        Handles the 'link <vendor_id> <phone> <secret>' command to link
        a vendor's Telegram account and automatically send final verification OTP.
        
        Args:
            data: Telegram update payload
        """
        msg = data.get("message") or {}
        text = (msg.get("text") or "").strip()
        chat_id = msg.get("chat", {}).get("id")
        first_name = msg.get("chat", {}).get("first_name")
        update_id = data.get("update_id")
        
        if not chat_id:
            return
        
        # Block brute-force if this chat is temporarily blocked
        if cls.auth_cache.is_blocked(chat_id):
            return
        
        print("Processing chat:", chat_id, "|", text)
        
        # Prevent duplicate Telegram retry
        if cls.auth_cache.has_processed_update(update_id):
            return
        cls.auth_cache.mark_update_processed(update_id)
        
        # Check if already linked
        vendor = Vendor.objects.filter(telegram_chat_id=chat_id).first()
        if vendor and vendor.is_verified:
            send_telegram_message(chat_id, "✅ The Chat is already linked use another number.")
            return
        elif vendor and not vendor.is_verified and not vendor.telegram_chat_id:
            send_telegram_message(chat_id, "Account is linked but final OTP is not verified. Please verify OTP :)(: .")
            return
        
        # Validate command format
        if not text.lower().startswith("link"):
            send_telegram_message(chat_id, "Format: link <vendor_id> <phone> <secret>")
            return
        
        parts = text.split()
        if len(parts) != 4:
            send_telegram_message(chat_id, "⚠️ Format: link <vendor_id> <phone> <secret>")
            return
        
        _, vendor_id, phone, secret = parts
        
        # Verify vendor credentials
        vendor = Vendor.objects.filter(
            id=vendor_id,
            business_phone=phone,
            secret=secret
        ).first()
        
        if not vendor:
            # Increment fail attempts and check if should block
            fails = cls.auth_cache.increment_fail_attempts(chat_id)
            
            if fails >= MAX_FAIL_ATTEMPTS:
                cls.auth_cache.block_chat(chat_id)
                send_telegram_message(chat_id, "⛔ Too many attempts. Blocked for 24h.")
            else:
                send_telegram_message(chat_id, f"❌ Invalid. Attempts left: {MAX_FAIL_ATTEMPTS - fails}")
            return
        
        # SUCCESS — TELEGRAM LINKED (partial, final OTP still needed)
        vendor.telegram_chat_id = chat_id
        vendor.save()

        VendorUpdated({ # event launch to update the cache data 
            "id": vendor.id,
            "action": "updated",
            "metadata": {
                "user_id": vendor.user_id  # Include user_id for cache invalidation
            }
        }).publish(bg=False)

        cls.auth_cache.clear_fail_attempts(chat_id)
        
        # SEND FINAL OTP AUTOMATICALLY
        otp = str(random.randint(100000, 999999))
        cls.auth_cache.set_final_otp(vendor.business_phone, otp)
        
        message = (
            f"🎉 Wow {first_name}!\n\n"
            "Your Telegram has been successfully linked to your account.\n\n"
            f"🔐 To complete the final verification, here is your OTP: *{otp}*\n\n"
            "Please enter this OTP in your dashboard to finish the Telegram integration."
        )
        send_telegram_message(chat_id, message)

        VendorUpdated({ # event launch to update the cache data 
            "id": vendor.id,
            "action": "updated",
            "metadata": {
                "user_id": vendor.user_id  # Include user_id for cache invalidation
            }
        }).publish(bg=False)
    
    @classmethod
    def send_login_otp(cls, phone_number: str, vendor: Vendor) -> dict:
        """
        Generate and send login OTP via Telegram.
        
        Args:
            phone_number: Vendor's business phone
            vendor: Vendor instance
            
        Returns:
            dict with 'success' (bool) and 'message' (str)
        """
        from datetime import datetime
        
        # Generate OTP
        otp = generate_otp()
        
        # Store in Redis
        cls.auth_cache.set_login_otp(phone_number, otp)
        
        # Prepare message
        user = vendor.user
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        message = f"""🔐 Login OTP Request

Hello {vendor.business_name or user.get_full_name() or user.username}!

Your login OTP is: *{otp}*

📱 Phone: {phone_number}
👤 Username: {user.username}
⏰ Time: {current_time}

⚠️ This OTP will expire in 5 minutes.
Do not share this OTP with anyone.

If you didn't request this, please ignore this message."""
        
        # Send via Telegram
        telegram_response = send_telegram_message(vendor.telegram_chat_id, message)
        
        if not telegram_response:
            return {
                'success': False,
                'message': 'Failed to send OTP. Please try again.'
            }
        
        return {
            'success': True,
            'message': 'OTP sent successfully to your Telegram'
        }
    
    @classmethod
    def verify_login_otp(cls, phone_number: str, otp: str) -> tuple[bool, str, Vendor | None]:
        """
        Verify login OTP.
        
        Args:
            phone_number: Vendor's business phone
            otp: OTP to verify
            
        Returns:
            Tuple of (success: bool, message: str, vendor: Vendor | None)
        """
        # Get OTP from Redis
        stored_otp = cls.auth_cache.get_login_otp(phone_number)
        
        if not stored_otp:
            return False, 'OTP expired or not found. Please request a new OTP.', None
        
        # Verify OTP
        if stored_otp != otp:
            return False, 'Invalid OTP', None
        
        # Get vendor
        try:
            vendor = Vendor.objects.get(business_phone=phone_number)
        except Vendor.DoesNotExist:
            return False, 'Vendor not found', None
        
        # Delete OTP after successful verification
        cls.auth_cache.delete_login_otp(phone_number)
        
        return True, 'Login successful', vendor
    
    @classmethod
    def verify_final_otp(cls, phone_number: str, otp: str) -> tuple[bool, str, Vendor | None]:
        """
        Verify final verification OTP and mark vendor as verified.
        
        Args:
            phone_number: Vendor's business phone
            otp: OTP to verify
            
        Returns:
            Tuple of (success: bool, message: str, vendor: Vendor | None)
        """
        # Get OTP from Redis
        stored_otp = cls.auth_cache.get_final_otp(phone_number)
        
        if not stored_otp:
            return False, 'OTP expired or not found. Please request a new OTP.', None
        
        # Verify OTP
        if stored_otp != otp:
            return False, 'Invalid OTP', None
        
        # Get vendor
        try:
            vendor = Vendor.objects.get(business_phone=phone_number)
        except Vendor.DoesNotExist:
            return False, 'Vendor not found', None
        
        # Mark verified
        vendor.is_verified = True
        vendor.save()
        
        # Delete OTP after successful verification
        cls.auth_cache.delete_final_otp(phone_number)
        
        return True, 'Vendor linked successfully', vendor
    
    @classmethod
    def resend_final_otp(cls, phone_number: str) -> tuple[bool, str]:
        """
        Regenerate and resend final verification OTP.
        
        Args:
            phone_number: Vendor's business phone
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        # Get vendor
        try:
            vendor = Vendor.objects.get(business_phone=phone_number)
        except Vendor.DoesNotExist:
            return False, 'Vendor not found'
        
        # Check if Telegram is linked
        if not vendor.telegram_chat_id:
            return False, 'Telegram not linked yet'
        
        # Generate new OTP
        otp = generate_otp()
        
        # Store in Redis
        cls.auth_cache.set_final_otp(phone_number, otp)
        
        # Send via Telegram
        send_telegram_message(vendor.telegram_chat_id, f"Your final verification OTP is: {otp}")
        
        return True, 'Final OTP sent'
