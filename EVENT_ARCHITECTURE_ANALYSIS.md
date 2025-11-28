# Event Architecture Analysis & Fixes

## 🔍 Current Issues Identified

### 1. **Critical Bug in ProductUpdatedSubscriber**
**Location:** `apps/core/handlers/product_handler.py:15-16`

```python
cache.delete(product_cache_key)  # ❌ USING UNDEFINED VARIABLE
product_cache_key = f"product:{product_id}"  # ❌ DEFINED AFTER USE
```

**Impact:** This causes a `NameError` and prevents the subscriber from running at all.

---

### 2. **Wrong Event Payload in VendorUpdatedSubscriber**
**Location:** `apps/core/handlers/vendor_handler.py:11`

```python
vendor_id = event.user_id  # ❌ WRONG ATTRIBUTE
```

**Actual payload sent:** `{"vendor": vendor.id, "data": serializer}`  
**Expected:** `event.vendor` not `event.user_id`

---

### 3. **Duplicate Event Publishing (Signals + Service Layer)**
**Locations:**
- `apps/products/signals.py:39` - Signal triggers event on EVERY save
- `apps/products/services.py:142-145` - Service also triggers event

**Impact:** Events fire twice for the same action, causing:
- Duplicate cache updates
- Unnecessary Celery tasks
- Confusion in logs

---

### 4. **Events Triggered on Product Creation (Unnecessary)**
**Location:** `apps/products/signals.py:24-29`

```python
if created:
    action = "CREATED"
    # ... publishes ProductUpdated event
```

**Problem:** Creating a product shouldn't trigger an "updated" event. There's no cache to invalidate yet.

---

### 5. **Sync Events Used in Signals (Wrong Pattern)**
**Location:** `apps/products/signals.py:39`

```python
ProductUpdated(payload).publish()  # SYNC - blocks DB transaction
```

**Problem:** 
- Signals run inside DB transactions
- Sync event handlers block the transaction
- Should be async or use `transaction.on_commit()`

---

### 6. **Missing Event for Product Creation**
**Current:** No event published when product is created  
**Impact:** No cache warming, no downstream notifications

---

### 7. **VendorService Not Using `transaction.on_commit()`**
**Location:** `apps/vendors/services.py:38-41`

```python
VendorUpdated({...}).publish(bg=True)  # ❌ Not wrapped in on_commit
```

**Problem:** Event fires before transaction commits, potential race condition

---

### 8. **Inconsistent Event Payload Structure**
- `ProductUpdated`: `{"product_id": X, "data": {...}}`
- `VendorUpdated`: `{"vendor": X, "data": {...}}`  
- `ProductDeleted`: `{"product_id": X, "vendor_id": Y, "is_active": Z, ...}`

**Problem:** Subscribers need different logic for each event type

---

### 9. **ProductDeletedSubscriber Uses Wrong Payload**
**Location:** `apps/core/handlers/product_handler.py:29`

```python
key = f"vendor:{event.vendor_id}:products"
```

**Problem:** `ProductDeleted` event is never published from service layer, only from signals. The payload structure doesn't match.

---

### 10. **No Event Published from `ProductService.delete_product()`**
**Location:** `apps/products/services.py:151-162`

The service does soft delete but never publishes `ProductDeleted` event.

---

## ✅ Recommended Architecture

### **Clear Separation of Concerns**

```
┌─────────────────┐
│   View Layer    │  ← HTTP handling only
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Service Layer   │  ← Business logic + Event publishing
└────────┬────────┘
         │
         ▼ (publishes event)
┌─────────────────┐
│   EventBus      │  ← Routes events to subscribers
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Subscribers    │  ← Cache updates, side effects
└─────────────────┘
```

---

## 🎯 When to Use Events

### ✅ **Use Async Events (bg=True) When:**
1. **Heavy operations:** Elasticsearch indexing, external API calls
2. **Cross-instance updates:** Redis cache updates (global state)
3. **Non-critical side effects:** Sending notifications, logging analytics
4. **Long-running tasks:** Image processing, report generation

### ✅ **Use Sync Events (bg=False) When:**
1. **Same-transaction validation:** Need immediate feedback
2. **Local cache updates:** In-memory cache (not Redis)
3. **Critical business logic:** Must complete before response

### ❌ **Don't Use Events When:**
1. **GET requests:** Never publish events on reads
2. **Simple field updates:** Direct DB update is enough
3. **No downstream effects:** No cache, no notifications, no indexing

---

## 🔧 Corrected Architecture

### **Event Publishing Rules**

| Action | Event Name | When | Mode | Published From |
|--------|-----------|------|------|----------------|
| Product Created | `product.created` | After DB commit | async | Service layer |
| Product Updated | `product.updated` | After DB commit | async | Service layer |
| Product Deleted | `product.deleted` | After DB commit | async | Service layer |
| Vendor Updated | `vendor.updated` | After DB commit | async | Service layer |

### **Remove Signal-Based Events**
- Delete `apps/products/signals.py` entirely
- All events published from service layer only
- Use `transaction.on_commit()` for all events

---

## 📋 Implementation Plan

### Phase 1: Fix Critical Bugs
1. Fix `ProductUpdatedSubscriber` variable order
2. Fix `VendorUpdatedSubscriber` payload attribute
3. Standardize event payload structure

### Phase 2: Remove Duplicate Events
1. Delete signal-based event publishing
2. Keep only service-layer events

### Phase 3: Add Missing Events
1. Add `ProductCreated` event
2. Publish `ProductDeleted` from service layer

### Phase 4: Ensure Consistency
1. Wrap all events in `transaction.on_commit()`
2. Use async mode for all Redis cache updates
3. Standardize payload structure

---

## 🎨 Final Event Payload Standard

```python
# All events follow this structure:
{
    "id": <primary_key>,           # Always use "id" not "product_id" or "vendor"
    "action": "created|updated|deleted",
    "data": <serialized_object>,   # Full serialized data
    "metadata": {                  # Optional metadata
        "vendor_id": X,
        "old_value": Y,
        # ... other context
    }
}
```

---

## 🚀 Production Checklist

- [ ] All events use `transaction.on_commit()`
- [ ] No events in GET endpoints
- [ ] All Redis updates are async
- [ ] Consistent payload structure
- [ ] No duplicate event publishing
- [ ] Proper error handling in subscribers
- [ ] Logging for debugging
- [ ] No race conditions
- [ ] Works in multi-instance environment
