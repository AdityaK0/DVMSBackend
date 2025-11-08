# 🎯 Subscription System Attack Vectors - Quick Reference

## Executive Summary

**Total Attack Vectors Identified:** 5 Critical
**Exploitability:** HIGH (without fixes)
**Impact:** Complete bypass of payment system
**Estimated Fix Time:** 16 hours

---

## Attack Surface Overview

```
┌─────────────────────────────────────────────────────────┐
│                  ATTACK SURFACE MAP                      │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  1. Payment Signature Replay                            │
│     └─> Reuse valid signatures for free subscriptions  │
│                                                          │
│  2. Race Condition                                       │
│     └─> Multiple concurrent requests = multiple subs    │
│                                                          │
│  3. Amount Tampering                                     │
│     └─> Pay ₹1, get ₹999 plan                          │
│                                                          │
│  4. Webhook Spoofing                                     │
│     └─> Fake activation without payment                 │
│                                                          │
│  5. JWT Manipulation                                     │
│     └─> Activate other vendors' subscriptions           │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## 🔴 Attack #1: Payment Signature Replay

**Attack Vector:**
```bash
# Attacker flow
1. Pay once legitimately (order_1 → payment_1 → signature_1)
2. Create new order (order_2)
3. Reuse payment_1 + signature_1 to verify order_2
4. Result: 2 subscriptions for 1 payment
```

**Exploit Code:**
```python
# Capture once
legit_payment = {
    "payment_id": "pay_real123",
    "signature": "sig_real456"
}

# Reuse forever
for month in range(12):
    new_order = create_order()
    verify_payment(
        order_id=new_order.id,
        payment_id=legit_payment["payment_id"],  # Reused!
        signature=legit_payment["signature"]     # Reused!
    )
```

**Fix:**
- Add unique constraints on `razorpay_payment_id` and `razorpay_signature`
- Check if payment/signature already used before verification
- Cross-reference order_id with payment_id

**Migration Required:**
```bash
python manage.py makemigrations subscriptions
python manage.py migrate
```

---

## 🔴 Attack #2: Race Condition

**Attack Vector:**
```python
import asyncio
import aiohttp

# Send 100 simultaneous requests
async def exploit():
    tasks = [verify_payment(same_order) for _ in range(100)]
    await asyncio.gather(*tasks)
    # Result: 100 subscriptions created!
```

**Current Flaw:**
```python
# Vulnerable code (no locking)
def verify_payment(request):
    txn = PaymentTransaction.objects.get(order_id=...)  # ❌ No lock
    if txn.status == 'captured':  # All 100 threads pass this check
        return "already processed"
    
    txn.status = 'captured'  # All 100 threads do this
    txn.save()
```

**Fix:**
```python
# Fixed code (with database locking)
from django.db import transaction

@transaction.atomic
def verify_payment(request):
    txn = PaymentTransaction.objects.select_for_update().get(...)  # ✅ Row locked
    if txn.status == 'captured':
        return "already processed"
    
    txn.status = 'processing'  # Immediate state change
    txn.save()
    # Only first thread proceeds, others blocked
```

---

## 🔴 Attack #3: Amount Tampering

**Attack Vector:**
```javascript
// Frontend attack - modify Razorpay order amount
const exploit = async () => {
    // Step 1: Backend creates order for ₹999
    const order = await fetch('/api/subscriptions/create-order/', {
        body: JSON.stringify({ plan_id: premium_plan })
    });
    
    // Step 2: Attacker manually creates Razorpay order with ₹1
    const razorpayOrder = await razorpay.orders.create({
        amount: 100,  // ₹1 instead of ₹999
        currency: 'INR'
    });
    
    // Step 3: Complete payment with ₹1
    // Backend never checks actual amount paid!
};
```

**Current Flaw:**
```python
# Backend never verifies actual amount
def verify_payment(request):
    # ❌ No amount verification
    txn.status = 'captured'  # Activated without checking!
```

**Fix:**
```python
def verify_payment(request):
    # ✅ Fetch actual payment from Razorpay
    client = get_razorpay_client()
    razorpay_payment = client.payment.fetch(payment_id)
    
    actual_amount = razorpay_payment['amount']
    expected_amount = payment_txn.amount
    
    if actual_amount != expected_amount:
        logger.error(f"🚨 Amount tampering: expected {expected_amount}, got {actual_amount}")
        return error_response("Amount mismatch")
```

---

## 🟠 Attack #4: Webhook Spoofing

**Attack Vector:**
```python
import hmac
import hashlib
import json

# If webhook secret leaked
STOLEN_SECRET = "whsec_abc123..."

def send_fake_webhook(order_id):
    fake_payload = {
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_fake999",
                    "order_id": order_id,
                    "amount": 99900,
                    "status": "captured"
                }
            }
        }
    }
    
    # Generate valid signature
    signature = hmac.new(
        STOLEN_SECRET.encode(),
        json.dumps(fake_payload).encode(),
        hashlib.sha256
    ).hexdigest()
    
    # Send to webhook endpoint
    requests.post('/api/subscriptions/webhook/', 
                  json=fake_payload,
                  headers={'X-Razorpay-Signature': signature})
```

**Fix Layers:**
1. **IP Whitelist** - Only accept from Razorpay IPs
2. **Signature Verification** - Already implemented ✅
3. **Cross-verify with Razorpay API** - Fetch payment to confirm it exists
4. **Event ID tracking** - Never process same webhook twice

---

## 🔴 Attack #5: JWT Token Manipulation

**Attack Vector:**
```python
import jwt

# Your current SECRET_KEY (exposed in settings.py!)
SECRET_KEY = "django-insecure-vd3b_wa*#xd7k*pewu5071!rpr!p8z)+pca@cpp&fu%t#gb%^@"

def forge_token(target_vendor_id):
    payload = {
        'user_id': 999,  # Attacker's ID
        'vendor_id': target_vendor_id,  # Victim's vendor
        'exp': future_timestamp
    }
    
    # Create forged token
    forged = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
    
    # Use to activate victim's subscription
    requests.post('/api/subscriptions/verify-payment/',
                  headers={'Authorization': f'Bearer {forged}'},
                  json=victim_payment_data)
```

**Critical Fixes:**
```python
# 1. IMMEDIATELY change SECRET_KEY
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY')  # Random 50+ char string

# 2. Add vendor ownership check
def verify_payment(request):
    txn = PaymentTransaction.objects.get(
        order_id=order_id,
        vendor=request.user.vendor  # ✅ Must match authenticated user
    )
    
    if txn.vendor.id != request.user.vendor.id:
        return error_response("Unauthorized", 403)

# 3. Add JWT claims validation
if request.auth.payload['vendor_id'] != actual_vendor.id:
    return error_response("Token manipulation detected", 401)
```

---

## 🛡️ Defense-in-Depth Strategy

### Layer 1: Request Validation
- ✅ Signature verification
- ✅ Amount verification
- ✅ Vendor ownership check
- ✅ Duplicate detection

### Layer 2: Database Protection
- ✅ Unique constraints
- ✅ Row-level locking
- ✅ Atomic transactions
- ✅ Indexes for performance

### Layer 3: External Verification
- ✅ Cross-verify with Razorpay API
- ✅ IP whitelisting for webhooks
- ✅ Event ID tracking
- ✅ Amount double-check

### Layer 4: Application Security
- ✅ Strong SECRET_KEY
- ✅ JWT claims validation
- ✅ Permission checks at multiple levels
- ✅ Rate limiting (TODO)

---

## 🧪 Testing the Fixes

```bash
# Run security tests
python manage.py test apps.subscriptions.tests_security

# Expected output:
# ✅ test_replay_attack_with_same_payment_id ... ok
# ✅ test_concurrent_verify_payment_requests ... ok
# ✅ test_pay_less_than_plan_price ... ok
# ✅ test_webhook_from_unauthorized_ip ... ok
# ✅ test_cross_vendor_payment_verification ... ok
```

---

## 📋 Implementation Checklist

### Immediate (Before Production)
- [ ] Change SECRET_KEY to 50+ character random string
- [ ] Add unique constraints to payment_id and signature
- [ ] Implement select_for_update() locking
- [ ] Add amount verification in verify_payment
- [ ] Add vendor ownership checks

### High Priority (Within 24h)
- [ ] Implement webhook IP whitelisting
- [ ] Add cross-verification with Razorpay API
- [ ] Add event ID tracking for webhooks
- [ ] Implement rate limiting on auth endpoints
- [ ] Add comprehensive logging

### Medium Priority (Within 1 week)
- [ ] Set up monitoring/alerting (Sentry)
- [ ] Add automated security tests to CI/CD
- [ ] Implement request throttling
- [ ] Add admin dashboard for suspicious activity
- [ ] Document security procedures

---

## 🚨 Incident Response

If you detect an attack:

1. **Immediate Actions:**
   ```bash
   # Disable webhook endpoint
   # In settings.py temporarily:
   RAZORPAY_WEBHOOK_ENABLED = False
   
   # Check for suspicious transactions
   python manage.py shell
   >>> from apps.subscriptions.models import *
   >>> suspicious = PaymentTransaction.objects.filter(
   ...     status='captured',
   ...     created_at__date=today
   ... ).select_related('vendor')
   ```

2. **Investigation:**
   - Check logs for repeated payment_ids
   - Look for concurrent requests from same IP
   - Verify actual Razorpay payment amounts
   - Check JWT token claims vs actual vendor IDs

3. **Remediation:**
   - Invalidate suspicious subscriptions
   - Refund legitimate customers
   - Rotate SECRET_KEY
   - Update webhook secret

---

## 📞 Support

For security concerns:
- **Email:** security@yourcompany.com
- **Bug Bounty:** Report at /security/disclosure

**DO NOT** publicly disclose vulnerabilities without coordinating with the security team.

---

## Version History

- **v1.0** (2024-11-08): Initial security analysis
- **Fixes Pending**: Implementation of all countermeasures

**Last Updated:** November 8, 2024
**Next Review:** Before production deployment
