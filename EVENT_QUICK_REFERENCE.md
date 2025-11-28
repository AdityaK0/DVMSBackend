# 🎯 Event System - Quick Reference

## When to Use Events

| Scenario | Use Event? | Mode | Why |
|----------|-----------|------|-----|
| Product created | ✅ Yes | `bg=True` | Warm cache, notify subscribers |
| Product updated | ✅ Yes | `bg=True` | Update cache, sync ES |
| Product deleted | ✅ Yes | `bg=True` | Clear cache, cleanup |
| Vendor updated | ✅ Yes | `bg=True` | Update cache |
| GET product | ❌ No | - | No state change |
| GET product list | ❌ No | - | No state change |
| Simple field update | ❌ No | - | Direct DB is enough |

---

## Event Publishing Template

```python
from django.db import transaction
from apps.core.events import YourEvent

# Inside your service method:
transaction.on_commit(lambda: YourEvent({
    "id": object.id,
    "action": "created|updated|deleted",
    "data": serialized_data,
    "metadata": {
        "vendor_id": vendor.id,
        # ... other context
    }
}).publish(bg=True))
```

---

## Subscriber Template

```python
import logging
from django.core.cache import cache

logger = logging.getLogger(__name__)


class YourSubscriber:
    queue = "default"

    def __call__(self, event):
        logger.info(f"▶ YourSubscriber called for {event.id}")

        try:
            # Access event data
            object_id = event.id
            object_data = event.data
            vendor_id = event.metadata.get("vendor_id")

            # Update Redis cache
            cache_key = f"your_model:{object_id}"
            cache.set(cache_key, object_data, timeout=60 * 60 * 5)
            logger.info(f"✅ Cache updated: {cache_key}")

        except Exception as e:
            logger.error(f"❌ YourSubscriber failed: {e}", exc_info=True)
```

---

## Common Patterns

### Pattern 1: Cache Warming (Create)
```python
# Subscriber sets cache after creation
cache.set(f"product:{product_id}", product_data, timeout=60*60*5)
```

### Pattern 2: Cache Update (Update)
```python
# Subscriber deletes then sets cache
cache.delete(f"product:{product_id}")
cache.set(f"product:{product_id}", product_data, timeout=60*60*5)
```

### Pattern 3: Cache Invalidation (Delete)
```python
# Subscriber deletes cache
cache.delete(f"product:{product_id}")
```

### Pattern 4: Related Cache Invalidation
```python
# Invalidate related caches
cache.delete(f"vendor:{vendor_id}:products")
cache.delete(f"portfolio:{vendor_id}")
```

---

## Debugging Commands

```bash
# Check if Celery is running
ps aux | grep celery

# Start Celery worker
celery -A marketplace worker --loglevel=info

# Check Redis
redis-cli ping

# View Redis keys
redis-cli keys "product:*"

# Get Redis value
redis-cli get "product:123"

# Clear all Redis cache
redis-cli FLUSHDB
```

---

## Common Issues & Fixes

| Issue | Cause | Fix |
|-------|-------|-----|
| Events not firing | Celery not running | Start Celery worker |
| Subscriber not called | Not registered in `EVENT_ROUTES` | Add to router |
| Cache not updating | Wrong cache key | Check subscriber logs |
| Duplicate events | Signal + service publishing | Remove signal events |
| Event fires before commit | No `transaction.on_commit()` | Wrap in `on_commit` |

---

## File Locations

```
apps/core/
├── events.py              # Event definitions
├── event_bus.py           # Event dispatcher
├── tasks.py               # Celery task handler
├── router.py              # Event → Subscriber mapping
└── handlers/
    ├── product_handler.py # Product subscribers
    └── vendor_handler.py  # Vendor subscribers

apps/products/
└── services.py            # Publishes product events

apps/vendors/
└── services.py            # Publishes vendor events
```

---

## Redis Cache Keys

```
product:{id}                    # Single product data
vendor:{id}                     # Single vendor data
vendor:{id}:products            # Vendor's product list
portfolio:{id}                  # Portfolio data
user:{id}                       # User data
```

---

## Event Payload Structure

```python
{
    "id": 123,                  # Primary key
    "action": "created",        # created|updated|deleted
    "data": {                   # Full serialized object
        "id": 123,
        "name": "...",
        # ... all fields
    },
    "metadata": {               # Optional context
        "vendor_id": 456,
        # ... other metadata
    }
}
```

---

## Testing Checklist

- [ ] Celery worker is running
- [ ] Redis is accessible
- [ ] Event is registered in `EVENT_ROUTES`
- [ ] Event is published with `bg=True`
- [ ] Event uses `transaction.on_commit()`
- [ ] Subscriber logs appear in Celery
- [ ] Redis cache is updated
- [ ] No errors in logs

---

## Performance Metrics

| Operation | Expected Time |
|-----------|--------------|
| Event dispatch | 1-3ms |
| Celery queuing | 5-10ms |
| Subscriber execution | 10-50ms |
| Redis cache set | 1-5ms |
| Total (async) | ~20-70ms background |

---

## Remember

✅ **DO:**
- Publish events from service layer
- Use `transaction.on_commit()`
- Use `bg=True` for cache updates
- Follow standardized payload
- Log everything

❌ **DON'T:**
- Publish events from GET endpoints
- Publish events from signals
- Publish before transaction commits
- Use inconsistent payload structure
- Ignore errors silently
