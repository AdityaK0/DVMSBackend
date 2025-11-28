# 🐛 Debugging: User Cache Not Invalidating

## The Problem
After updating vendor profile, `/me` API still returns old data because the user cache (`user:{user_id}`) is not being invalidated.

## Root Cause Found
The `@redis_cached` decorator was not working properly with `UserService.get_user(user)` because:
- It receives a **user object**, not a `user_id`
- The decorator was trying to extract `pk` from the object
- Cache key generation was failing

## What Was Fixed

### 1. UserService.get_user() - Manual Cache Handling
**Before:**
```python
@redis_cached("user", "user_id", ttl=60 * 60 * 5)
def get_user(user):
    # Decorator couldn't extract user.id properly
```

**After:**
```python
def get_user(user):
    user_id = user.id
    cache_key = f"user:{user_id}"
    
    # Manual cache check
    cached = cache.get(cache_key)
    if cached:
        return cached
    
    # Build fresh data
    data = {"user": UserSerializer(user).data}
    
    # Cache it
    cache.set(cache_key, data, timeout=60 * 60 * 5)
    return data
```

### 2. VendorUpdatedSubscriber - Better Logging
Added comprehensive logging to track cache invalidation:
```python
def __call__(self, event):
    logger.info(f"▶ VendorUpdatedSubscriber called for vendor {event.id}")
    
    user_id = event.metadata.get("user_id")
    vendor_id = event.id
    
    logger.info(f"📋 Invalidating caches - user_id: {user_id}, vendor_id: {vendor_id}")
    
    cache.delete(f"user:{user_id}")
    logger.info(f"🗑️  Deleted cache: user:{user_id}")
    
    # ... etc
```

### 3. Sync Mode (bg=False)
You already changed to sync mode, which is correct for immediate cache invalidation:
```python
VendorUpdated({...}).publish(bg=False)  # Executes immediately
```

---

## How to Test

### Method 1: Using the Test Script
```bash
cd /Users/upforcetech/simple/learnhub/ecs/management_V1/marketplace
python test_vendor_cache.py
```

This will:
1. Get a vendor from DB
2. Check current cache state
3. Update the vendor
4. Check cache state after update
5. Verify caches were invalidated

### Method 2: Manual API Testing
```bash
# 1. Call me_view to warm cache
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/users/me/

# 2. Update vendor
curl -X PUT \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"business_name": "New Name"}' \
  http://localhost:8000/api/vendors/YOUR_VENDOR_ID/

# 3. Call me_view again - should show new data
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/users/me/
```

### Method 3: Check Logs
Look for these log entries after vendor update:

```
# Event dispatched
⚡ Dispatching event 'vendor.updated' to 1 handler(s) [SYNC]

# Subscriber called
▶ VendorUpdatedSubscriber called for vendor 123

# Caches invalidated
📋 Invalidating caches - user_id: 456, vendor_id: 123
🗑️  Deleted cache: user:456
🗑️  Deleted cache: portfolio:123
🗑️  Deleted cache: vendor:123

# Next me_view call
❌ Redis Cache MISS: user:456
✅ Redis Cache SET: user:456
```

---

## Debugging Checklist

If cache is still not invalidating:

### 1. Check Event is Published
```python
# In VendorService.update_vendor(), add print:
print(f"🔥 Publishing VendorUpdated event for vendor {vendor.id}, user {vendor.user_id}")
```

### 2. Check Subscriber is Called
```python
# In VendorUpdatedSubscriber, check print output:
print(f"✅ User + vendor + portfolio cache invalidated for user:{user_id}, vendor:{vendor_id}")
```

### 3. Check Cache Keys Match
```python
# In Django shell:
from django.core.cache import cache

# Check what keys exist
import redis
r = redis.from_url("your_redis_url")
keys = r.keys("user:*")
print(keys)  # Should show user:123, etc.
```

### 4. Verify Sync Mode
```python
# In VendorService, ensure:
.publish(bg=False)  # NOT bg=True
```

### 5. Check Transaction Commits
```python
# Make sure transaction.on_commit is working:
from django.db import transaction

# In VendorService:
transaction.on_commit(lambda: print("🔥 Transaction committed!"))
```

---

## Expected Flow (Step by Step)

```
1. User calls: PUT /api/vendors/123/
   ↓
2. VendorService.update_vendor() executes
   ↓
3. DB transaction updates vendor
   ↓
4. transaction.on_commit() fires
   ↓
5. VendorUpdated event published (bg=False)
   ↓
6. EventBus.dispatch() called (SYNC mode)
   ↓
7. VendorUpdatedSubscriber.__call__() executes IMMEDIATELY
   ↓
8. cache.delete("user:456") executes
   ↓
9. Response returned to user
   ↓
10. User calls: GET /api/users/me/
    ↓
11. UserService.get_user() called
    ↓
12. cache.get("user:456") returns None (cache miss)
    ↓
13. Fresh data fetched from DB
    ↓
14. cache.set("user:456", data) stores new data
    ↓
15. User sees updated vendor data ✅
```

---

## Common Issues

### Issue 1: Event Not Firing
**Symptom:** No subscriber logs  
**Cause:** Event not registered in EVENT_ROUTES  
**Fix:** Check `apps/core/router.py`

### Issue 2: Wrong Cache Key
**Symptom:** Cache invalidated but me_view still cached  
**Cause:** Cache key mismatch  
**Fix:** Verify both use `user:{user_id}`

### Issue 3: Async Mode
**Symptom:** Cache invalidated too late  
**Cause:** Using `bg=True`  
**Fix:** Use `bg=False` for immediate invalidation

### Issue 4: Transaction Not Committed
**Symptom:** Event fires but DB not updated  
**Cause:** Transaction rolled back  
**Fix:** Check for exceptions in service

---

## Quick Verification

Run this in Django shell:
```python
from django.core.cache import cache
from apps.vendors.models import Vendor
from apps.vendors.services import VendorService

# Get a vendor
vendor = Vendor.objects.first()
user_id = vendor.user_id

# Warm cache
cache.set(f"user:{user_id}", {"test": "data"}, 300)

# Verify cache exists
print(cache.get(f"user:{user_id}"))  # Should show {"test": "data"}

# Update vendor
VendorService.update_vendor(vendor, {"business_name": "Test"}, context=None)

# Check cache again
print(cache.get(f"user:{user_id}"))  # Should be None if invalidation worked
```

---

## Summary of Changes

1. ✅ Fixed `UserService.get_user()` to manually handle caching
2. ✅ Added comprehensive logging to `VendorUpdatedSubscriber`
3. ✅ Using sync mode (`bg=False`) for immediate invalidation
4. ✅ Proper cache key: `user:{user_id}`
5. ✅ Created test script: `test_vendor_cache.py`

**The cache invalidation should now work correctly!** 🎉
