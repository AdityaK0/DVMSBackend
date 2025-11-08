#!/bin/bash

# =============================================================================
# REPLAY ATTACK API TEST SCRIPT
# =============================================================================
# This script simulates a replay attack against your subscription system
#
# Usage:
#   1. Start your Django server: python manage.py runserver
#   2. Update JWT_TOKEN and BASE_URL below
#   3. Run: bash test_replay_attack_api.sh
# =============================================================================

# Configuration
BASE_URL="http://localhost:8000/api"
JWT_TOKEN="YOUR_JWT_TOKEN_HERE"  # ⚠️ UPDATE THIS!

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "=============================================================================="
echo "🧪 REPLAY ATTACK SIMULATION TEST"
echo "=============================================================================="
echo ""

# Check if JWT token is set
if [ "$JWT_TOKEN" = "YOUR_JWT_TOKEN_HERE" ]; then
    echo -e "${RED}❌ ERROR: Please update JWT_TOKEN in the script${NC}"
    echo ""
    echo "To get your JWT token:"
    echo "  1. Login via your frontend or Postman"
    echo "  2. Copy the access token from the response"
    echo "  3. Update JWT_TOKEN in this script"
    echo ""
    exit 1
fi

echo -e "${BLUE}Configuration:${NC}"
echo "  Base URL: $BASE_URL"
echo "  JWT Token: ${JWT_TOKEN:0:20}...${JWT_TOKEN: -10}"
echo ""

# =============================================================================
# STEP 1: Create First Order and Complete Payment
# =============================================================================
echo "=============================================================================="
echo "STEP 1: Create First Order (Legitimate Payment)"
echo "=============================================================================="

ORDER1_RESPONSE=$(curl -s -X POST "$BASE_URL/subscriptions/create-order/" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"plan_id": 1}')

echo -e "${GREEN}Order 1 Response:${NC}"
echo "$ORDER1_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$ORDER1_RESPONSE"
echo ""

ORDER1_ID=$(echo "$ORDER1_RESPONSE" | grep -o '"order_id":"[^"]*"' | cut -d'"' -f4)

if [ -z "$ORDER1_ID" ]; then
    echo -e "${RED}❌ Failed to create order 1. Check your JWT token and vendor setup.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Order 1 created: $ORDER1_ID${NC}"
echo ""

# =============================================================================
# NOTE: At this point, you would normally:
# 1. Complete payment via Razorpay UI
# 2. Get payment_id and signature from Razorpay response
# 3. Verify payment
#
# For this test, we'll extract a real payment from your database
# =============================================================================

echo "=============================================================================="
echo "STEP 2: Extract Real Payment Details from Database"
echo "=============================================================================="
echo ""
echo "Run this in Django shell to get a real payment:"
echo ""
echo -e "${YELLOW}python manage.py shell${NC}"
echo ""
echo -e "${YELLOW}from apps.subscriptions.models import PaymentTransaction${NC}"
echo -e "${YELLOW}txn = PaymentTransaction.objects.filter(status='captured').first()${NC}"
echo -e "${YELLOW}if txn:${NC}"
echo -e "${YELLOW}    print(f'Order ID: {txn.razorpay_order_id}')${NC}"
echo -e "${YELLOW}    print(f'Payment ID: {txn.razorpay_payment_id}')${NC}"
echo -e "${YELLOW}    print(f'Signature: {txn.razorpay_signature}')${NC}"
echo ""
echo "Copy the values and press Enter to continue..."
read -p "Payment ID: " PAYMENT_ID
read -p "Signature: " SIGNATURE

if [ -z "$PAYMENT_ID" ] || [ -z "$SIGNATURE" ]; then
    echo -e "${RED}❌ Payment details required to continue test${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}✅ Using Payment ID: $PAYMENT_ID${NC}"
echo -e "${GREEN}✅ Using Signature: ${SIGNATURE:0:20}...${NC}"
echo ""

# =============================================================================
# STEP 3: Create Second Order (Attack Target)
# =============================================================================
echo "=============================================================================="
echo "STEP 3: Create Second Order (Replay Attack Target)"
echo "=============================================================================="

ORDER2_RESPONSE=$(curl -s -X POST "$BASE_URL/subscriptions/create-order/" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"plan_id": 1}')

echo -e "${GREEN}Order 2 Response:${NC}"
echo "$ORDER2_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$ORDER2_RESPONSE"
echo ""

ORDER2_ID=$(echo "$ORDER2_RESPONSE" | grep -o '"order_id":"[^"]*"' | cut -d'"' -f4)

if [ -z "$ORDER2_ID" ]; then
    echo -e "${RED}❌ Failed to create order 2${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Order 2 created: $ORDER2_ID${NC}"
echo ""

# =============================================================================
# STEP 4: 🚨 REPLAY ATTACK - Try to use old payment for new order
# =============================================================================
echo "=============================================================================="
echo "🚨 STEP 4: REPLAY ATTACK - Reuse Payment for Different Order"
echo "=============================================================================="
echo ""
echo -e "${RED}ATTACK SCENARIO:${NC}"
echo "  → Attacker creates new order: $ORDER2_ID"
echo "  → Attacker tries to verify with OLD payment: $PAYMENT_ID"
echo "  → If successful: FREE SUBSCRIPTION!"
echo "  → If blocked: Attack prevented ✅"
echo ""

ATTACK_RESPONSE=$(curl -s -X POST "$BASE_URL/subscriptions/verify-payment/" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"razorpay_order_id\": \"$ORDER2_ID\",
    \"razorpay_payment_id\": \"$PAYMENT_ID\",
    \"razorpay_signature\": \"$SIGNATURE\"
  }")

echo -e "${YELLOW}Attack Response:${NC}"
echo "$ATTACK_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$ATTACK_RESPONSE"
echo ""

# Check if attack was blocked
if echo "$ATTACK_RESPONSE" | grep -q "already been used\|replay attack\|already used"; then
    echo ""
    echo "=============================================================================="
    echo -e "${GREEN}✅✅✅ SECURITY SUCCESS! ATTACK BLOCKED! ✅✅✅${NC}"
    echo "=============================================================================="
    echo ""
    echo "Your replay attack protection is working correctly!"
    echo ""
    echo "What happened:"
    echo "  ✅ System detected payment_id was already used"
    echo "  ✅ Attacker cannot reuse old payment"
    echo "  ✅ Each payment can only activate ONE subscription"
    echo ""
    echo "Financial impact prevented:"
    echo "  💰 Potential loss per attack: ₹999 - ₹9,999"
    echo "  💰 Protection status: ACTIVE"
    echo ""
elif echo "$ATTACK_RESPONSE" | grep -q "success.*true\|subscription.*activated"; then
    echo ""
    echo "=============================================================================="
    echo -e "${RED}❌❌❌ SECURITY FAILURE! ATTACK SUCCEEDED! ❌❌❌${NC}"
    echo "=============================================================================="
    echo ""
    echo "⚠️  WARNING: Replay attack protection is NOT working!"
    echo ""
    echo "What happened:"
    echo "  ❌ Attacker reused old payment for new order"
    echo "  ❌ FREE subscription was activated"
    echo "  ❌ This is a CRITICAL security vulnerability"
    echo ""
    echo "Required fixes:"
    echo "  1. Check verify_payment function has replay checks"
    echo "  2. Verify database constraints are active"
    echo "  3. Review SECURITY_ATTACK_SUMMARY.md"
    echo ""
else
    echo ""
    echo "=============================================================================="
    echo -e "${YELLOW}⚠️  UNEXPECTED RESPONSE${NC}"
    echo "=============================================================================="
    echo ""
    echo "The response doesn't match expected patterns."
    echo "Manual review required."
    echo ""
fi

echo "=============================================================================="
echo "Test completed!"
echo "=============================================================================="
