#!/usr/bin/env python
"""
Test script to verify vendor update → user cache invalidation flow.

Run this after updating a vendor profile to check if caches are properly invalidated.
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'marketplace.settings')
django.setup()

from django.core.cache import cache
from apps.vendors.models import Vendor
from apps.users.models import User

def test_cache_invalidation():
    """Test that vendor update invalidates user cache."""
    
    print("\n" + "="*60)
    print("CACHE INVALIDATION TEST")
    print("="*60 + "\n")
    
    # Get a vendor
    vendor = Vendor.objects.first()
    if not vendor:
        print("❌ No vendors found in database")
        return
    
    user = vendor.user
    
    print(f"Testing with:")
    print(f"  Vendor ID: {vendor.id}")
    print(f"  User ID: {user.id}")
    print(f"  Business Name: {vendor.business_name}")
    print()
    
    # Check current cache state
    print("Current cache state:")
    user_cache = cache.get(f"user:{user.id}")
    vendor_cache = cache.get(f"vendor:{vendor.id}")
    portfolio_cache = cache.get(f"portfolio:{vendor.id}")
    
    print(f"  user:{user.id} → {'EXISTS' if user_cache else 'EMPTY'}")
    print(f"  vendor:{vendor.id} → {'EXISTS' if vendor_cache else 'EMPTY'}")
    print(f"  portfolio:{vendor.id} → {'EXISTS' if portfolio_cache else 'EMPTY'}")
    print()
    
    # Now update the vendor
    print("Updating vendor business_name...")
    old_name = vendor.business_name
    new_name = f"{old_name} (Updated)"
    
    from apps.vendors.services import VendorService
    
    try:
        VendorService.update_vendor(
            vendor=vendor,
            data={"business_name": new_name},
            context=None
        )
        print(f"✅ Vendor updated: {old_name} → {new_name}")
    except Exception as e:
        print(f"❌ Update failed: {e}")
        return
    
    print()
    
    # Check cache state after update
    print("Cache state after update:")
    user_cache_after = cache.get(f"user:{user.id}")
    vendor_cache_after = cache.get(f"vendor:{vendor.id}")
    portfolio_cache_after = cache.get(f"portfolio:{vendor.id}")
    
    print(f"  user:{user.id} → {'EXISTS' if user_cache_after else 'EMPTY ✅'}")
    print(f"  vendor:{vendor.id} → {'EXISTS' if vendor_cache_after else 'EMPTY ✅'}")
    print(f"  portfolio:{vendor.id} → {'EXISTS' if portfolio_cache_after else 'EMPTY ✅'}")
    print()
    
    # Verify
    if not user_cache_after and not portfolio_cache_after:
        print("✅ SUCCESS: Caches properly invalidated!")
        print("   me_view will now fetch fresh data from DB")
    else:
        print("❌ FAILURE: Some caches still exist")
        print("   Check if VendorUpdatedSubscriber is being called")
    
    print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    test_cache_invalidation()
