# 🔄 Vendor Update Cache Strategy

## The Problem

In your system, **Vendor and User are linked** (`vendor.user`). When a vendor profile is updated:
- The vendor data changes
- The user context (accessed via `me_view`) also needs to reflect these changes
- Multiple cache keys need to be invalidated

## The Solution

When `VendorUpdated` event fires, the subscriber invalidates **3 cache keys**:

### 1. Vendor Cache
```python
vendor:{vendor_id}
```
Stores vendor-specific data.

### 2. User Cache (CRITICAL for me_view)
```python
user:{user_id}
```
Stores user context returned by `me_view`. This includes vendor data, so it MUST be invalidated when vendor updates.

### 3. Portfolio Cache
```python
portfolio:{vendor_id}
```
Vendor profile changes may affect portfolio display.

---

## Event Flow

```
VendorService.update_vendor()
    ↓
VendorUpdated event published with:
{
    "id": vendor.id,
    "action": "updated",
    "data": {...},
    "metadata": {
        "user_id": vendor.user_id  ← CRITICAL!
    }
}
    ↓
VendorUpdatedSubscriber executes
    ↓
Invalidates 3 caches:
    • cache.set("vendor:{vendor_id}", data)
    • cache.delete("user:{user_id}")      ← Ensures me_view gets fresh data
    • cache.delete("portfolio:{vendor_id}")
```

---

## Why This Matters

### Before Fix:
```python
# User updates vendor profile
PUT /api/vendors/123/

# Vendor cache updated ✅
# User cache NOT invalidated ❌

# User calls me_view
GET /api/users/me/

# Returns STALE user data ❌
# Vendor changes not reflected
```

### After Fix:
```python
# User updates vendor profile
PUT /api/vendors/123/

# Vendor cache updated ✅
# User cache invalidated ✅

# User calls me_view
GET /api/users/me/

# Cache miss, fetches fresh data from DB ✅
# Vendor changes reflected immediately ✅
```

---

## Code References

### Event Publishing (VendorService)
```python
# apps/vendors/services.py

transaction.on_commit(lambda: VendorUpdated({
    "id": vendor.id,
    "action": "updated",
    "data": serializer,
    "metadata": {
        "user_id": vendor.user_id  # ← Pass user_id for cache invalidation
    }
}).publish(bg=True))
```

### Cache Invalidation (VendorUpdatedSubscriber)
```python
# apps/core/handlers/vendor_handler.py

def __call__(self, event):
    vendor_id = event.id
    user_id = event.metadata.get("user_id")
    
    # Update vendor cache
    cache.set(f"vendor:{vendor_id}", vendor_data, timeout=60*60*5)
    
    # Invalidate user cache (for me_view)
    if user_id:
        cache.delete(f"user:{user_id}")
    
    # Invalidate portfolio cache
    cache.delete(f"portfolio:{vendor_id}")
```

### me_view Usage
```python
# apps/users/views.py

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me_view(request):
    user = request.user
    data = UserService.get_user(user)  # Uses cache key: user:{user.id}
    return Response(data)
```

---

## Testing

### Test Vendor Update → me_view Refresh

```bash
# 1. Get initial user data
GET /api/users/me/
# Response includes vendor data

# 2. Update vendor profile
PUT /api/vendors/123/
{
    "business_name": "New Business Name"
}

# 3. Get user data again
GET /api/users/me/
# Response should show "New Business Name" ✅

# Check logs:
# ✅ Vendor cache updated: vendor:123
# 🗑️  Invalidated user cache: user:456
# 🗑️  Invalidated portfolio cache: portfolio:123
```

---

## Key Takeaway

**When vendor data changes, user cache MUST be invalidated** because:
- Vendor and User are linked entities
- `me_view` returns user context which includes vendor data
- Stale user cache = stale vendor data in `me_view`

This is now handled automatically by `VendorUpdatedSubscriber`! 🎉
