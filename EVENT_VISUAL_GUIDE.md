# Event System Architecture - Visual Guide

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CLIENT REQUEST                              │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          VIEW LAYER                                 │
│  • HTTP request handling                                            │
│  • Authentication/permissions                                       │
│  • Response formatting                                              │
│  ❌ NO business logic                                               │
│  ❌ NO event publishing                                             │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        SERVICE LAYER                                │
│  • Business logic                                                   │
│  • DB operations                                                    │
│  • Validation                                                       │
│  ✅ Event publishing (after commit)                                 │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    ▼                           ▼
          ┌──────────────────┐        ┌──────────────────┐
          │  DB Transaction  │        │  Event Published │
          │   (PostgreSQL)   │        │ (on_commit hook) │
          └──────────────────┘        └──────────────────┘
                                              │
                                              ▼
                                    ┌──────────────────┐
                                    │    EventBus      │
                                    │   (dispatcher)   │
                                    └──────────────────┘
                                              │
                                              ▼
                                    ┌──────────────────┐
                                    │  Celery Queue    │
                                    │     (Redis)      │
                                    └──────────────────┘
                                              │
                                              ▼
                                    ┌──────────────────┐
                                    │  Celery Worker   │
                                    │  (background)    │
                                    └──────────────────┘
                                              │
                                              ▼
                                    ┌──────────────────┐
                                    │   Subscriber     │
                                    │   (handler)      │
                                    └──────────────────┘
                                              │
                                              ▼
                                    ┌──────────────────┐
                                    │  Redis Cache     │
                                    │    (updated)     │
                                    └──────────────────┘
```

---

## 🔄 Event Lifecycle

### 1. Product Creation Flow

```
POST /api/products/
         │
         ▼
┌─────────────────────┐
│  create_product()   │  ← View
│  (views.py)         │
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│ ProductService.     │  ← Service
│ create_product()    │
└─────────────────────┘
         │
         ├─► Product.objects.create(...)  ← DB write
         │
         └─► transaction.on_commit(       ← Event publish
                 lambda: ProductCreated({
                     "id": product.id,
                     "action": "created",
                     "data": {...},
                     "metadata": {...}
                 }).publish(bg=True)
             )
         │
         ▼
┌─────────────────────┐
│    EventBus.        │  ← Dispatcher
│    dispatch()       │
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│  Celery Task        │  ← Async processing
│  handle_event()     │
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│ ProductCreated      │  ← Subscriber
│ Subscriber()        │
└─────────────────────┘
         │
         ├─► cache.set("product:123", data)  ← Cache warm
         │
         └─► cache.delete("vendor:X:products")  ← Invalidate list
```

---

## 📦 Component Responsibilities

```
┌────────────────────────────────────────────────────────────┐
│                      COMPONENTS                            │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  BaseEvent                                                 │
│  ├─ Defines event structure                               │
│  ├─ Provides .publish() method                            │
│  └─ Sets payload as attributes                            │
│                                                            │
│  EventBus                                                  │
│  ├─ Routes events to subscribers                          │
│  ├─ Handles sync/async dispatch                           │
│  └─ Logs dispatch activity                                │
│                                                            │
│  EVENT_ROUTES                                              │
│  ├─ Maps event names to subscribers                       │
│  └─ Single source of truth for routing                    │
│                                                            │
│  Celery Task (handle_event)                               │
│  ├─ Executes subscribers asynchronously                   │
│  ├─ Retries on failure                                    │
│  └─ Logs execution                                        │
│                                                            │
│  Subscribers                                               │
│  ├─ Update Redis cache                                    │
│  ├─ Handle errors gracefully                              │
│  └─ Log all actions                                       │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

---

## 🎯 Event Types & Their Flows

### ProductCreated
```
Service: ProductService.create_product()
   ↓
Event: ProductCreated
   ↓
Subscriber: ProductCreatedSubscriber
   ↓
Actions:
   • cache.set("product:{id}", data)
   • cache.delete("vendor:{id}:products")
```

### ProductUpdated
```
Service: ProductService.update_product()
   ↓
Event: ProductUpdated
   ↓
Subscriber: ProductUpdatedSubscriber
   ↓
Actions:
   • cache.delete("product:{id}")
   • cache.set("product:{id}", data)
   • cache.delete("vendor:{id}:products")
```

### ProductDeleted
```
Service: ProductService.delete_product()
   ↓
Event: ProductDeleted
   ↓
Subscriber: ProductDeletedSubscriber
   ↓
Actions:
   • cache.delete("product:{id}")
   • cache.delete("vendor:{id}:products")
```

### VendorUpdated
```
Service: VendorService.update_vendor()
   ↓
Event: VendorUpdated
   ↓
Subscriber: VendorUpdatedSubscriber
   ↓
Actions:
   • cache.delete("vendor:{id}")
   • cache.set("vendor:{id}", data)
   • cache.delete("portfolio:{id}")
```

---

## 🔍 Cache Strategy

```
┌─────────────────────────────────────────────────────────────┐
│                    REDIS CACHE KEYS                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  product:{id}                                               │
│  ├─ Stores: Full product data                              │
│  ├─ TTL: 5 hours                                            │
│  ├─ Updated by: ProductCreated, ProductUpdated             │
│  └─ Deleted by: ProductDeleted                             │
│                                                             │
│  vendor:{id}                                                │
│  ├─ Stores: Full vendor data                               │
│  ├─ TTL: 5 hours                                            │
│  ├─ Updated by: VendorUpdated                              │
│  └─ Deleted by: -                                           │
│                                                             │
│  vendor:{id}:products                                       │
│  ├─ Stores: Product list for vendor                        │
│  ├─ TTL: Varies                                             │
│  ├─ Updated by: -                                           │
│  └─ Deleted by: ProductCreated, ProductUpdated, Deleted    │
│                                                             │
│  portfolio:{id}                                             │
│  ├─ Stores: Portfolio data                                 │
│  ├─ TTL: Varies                                             │
│  ├─ Updated by: -                                           │
│  └─ Deleted by: VendorUpdated                              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## ⚡ Performance Timeline

```
Time (ms)    Action                          Location
─────────────────────────────────────────────────────────────
0            HTTP request arrives            View
1            Service method called           Service
5            DB write starts                 PostgreSQL
20           DB write completes              PostgreSQL
21           transaction.on_commit fires     Django
22           Event published                 EventBus
23           Celery task queued              Redis
25           HTTP response sent              View
─────────────────────────────────────────────────────────────
             ⬇ Background processing ⬇
─────────────────────────────────────────────────────────────
50           Celery worker picks up task     Celery
55           Subscriber executes             Subscriber
60           Redis cache updated             Redis
65           Task completes                  Celery
```

**Total user-facing latency: ~25ms**  
**Total background processing: ~40ms**

---

## 🛡️ Error Handling Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    ERROR SCENARIOS                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Scenario 1: DB Transaction Fails                          │
│  ├─ Service raises exception                               │
│  ├─ Transaction rolls back                                 │
│  ├─ on_commit hook never fires                             │
│  └─ ✅ No event published (correct!)                       │
│                                                             │
│  Scenario 2: Event Dispatch Fails                          │
│  ├─ EventBus catches exception                             │
│  ├─ Logs error                                             │
│  └─ ❌ Event lost (acceptable for cache updates)           │
│                                                             │
│  Scenario 3: Celery Task Fails                             │
│  ├─ Task catches exception                                 │
│  ├─ Retries up to 3 times                                  │
│  ├─ Logs each attempt                                      │
│  └─ ⚠️  Eventually gives up (logged)                       │
│                                                             │
│  Scenario 4: Subscriber Fails                              │
│  ├─ Subscriber catches exception                           │
│  ├─ Logs error with full traceback                         │
│  ├─ Other subscribers still execute                        │
│  └─ ⚠️  Cache may be stale (will refresh on next read)     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔐 Multi-Instance Safety

```
┌──────────────────────────────────────────────────────────────┐
│              MULTI-INSTANCE DEPLOYMENT                       │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  EC2 Instance 1          EC2 Instance 2          EC2 Instance 3
│       │                       │                       │
│       ├─► Django App          ├─► Django App          ├─► Django App
│       │                       │                       │
│       └─► Celery Worker       └─► Celery Worker       └─► Celery Worker
│                               │
│                               ▼
│                    ┌──────────────────────┐
│                    │    Shared Redis      │
│                    │  (Global Cache +     │
│                    │   Celery Broker)     │
│                    └──────────────────────┘
│                               │
│                               ▼
│                    ┌──────────────────────┐
│                    │   PostgreSQL DB      │
│                    │  (Single Source of   │
│                    │       Truth)         │
│                    └──────────────────────┘
│                                                              │
│  ✅ Events work correctly across all instances              │
│  ✅ Redis cache is global and consistent                    │
│  ✅ Any worker can process any event                        │
│  ✅ No local state dependencies                             │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## 📊 Monitoring & Observability

```
┌─────────────────────────────────────────────────────────────┐
│                    LOG LEVELS                               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  INFO  - Normal operation                                  │
│  ├─ "📤 Dispatching event 'product.created'..."            │
│  ├─ "🔥 Celery executing event: product.created"           │
│  ├─ "▶ ProductCreatedSubscriber called for product 123"    │
│  └─ "✅ Product cache warmed: product:123"                 │
│                                                             │
│  WARNING - Recoverable issues                              │
│  ├─ "⚠️  No handlers registered for event: X"              │
│  └─ "⚠️  Handler not found: X"                             │
│                                                             │
│  ERROR - Failures                                          │
│  ├─ "❌ Failed to dispatch event to Celery: X"             │
│  ├─ "❌ Handler X failed: Y"                               │
│  └─ "❌ ProductCreatedSubscriber failed: Z"                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎯 Decision Tree: Should I Use an Event?

```
                    State Changed?
                         │
           ┌─────────────┴─────────────┐
           │                           │
          YES                         NO
           │                           │
           ▼                           ▼
    Side Effects Needed?        ❌ NO EVENT
    (cache, notifications)
           │
    ┌──────┴──────┐
    │             │
   YES           NO
    │             │
    ▼             ▼
 ✅ USE        ❌ NO EVENT
   EVENT
    │
    ▼
 Heavy Operation?
    │
    ┌──────┴──────┐
    │             │
   YES           NO
    │             │
    ▼             ▼
 bg=True      bg=False
 (async)       (sync)
```

---

This visual guide should help you understand the complete event architecture at a glance!
