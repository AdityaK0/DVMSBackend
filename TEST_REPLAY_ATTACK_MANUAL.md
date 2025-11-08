# 🧪 Manual Replay Attack Testing Guide

## Quick Test (5 minutes)

### ✅ What You Already Have (From Your Logs)

From your server logs, you already completed a payment:
```
Order ID: order_RdEUl7LkAr3bkd
Payment ID: pay_RdEV52z75RQcyO
Status: captured ✅
```

This means the database already has this payment_id recorded!

---

## 🚨 Test 1: Simple Replay Attack (Easiest)

### **Step 1: Create a NEW Order**

**Via Postman/Frontend:**
```
POST http://localhost:8000/api/subscriptions/create-order/
Headers:
  Authorization: Bearer YOUR_JWT_TOKEN
  Content-Type: application/json
Body:
{
  "plan_id": 1
}
```

**Response:**
```json
{
  "order_id": "order_NEW123",  // ← Save this NEW order ID
  "amount": 100,
  "currency": "INR"
}
```

### **Step 2: Try to Verify with OLD Payment (ATTACK)**

**Via Postman/Frontend:**
```
POST http://localhost:8000/api/subscriptions/verify-payment/
Headers:
  Authorization: Bearer YOUR_JWT_TOKEN
  Content-Type: application/json
Body:
{
  "razorpay_order_id": "order_NEW123",              // ← NEW order
  "razorpay_payment_id": "pay_RdEV52z75RQcyO",     // ← OLD payment (REPLAY!)
  "razorpay_signature": "COPY_FROM_FIRST_PAYMENT"   // ← OLD signature
}
```

### **Expected Results:**

#### ✅ **WITH Protection (Current):**
```json
{
  "error": "This payment ID has already been used. Contact support if this is an error."
}
```
**Status Code:** 400 Bad Request
**Meaning:** 🎉 **ATTACK BLOCKED!** Protection is working!

#### ❌ **WITHOUT Protection (Vulnerable):**
```json
{
  "success": true,
  "detail": "Payment verified and subscription activated"
}
```
**Status Code:** 200 OK
**Meaning:** 🚨 **CRITICAL VULNERABILITY!** Attacker got free subscription!

---

## 🧪 Test 2: Database-Level Test

### **Run Python Script**

```bash
cd /Users/upforcetech/simple/learnhub/ecs/marketplace
python test_replay_attack.py
```

**Expected Output:**
```
==============================================================================
🧪 TESTING REPLAY ATTACK PROTECTION
==============================================================================

✅ Using vendor: Test Vendor (ID: 17)
✅ Using plan: Basic Plan (ID: 1)

==============================================================================
TEST 1: Try to create duplicate payment_id
==============================================================================
✅ First transaction created: order_test_abc123
✅ SECURITY SUCCESS: Duplicate payment_id blocked!
✅ REPLAY ATTACK PREVENTED!

==============================================================================
TEST 2: Try to create duplicate signature
==============================================================================
✅ First transaction created: order_test_def456
✅ SECURITY SUCCESS: Duplicate signature blocked!
✅ REPLAY ATTACK PREVENTED!

==============================================================================
TEST 3: Try to reuse your actual payment from logs
==============================================================================
✅ Found real payment: pay_RdEV52z75RQcyO
✅ SECURITY SUCCESS: Real payment_id cannot be reused!
✅ YOUR PAYMENT IS PROTECTED!
```

---

## 🧪 Test 3: API Test with cURL

### **Quick cURL Test**

```bash
# 1. Get your JWT token
TOKEN="eyJ0eXAiOiJKV1QiLCJhbGc..."  # From login response

# 2. Create new order
curl -X POST http://localhost:8000/api/subscriptions/create-order/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"plan_id": 1}'

# Response: {"order_id": "order_XYZ123", ...}

# 3. Try replay attack
curl -X POST http://localhost:8000/api/subscriptions/verify-payment/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "razorpay_order_id": "order_XYZ123",
    "razorpay_payment_id": "pay_RdEV52z75RQcyO",
    "razorpay_signature": "GET_FROM_YOUR_FIRST_PAYMENT"
  }'

# Expected: {"error": "This payment ID has already been used..."}
```

---

## 🧪 Test 4: Check Current Protection Status

### **Quick Database Check**

```bash
python manage.py shell
```

```python
from apps.subscriptions.models import PaymentTransaction
from django.db import connection

# Check if unique constraints exist
with connection.cursor() as cursor:
    cursor.execute("""
        SELECT constraint_name 
        FROM information_schema.table_constraints 
        WHERE table_name='subscriptions_paymenttransaction' 
        AND constraint_type='UNIQUE';
    """)
    constraints = cursor.fetchall()
    print("Unique constraints:")
    for c in constraints:
        print(f"  - {c[0]}")

# Check if duplicate payment_ids exist
duplicates = PaymentTransaction.objects.values('razorpay_payment_id').annotate(
    count=Count('id')
).filter(count__gt=1, razorpay_payment_id__isnull=False)

if duplicates.exists():
    print("\n❌ WARNING: Duplicate payment_ids found!")
    for dup in duplicates:
        print(f"  - {dup['razorpay_payment_id']}: {dup['count']} times")
else:
    print("\n✅ No duplicate payment_ids found - protection working!")
```

---

## 📊 Test Results Interpretation

### ✅ **Protection WORKING**
```
✅ Duplicate payment_id blocked by database
✅ API returns error: "already been used"
✅ Status code: 400 Bad Request
✅ No new subscription created
✅ Logs show: "🚨 REPLAY ATTACK DETECTED"
```

### ❌ **Protection NOT WORKING**
```
❌ Same payment_id accepted twice
❌ API returns success message
❌ Status code: 200 OK
❌ New subscription activated without payment
❌ No error in logs
```

---

## 🎯 Real-World Attack Simulation

### **Scenario: Malicious Vendor**

1. **Attacker completes ONE legitimate payment:** ₹1 for Basic Plan
2. **Attacker captures the response:**
   ```json
   {
     "razorpay_payment_id": "pay_ABC123",
     "razorpay_signature": "sig_XYZ789"
   }
   ```
3. **Attacker creates 100 new orders** (via script/automation)
4. **Attacker verifies all 100 with SAME payment details**
5. **Without protection:** Gets 100 subscriptions for ₹1
6. **With protection:** Gets 1 subscription, 99 attacks blocked ✅

### **Financial Impact**

| Scenario | Cost to Attacker | Value Gained | Your Loss |
|----------|------------------|--------------|-----------|
| **No Protection** | ₹1 | 100 × ₹999 = ₹99,900 | ₹99,899 |
| **With Protection** | ₹1 | 1 × ₹999 = ₹999 | ₹0 ✅ |

---

## 🔍 What to Look For in Logs

### **Attack Blocked (Good):**
```
INFO: ✅ Payment signature verified for order order_NEW123
ERROR: 🚨 REPLAY ATTACK DETECTED: payment_id pay_RdEV52z75RQcyO already used
INFO: Returned 400 error: Payment ID already used
```

### **Attack Succeeded (Bad):**
```
INFO: ✅ Payment signature verified for order order_NEW123
INFO: ✅ Payment verified and subscription created
INFO: ✅ Subscription activated for vendor 17
```

---

## 🚀 Quick Run All Tests

```bash
# Test 1: Database-level test
python test_replay_attack.py

# Test 2: API test (requires manual JWT token)
# Edit test_replay_attack_api.sh and add your JWT token
bash test_replay_attack_api.sh

# Test 3: Check database constraints
python manage.py shell -c "
from django.db import connection
with connection.cursor() as cursor:
    cursor.execute(\"SELECT constraint_name FROM information_schema.table_constraints WHERE table_name='subscriptions_paymenttransaction' AND constraint_type='UNIQUE'\")
    print('Constraints:', [c[0] for c in cursor.fetchall()])
"
```

---

## 📝 Summary

**To confirm protection is working, you should see:**

1. ✅ Database throws `IntegrityError` on duplicate payment_id
2. ✅ API returns 400 error with message about "already used"
3. ✅ Logs show "REPLAY ATTACK DETECTED"
4. ✅ Only ONE subscription exists per payment_id
5. ✅ `unique_payment_signature_combo` constraint exists in database

**If any of these fail, the protection is NOT working properly!**

---

## 🆘 Troubleshooting

### "No duplicate payment_id found to test"
**Solution:** Complete at least one real payment first, then try to reuse it.

### "Signature verification failed"
**Solution:** This is Razorpay's validation failing (different issue). The replay check happens AFTER signature validation.

### "Payment transaction not found"
**Solution:** The order_id doesn't exist or doesn't belong to you. Use a valid order_id.

---

**Last Updated:** November 8, 2025
