# 🔐 Secure Razorpay Payment Implementation

## Overview
This document describes the secure, production-ready payment architecture that ensures subscriptions are activated **only after confirmed payment capture** with cryptographic proof from Razorpay.

## Architecture

### Security Flow
```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐     ┌──────────────┐
│   Frontend  │────►│ create-order │────►│  Razorpay   │────►│   Payment    │
│             │     │   (Backend)  │     │   Gateway   │     │     Page     │
└─────────────┘     └──────────────┘     └─────────────┘     └──────────────┘
                            │                                        │
                            ▼                                        │
                    ┌──────────────┐                                 │
                    │ PaymentTxn   │                                 │
                    │ status=created│                                │
                    └──────────────┘                                 │
                                                                     │
                                        User Pays                    │
                                             │                       │
                                             ▼                       │
                    ┌────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Frontend   │────►│verify-payment│────►│  Signature  │
│  (success)  │     │   (Backend)  │     │ Verification│
└─────────────┘     └──────────────┘     └─────────────┘
                            │                    │
                            │     ✅ Valid       │
                            ├────────────────────┘
                            │
                            ▼
                    ┌──────────────┐
                    │  Activate    │
                    │ Subscription │
                    └──────────────┘
                            │
                            ▼
                    ┌──────────────┐
                    │   Sync to    │
                    │Elasticsearch │
                    └──────────────┘
```

## Key Security Features

### 1. **No Premature Activation**
- `create-order` endpoint **ONLY** creates:
  - Razorpay Order
  - PaymentTransaction with `status='created'`
- **DOES NOT** activate subscription
- Even if user cancels payment, no subscription is created

### 2. **Cryptographic Signature Verification**
```python
# Every payment must pass this verification
client.utility.verify_payment_signature({
    "razorpay_order_id": order_id,
    "razorpay_payment_id": payment_id,
    "razorpay_signature": signature,
})
```
- Uses HMAC-SHA256 with your secret key
- Cannot be faked by client-side manipulation
- Razorpay SDK automatically validates the signature

### 3. **Transaction Proof Chain**
```
Order Created → PaymentTransaction (status=created)
                      ↓
Payment Successful → Signature Verified
                      ↓
                PaymentTransaction (status=captured)
                      ↓
                Subscription Activated
```

### 4. **Idempotency Protection**
- Prevents duplicate activations from:
  - Multiple frontend calls
  - Webhook replays
  - Race conditions
- Checks if transaction already captured before processing

### 5. **Webhook Backup**
- Production webhook handler at `/api/subscriptions/webhook/`
- Handles `payment.captured` and `payment.failed` events
- Provides redundancy if frontend verification fails
- Also cryptographically verified

## Models

### SubscriptionPlan
```python
- name, plan_type, description
- price (Decimal), price_in_paise (Integer)
- duration_days, sync_limit
- is_active
```

### PaymentTransaction
```python
- vendor, plan
- razorpay_order_id (unique)
- razorpay_payment_id, razorpay_signature
- amount (in paise), currency
- status: created → captured/failed
- error_message, razorpay_response
- created_at, verified_at
```

### Subscription
```python
- vendor (OneToOne)
- plan, transaction (ForeignKeys)
- start_date, end_date, is_active
- amount, order_id, payment_id
```

## API Endpoints

### 1. GET `/api/subscriptions/plans/`
**Purpose**: List available subscription plans

**Auth**: Required

**Response**:
```json
{
  "plans": [
    {
      "id": 1,
      "name": "Basic Plan",
      "plan_type": "basic",
      "price": "999.00",
      "price_in_paise": 99900,
      "duration_days": 30,
      "sync_limit": 10,
      "description": "Perfect for small businesses"
    }
  ]
}
```

### 2. POST `/api/subscriptions/create-order/`
**Purpose**: Create Razorpay order (NO subscription activation)

**Auth**: Required

**Request**:
```json
{
  "plan_id": 1
}
```

**Response**:
```json
{
  "order_id": "order_MN1pQ2xYzZ3abc",
  "amount": 99900,
  "currency": "INR",
  "key": "rzp_test_xxxxxxxx",
  "plan": { /* plan details */ },
  "transaction_id": 42
}
```

**Security**:
- ✅ Only creates PaymentTransaction with `status='created'`
- ✅ Checks for existing active subscription
- ✅ Does NOT activate subscription
- ✅ Validates plan exists and is active

### 3. POST `/api/subscriptions/verify-payment/`
**Purpose**: Verify payment signature and activate subscription

**Auth**: Required

**Request**:
```json
{
  "razorpay_payment_id": "pay_MN1pQ2xYzZ3abc",
  "razorpay_order_id": "order_MN1pQ2xYzZ3abc",
  "razorpay_signature": "abc123def456..."
}
```

**Response**:
```json
{
  "success": true,
  "detail": "Payment verified and subscription created successfully.",
  "subscription": { /* subscription details */ },
  "transaction": { /* transaction details */ }
}
```

**Security Flow**:
1. ✅ Validate all required fields present
2. ✅ Verify Razorpay signature (cryptographic proof)
3. ✅ Find PaymentTransaction (proof of backend order creation)
4. ✅ Check idempotency (prevent duplicate activation)
5. ✅ Create/Update Subscription (atomic transaction)
6. ✅ Mark PaymentTransaction as `captured`
7. ✅ Sync to Elasticsearch
8. ✅ Return success response

**Error Responses**:
- `400`: Missing fields or invalid signature
- `404`: PaymentTransaction not found (order not created via backend)
- `500`: Server error during activation

### 4. GET `/api/subscriptions/status/`
**Purpose**: Get current vendor subscription status

**Auth**: Required

**Response**:
```json
{
  "subscription": {
    "id": 1,
    "vendor": 42,
    "vendor_name": "Tech Store",
    "plan": 1,
    "plan_name": "Basic Plan",
    "is_active": true,
    "start_date": "2025-11-08T10:30:00Z",
    "end_date": "2025-12-08T10:30:00Z",
    "days_remaining": 30,
    "amount": "999.00"
  }
}
```

### 5. POST `/api/subscriptions/webhook/` (Public)
**Purpose**: Razorpay webhook handler for production

**Auth**: None (webhook signature verified)

**Events Handled**:
- `payment.captured`: Activate subscription
- `payment.failed`: Mark transaction as failed

**Security**:
- ✅ Verifies webhook signature using `RAZORPAY_WEBHOOK_SECRET`
- ✅ Idempotency protection
- ✅ Only processes transactions created via backend
- ✅ Atomic database operations

## Frontend Integration Example

```javascript
// 1. Fetch plans
const plans = await fetch('/api/subscriptions/plans/').then(r => r.json());

// 2. Create order
const orderData = await fetch('/api/subscriptions/create-order/', {
  method: 'POST',
  headers: { 'Authorization': `Bearer ${token}` },
  body: JSON.stringify({ plan_id: selectedPlanId })
}).then(r => r.json());

// 3. Open Razorpay checkout
const options = {
  key: orderData.key,
  amount: orderData.amount,
  currency: orderData.currency,
  order_id: orderData.order_id,
  name: "Your Company",
  description: orderData.plan.name,
  handler: async function (response) {
    // 4. Verify payment on backend
    const result = await fetch('/api/subscriptions/verify-payment/', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` },
      body: JSON.stringify({
        razorpay_payment_id: response.razorpay_payment_id,
        razorpay_order_id: response.razorpay_order_id,
        razorpay_signature: response.razorpay_signature
      })
    }).then(r => r.json());
    
    if (result.success) {
      // Subscription activated!
      window.location.href = '/dashboard/subscription-success';
    }
  },
  modal: {
    ondismiss: function() {
      // User cancelled - no subscription created
      console.log('Payment cancelled');
    }
  }
};

const rzp = new Razorpay(options);
rzp.open();
```

## Environment Variables

Add to `.env`:
```bash
RAZORPAY_KEY_ID=rzp_test_xxxxxxxx
RAZORPAY_KEY_SECRET=your_secret_key_here
RAZORPAY_WEBHOOK_SECRET=your_webhook_secret_here  # From Razorpay Dashboard
```

## Database Migrations

```bash
# Create migrations
python manage.py makemigrations subscriptions

# Apply migrations
python manage.py migrate subscriptions
```

## Admin Setup

Create subscription plans via Django admin or shell:

```python
from apps.subscriptions.models import SubscriptionPlan

SubscriptionPlan.objects.create(
    name="Basic Plan",
    plan_type="basic",
    description="Perfect for small businesses",
    price=999.00,  # price_in_paise auto-calculated
    duration_days=30,
    sync_limit=10,
    is_active=True
)

SubscriptionPlan.objects.create(
    name="Premium Plan",
    plan_type="premium",
    description="For growing businesses",
    price=1999.00,
    duration_days=30,
    sync_limit=50,
    is_active=True
)
```

## Elasticsearch Sync

After successful payment verification, the system automatically:
1. Updates vendor document in Elasticsearch
2. Sets `is_subscribed: true` and `subscription_active: true`
3. Records `last_sync` timestamp

This ensures FastAPI public portfolio can check subscription status instantly.

## Testing Checklist

### ✅ Security Tests
- [ ] Cannot activate subscription by calling `create-order` alone
- [ ] Cannot bypass signature verification
- [ ] Cannot activate with fake `order_id`
- [ ] Cannot activate same payment twice (idempotency)
- [ ] Webhook rejects invalid signatures
- [ ] Expired subscriptions auto-deactivate

### ✅ Payment Flow Tests
- [ ] Create order successfully
- [ ] User cancels payment → no subscription
- [ ] User completes payment → subscription activated
- [ ] Webhook handles `payment.captured`
- [ ] Webhook handles `payment.failed`
- [ ] Multiple vendors can pay simultaneously

### ✅ Integration Tests
- [ ] Elasticsearch syncs after payment
- [ ] Subscription status endpoint returns correct data
- [ ] Plans endpoint lists active plans only
- [ ] Transaction history is accurate

## Production Deployment

1. **Set environment variables** in production:
   ```bash
   RAZORPAY_KEY_ID=rzp_live_xxxxxxxx
   RAZORPAY_KEY_SECRET=<live_secret>
   RAZORPAY_WEBHOOK_SECRET=<webhook_secret>
   ```

2. **Configure Razorpay webhook**:
   - Go to Razorpay Dashboard → Webhooks
   - Add webhook URL: `https://yourdomain.com/api/subscriptions/webhook/`
   - Select events: `payment.captured`, `payment.failed`
   - Copy webhook secret to `RAZORPAY_WEBHOOK_SECRET`

3. **Test with Razorpay test cards**:
   - Success: 4111 1111 1111 1111
   - Failure: 4000 0000 0000 0002

4. **Monitor logs**:
   - Look for `✅` (success) and `❌` (failure) emojis in logs
   - Check PaymentTransaction status transitions
   - Verify Elasticsearch sync confirmations

## Security Best Practices

1. ✅ **Never trust client-side data** - Always verify on backend
2. ✅ **Signature verification is mandatory** - Don't skip this step
3. ✅ **Use atomic transactions** - Prevent partial state updates
4. ✅ **Implement idempotency** - Handle duplicate requests safely
5. ✅ **Log all payment events** - Essential for debugging and auditing
6. ✅ **Keep secrets secure** - Use environment variables, never commit keys
7. ✅ **Monitor webhook failures** - Set up alerts for payment issues

## Support & Troubleshooting

### Payment not activating?
1. Check logs for signature verification errors
2. Verify `RAZORPAY_KEY_SECRET` is correct
3. Confirm PaymentTransaction exists with correct `order_id`
4. Check Elasticsearch connection if sync fails

### Webhook not working?
1. Verify `RAZORPAY_WEBHOOK_SECRET` is set
2. Test webhook signature verification
3. Check firewall/CORS settings
4. Review Razorpay Dashboard → Webhooks → Logs

### Multiple activations?
1. Check idempotency logic in `verify_payment`
2. Review transaction status transitions
3. Add unique constraint on critical fields if needed

---

## 🎉 Result

You now have a **production-ready, secure payment system** that:
- ✅ Cannot be tricked by client-side cancellations
- ✅ Requires cryptographic proof for activation
- ✅ Prevents fake frontend requests
- ✅ Handles edge cases gracefully
- ✅ Syncs to Elasticsearch automatically
- ✅ Provides webhook redundancy
- ✅ Follows industry best practices

**No subscription will be activated without confirmed, verified payment capture!** 🔒
