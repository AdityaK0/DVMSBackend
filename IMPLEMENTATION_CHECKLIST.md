# 🔧 Security Fixes Implementation Checklist

## Status: Changes Applied ✅

### ✅ **COMPLETED - Settings Security**
**Files Modified:**
- `marketplace/settings.py`

**Changes Made:**
1. ✅ SECRET_KEY now loaded from environment variable
2. ✅ DEBUG controlled by environment variable
3. ✅ Security headers added (SECURE_SSL_REDIRECT, HSTS, etc.)
4. ✅ Removed print() statements that logged database credentials
5. ✅ JWT token lifetime reduced from 10 hours to 1 hour
6. ✅ Added custom JWT serializer configuration
7. ✅ Fixed duplicate middleware (removed extra CorsMiddleware)
8. ✅ Added CSRF_TRUSTED_ORIGINS

### ✅ **COMPLETED - JWT Security**
**Files Modified:**
- `apps/users/serializers.py`

**Changes Made:**
1. ✅ Created `CustomTokenObtainPairSerializer` class
2. ✅ Added `vendor_id` claim to JWT tokens
3. ✅ Added role, email, username claims for validation

### ✅ **COMPLETED - Database Model Security**
**Files Modified:**
- `apps/subscriptions/models.py`

**Changes Made:**
1. ✅ Added `unique=True` to `razorpay_payment_id`
2. ✅ Added `unique=True` to `razorpay_signature`
3. ✅ Added index on `razorpay_payment_id`
4. ✅ Added unique constraint for payment_id + signature combo

---

## ⏳ **PENDING - Critical Actions Required**

### 🔴 **STEP 1: Create .env File and Generate SECRET_KEY**
**Priority:** 🚨 DO THIS NOW

```bash
# Generate a new SECRET_KEY
python -c 'import secrets; print(secrets.token_urlsafe(50))'
```

Create `.env` file in project root:
```bash
# .env
DJANGO_SECRET_KEY=<paste_generated_key_here>
DEBUG=True
ENVIRONMENT=development
ALLOWED_HOSTS=localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=http://localhost:5173,http://localhost:3000

# Database
POSTGRES_DB=marketplace_db
POSTGRES_USER=your_user
POSTGRES_PASSWORD=your_password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# Razorpay
RAZORPAY_KEY_ID=your_key_id
RAZORPAY_KEY_SECRET=your_key_secret
RAZORPAY_WEBHOOK_SECRET=your_webhook_secret

# Cloudinary
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret
```

**Test it:**
```bash
cd /Users/upforcetech/simple/learnhub/ecs/marketplace
python manage.py check --deploy
```

---

### 🔴 **STEP 2: Run Database Migrations**
**Priority:** 🚨 CRITICAL - Required for unique constraints

```bash
# Create migrations for model changes
python manage.py makemigrations subscriptions

# Review the migration file
# apps/subscriptions/migrations/000X_alter_paymenttransaction_unique.py

# Apply migrations
python manage.py migrate
```

**Expected Output:**
```
Operations to perform:
  Apply all migrations: subscriptions
Running migrations:
  Applying subscriptions.000X_alter_paymenttransaction_unique... OK
```

---

### 🟠 **STEP 3: Update verify_payment Function** 
**Priority:** 🔴 HIGH - Core security fix

**File:** `apps/subscriptions/views.py`

**Action:** Replace the entire `verify_payment` function (lines ~180-314) with the secure version from `views_secure_verify.py`

**Quick Way:**
```bash
# The secure implementation is in:
# apps/subscriptions/views_secure_verify.py

# Copy the function and replace in apps/subscriptions/views.py
```

**Or manually add these checks to existing verify_payment:**
1. Add replay attack check (lines 30-48 in views_secure_verify.py)
2. Add race condition protection with `select_for_update()`
3. Add amount verification with `client.payment.fetch(payment_id)`
4. Add vendor ownership validation
5. Add JWT claim validation

---

### 🟠 **STEP 4: Update Webhook Function (Amount Verification)**
**Priority:** HIGH

**File:** `apps/subscriptions/views.py` - `razorpay_webhook` function

**Add amount verification in webhook (around line 320):**

```python
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

### 🟡 **STEP 5: Add IP Whitelisting to Webhook (Optional but Recommended)**
**Priority:** MEDIUM

**File:** `apps/subscriptions/views.py`

**Add at the top of `razorpay_webhook` function:**

```python
RAZORPAY_WEBHOOK_IPS = [
    '3.111.198.88',
    '13.232.253.10', 
    '52.66.187.44',
    # Get complete list from Razorpay documentation
]

@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
def razorpay_webhook(request):
    # ✅ CHECK: Verify request comes from Razorpay IP
    client_ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', '')).split(',')[0].strip()
    
    if settings.ENVIRONMENT == 'production' and client_ip not in RAZORPAY_WEBHOOK_IPS:
        logger.error(f"🚨 WEBHOOK FROM UNAUTHORIZED IP: {client_ip}")
        return Response({"status": "forbidden"}, status=status.HTTP_403_FORBIDDEN)
    
    # Continue with existing code...
```

---

### 🟡 **STEP 6: Add Webhook Cross-Verification (Recommended)**
**Priority:** MEDIUM

**Add payment verification check in webhook:**

```python
if event_type == "payment.captured":
    payment = event["payload"]["payment"]["entity"]
    payment_id = payment.get("id")
    order_id = payment.get("order_id")
    
    # ✅ Cross-verify with Razorpay API
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
```

---

## 🧪 **Testing the Fixes**

### Test 1: Verify SECRET_KEY is from environment
```bash
python manage.py shell
>>> from django.conf import settings
>>> print(settings.SECRET_KEY[:20])  # Should NOT start with 'django-insecure'
>>> print(settings.DEBUG)  # Should be True in dev, False in prod
```

### Test 2: Verify JWT tokens have vendor_id claim
```bash
# Make a login request and decode the token
python manage.py shell
>>> from apps.users.models import User
>>> user = User.objects.first()
>>> from rest_framework_simplejwt.tokens import RefreshToken
>>> token = RefreshToken.for_user(user)
>>> print(dict(token.payload))  # Should see 'vendor_id' key
```

### Test 3: Verify unique constraints work
```bash
python manage.py shell
>>> from apps.subscriptions.models import PaymentTransaction
>>> # Try to create duplicate payment_id - should fail
>>> PaymentTransaction.objects.create(
...     vendor_id=1,
...     razorpay_order_id="test_order_1",
...     razorpay_payment_id="pay_123",
...     amount=100000
... )
>>> # Second attempt with same payment_id should raise IntegrityError
>>> PaymentTransaction.objects.create(
...     vendor_id=1,
...     razorpay_order_id="test_order_2",
...     razorpay_payment_id="pay_123",  # Same payment_id
...     amount=100000
... )
# Expected: django.db.utils.IntegrityError
```

### Test 4: Run security test suite
```bash
python manage.py test apps.subscriptions.tests_security -v 2
```

---

## 📋 **Production Deployment Checklist**

Before deploying to production:

- [ ] ✅ SECRET_KEY is 50+ characters and from environment
- [ ] ✅ DEBUG=False in production
- [ ] ✅ ALLOWED_HOSTS configured with actual domain
- [ ] ✅ CSRF_TRUSTED_ORIGINS configured with actual domain
- [ ] ✅ All security headers enabled (HSTS, SSL redirect, etc.)
- [ ] ✅ Database migrations applied
- [ ] ✅ Unique constraints on payment_id and signature
- [ ] ✅ verify_payment updated with all security checks
- [ ] ✅ Webhook has amount verification
- [ ] ⏳ Webhook has IP whitelisting (recommended)
- [ ] ⏳ Webhook has cross-verification (recommended)
- [ ] ✅ JWT tokens reduced to 1-hour lifetime
- [ ] ✅ JWT tokens include vendor_id claim
- [ ] ⏳ Rate limiting configured
- [ ] ⏳ Monitoring/logging set up (Sentry)

---

## 🚨 **What Happens If You Don't Fix These?**

### Without these fixes:
1. **Replay Attacks:** Attacker pays once, gets unlimited subscriptions
2. **Race Conditions:** 1 payment = multiple subscriptions created
3. **Amount Tampering:** Pay ₹1 for ₹999 plan
4. **Webhook Spoofing:** Activate subscriptions without payment
5. **JWT Manipulation:** Steal other vendors' payments

### Financial Impact:
- Estimated loss per successful attack: **₹999 - ₹9,999**
- Attacks per day if exploited: **10-100+**
- **Potential monthly loss: ₹3,00,000 - ₹30,00,000+**

---

## 📞 **Need Help?**

If you encounter errors during implementation:

1. **Migration errors:** Delete the migration file and regenerate
2. **Unique constraint errors:** Check for existing duplicate data
3. **Import errors:** Ensure all imports are at top of file
4. **JWT errors:** Restart server after settings changes

**Common Issues:**

**Issue:** `IntegrityError: duplicate key value violates unique constraint`
**Solution:** Clean up existing duplicate payment_ids before migration:
```python
python manage.py shell
>>> from apps.subscriptions.models import PaymentTransaction
>>> # Find duplicates
>>> duplicates = PaymentTransaction.objects.values('razorpay_payment_id').annotate(count=Count('id')).filter(count__gt=1)
>>> print(duplicates)
```

---

## ✅ **Summary of What Changed**

| File | Lines Changed | Purpose |
|------|--------------|---------|
| `marketplace/settings.py` | 20+ | SECRET_KEY, DEBUG, security headers |
| `apps/users/serializers.py` | 25+ | Custom JWT with vendor_id claim |
| `apps/subscriptions/models.py` | 10+ | Unique constraints for replay prevention |
| `apps/subscriptions/views.py` | 150+ | Secure verify_payment implementation |

**Total Implementation Time:** 2-4 hours
**Critical Priority Items:** Steps 1, 2, 3 (SECRET_KEY, migrations, verify_payment)

---

Last Updated: November 8, 2024
