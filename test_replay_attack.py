#!/usr/bin/env python
"""
Manual Replay Attack Test Script
This script simulates a replay attack to verify protection is working.
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'marketplace.settings')
django.setup()

from apps.subscriptions.models import PaymentTransaction, Subscription
from apps.vendors.models import Vendor
from apps.subscriptions.models import SubscriptionPlan
from django.utils import timezone
import uuid


def test_replay_attack_protection():
    """
    Test if the database constraints prevent replay attacks
    """
    print("=" * 80)
    print("🧪 TESTING REPLAY ATTACK PROTECTION")
    print("=" * 80)
    
    # Get or create a test vendor
    vendor = Vendor.objects.first()
    if not vendor:
        print("❌ No vendor found. Please create a vendor first.")
        return
    
    plan = SubscriptionPlan.objects.first()
    if not plan:
        print("❌ No subscription plan found. Please create a plan first.")
        return
    
    print(f"\n✅ Using vendor: {vendor.business_name} (ID: {vendor.id})")
    print(f"✅ Using plan: {plan.name} (ID: {plan.id})")
    
    # Test 1: Create two transactions with same payment_id
    print("\n" + "=" * 80)
    print("TEST 1: Try to create duplicate payment_id")
    print("=" * 80)
    
    test_payment_id = f"pay_test_{uuid.uuid4().hex[:10]}"
    test_signature = f"sig_test_{uuid.uuid4().hex[:10]}"
    
    try:
        # First transaction
        txn1 = PaymentTransaction.objects.create(
            vendor=vendor,
            plan=plan,
            razorpay_order_id=f"order_test_{uuid.uuid4().hex[:10]}",
            razorpay_payment_id=test_payment_id,
            razorpay_signature=test_signature,
            amount=plan.price * 100,
            status='captured'
        )
        print(f"✅ First transaction created: {txn1.razorpay_order_id}")
        
        # Try to create second transaction with SAME payment_id (REPLAY ATTACK)
        try:
            txn2 = PaymentTransaction.objects.create(
                vendor=vendor,
                plan=plan,
                razorpay_order_id=f"order_test_{uuid.uuid4().hex[:10]}",  # Different order
                razorpay_payment_id=test_payment_id,  # ❌ SAME payment_id (ATTACK)
                razorpay_signature=f"sig_different_{uuid.uuid4().hex[:10]}",  # Different sig
                amount=plan.price * 100,
                status='captured'
            )
            print("❌ SECURITY FAILURE: Duplicate payment_id was allowed!")
            print("🚨 REPLAY ATTACK WOULD SUCCEED!")
            
        except Exception as e:
            print(f"✅ SECURITY SUCCESS: Duplicate payment_id blocked!")
            print(f"   Error: {str(e)[:100]}")
            print("✅ REPLAY ATTACK PREVENTED!")
        
        # Cleanup
        txn1.delete()
        
    except Exception as e:
        print(f"❌ Test setup failed: {str(e)}")
    
    # Test 2: Try to reuse signature
    print("\n" + "=" * 80)
    print("TEST 2: Try to create duplicate signature")
    print("=" * 80)
    
    test_payment_id_2 = f"pay_test_{uuid.uuid4().hex[:10]}"
    test_signature_2 = f"sig_test_{uuid.uuid4().hex[:10]}"
    
    try:
        # First transaction
        txn1 = PaymentTransaction.objects.create(
            vendor=vendor,
            plan=plan,
            razorpay_order_id=f"order_test_{uuid.uuid4().hex[:10]}",
            razorpay_payment_id=test_payment_id_2,
            razorpay_signature=test_signature_2,
            amount=plan.price * 100,
            status='captured'
        )
        print(f"✅ First transaction created: {txn1.razorpay_order_id}")
        
        # Try to create second transaction with SAME signature (REPLAY ATTACK)
        try:
            txn2 = PaymentTransaction.objects.create(
                vendor=vendor,
                plan=plan,
                razorpay_order_id=f"order_test_{uuid.uuid4().hex[:10]}",  # Different order
                razorpay_payment_id=f"pay_different_{uuid.uuid4().hex[:10]}",  # Different payment_id
                razorpay_signature=test_signature_2,  # ❌ SAME signature (ATTACK)
                amount=plan.price * 100,
                status='captured'
            )
            print("❌ SECURITY FAILURE: Duplicate signature was allowed!")
            print("🚨 REPLAY ATTACK WOULD SUCCEED!")
            
        except Exception as e:
            print(f"✅ SECURITY SUCCESS: Duplicate signature blocked!")
            print(f"   Error: {str(e)[:100]}")
            print("✅ REPLAY ATTACK PREVENTED!")
        
        # Cleanup
        txn1.delete()
        
    except Exception as e:
        print(f"❌ Test setup failed: {str(e)}")
    
    # Test 3: Check existing payment reuse (from your real payment)
    print("\n" + "=" * 80)
    print("TEST 3: Try to reuse your actual payment from logs")
    print("=" * 80)
    
    real_payment = PaymentTransaction.objects.filter(
        razorpay_payment_id="pay_RdEV52z75RQcyO"
    ).first()
    
    if real_payment:
        print(f"✅ Found real payment: {real_payment.razorpay_payment_id}")
        print(f"   Order: {real_payment.razorpay_order_id}")
        print(f"   Status: {real_payment.status}")
        
        try:
            # Try to create new transaction with same payment_id
            new_txn = PaymentTransaction.objects.create(
                vendor=vendor,
                plan=plan,
                razorpay_order_id=f"order_replay_{uuid.uuid4().hex[:10]}",
                razorpay_payment_id="pay_RdEV52z75RQcyO",  # ❌ Reuse real payment_id
                razorpay_signature=f"sig_fake_{uuid.uuid4().hex[:10]}",
                amount=plan.price * 100,
                status='created'
            )
            print("❌ SECURITY FAILURE: Real payment_id was reused!")
            print("🚨 ATTACKER COULD STEAL YOUR PAYMENT!")
            new_txn.delete()
            
        except Exception as e:
            print(f"✅ SECURITY SUCCESS: Real payment_id cannot be reused!")
            print(f"   Error: {str(e)[:100]}")
            print("✅ YOUR PAYMENT IS PROTECTED!")
    else:
        print("⚠️  No real payment found with ID: pay_RdEV52z75RQcyO")
        print("   (This is okay if you're in a fresh database)")
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 TEST SUMMARY")
    print("=" * 80)
    print("""
    If all tests show ✅ SECURITY SUCCESS, your replay attack protection is working!
    
    What this means:
    - Attackers CANNOT reuse payment IDs
    - Attackers CANNOT reuse signatures
    - Each payment can only activate ONE subscription
    - Database-level protection is active
    
    Without this protection:
    - Pay once = unlimited subscriptions
    - Potential loss: ₹10,000 - ₹1,00,000+ per attack
    """)
    print("=" * 80)


if __name__ == "__main__":
    test_replay_attack_protection()
