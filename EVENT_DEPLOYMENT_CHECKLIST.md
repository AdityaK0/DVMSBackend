# 🚀 Event System Migration Checklist

## Pre-Deployment Checklist

### 1. Code Review
- [ ] All files updated correctly
- [ ] No syntax errors
- [ ] Imports are correct
- [ ] Event names match in router
- [ ] Payload structures are standardized

### 2. Local Testing

#### Start Services
```bash
# Terminal 1: Start Django
python manage.py runserver

# Terminal 2: Start Celery
celery -A marketplace worker --loglevel=info

# Terminal 3: Monitor Redis
redis-cli monitor
```

#### Test Product Creation
```bash
# Create a product via API
curl -X POST http://localhost:8000/api/products/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Product",
    "price": 99.99,
    "category": 1,
    "image_urls": ["https://example.com/image.jpg"]
  }'

# Expected logs:
# Django: "📤 Dispatching event 'product.created' to 1 handler(s) [ASYNC]"
# Celery: "🔥 Celery executing event: product.created → ProductCreatedSubscriber"
# Celery: "▶ ProductCreatedSubscriber called for product 123"
# Celery: "✅ Product cache warmed: product:123"
```

#### Test Product Update
```bash
# Update a product
curl -X PUT http://localhost:8000/api/products/123/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Updated Product"
  }'

# Expected logs:
# Django: "📤 Dispatching event 'product.updated' to 1 handler(s) [ASYNC]"
# Celery: "🔥 Celery executing event: product.updated → ProductUpdatedSubscriber"
# Celery: "✅ Product cache updated: product:123"
```

#### Test Product Deletion
```bash
# Delete a product
curl -X DELETE http://localhost:8000/api/products/123/ \
  -H "Authorization: Bearer YOUR_TOKEN"

# Expected logs:
# Django: "📤 Dispatching event 'product.deleted' to 1 handler(s) [ASYNC]"
# Celery: "🔥 Celery executing event: product.deleted → ProductDeletedSubscriber"
# Celery: "🗑️  Deleted product cache: product:123"
```

#### Verify Redis Cache
```bash
# Check if cache was set
redis-cli get "product:123"

# Should return JSON with product data
```

### 3. Verify No Duplicate Events
```bash
# Create a product and count log entries
# Should see EXACTLY:
# - 1 "Dispatching event" log
# - 1 "Celery executing event" log
# - 1 "Subscriber called" log

# If you see 2x of each, signals are still firing (BAD!)
```

### 4. Test Error Scenarios

#### Test with Celery Stopped
```bash
# Stop Celery worker
# Create a product
# Should see: Event queued but not processed
# Start Celery
# Should see: Event processed from queue
```

#### Test with Redis Down
```bash
# Stop Redis
# Create a product
# Should see: Error logged, but request succeeds
# Start Redis
# Cache will be empty (acceptable)
```

### 5. Performance Testing
```bash
# Measure response time
time curl -X POST http://localhost:8000/api/products/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{...}'

# Should be < 100ms (event is async)
```

---

## Deployment Checklist

### 1. Pre-Deployment
- [ ] All tests pass locally
- [ ] Code reviewed and approved
- [ ] Documentation updated
- [ ] Rollback plan prepared

### 2. Deployment Steps

#### Step 1: Deploy Code
```bash
# Pull latest code
git pull origin main

# Install dependencies (if any)
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --noinput
```

#### Step 2: Restart Services
```bash
# Restart Django (depends on your setup)
sudo systemctl restart gunicorn
# or
sudo supervisorctl restart django

# Restart Celery workers
sudo systemctl restart celery
# or
sudo supervisorctl restart celery
```

#### Step 3: Verify Services
```bash
# Check Django is running
curl http://localhost:8000/health/

# Check Celery is running
celery -A marketplace inspect active

# Check Redis is accessible
redis-cli ping
```

### 3. Post-Deployment Verification

#### Verify Events are Working
```bash
# Create a test product
# Check logs for event flow
tail -f /var/log/django/app.log
tail -f /var/log/celery/worker.log
```

#### Verify Cache Updates
```bash
# Create/update a product
# Check Redis cache
redis-cli get "product:123"
```

#### Monitor for Errors
```bash
# Watch for errors in logs
tail -f /var/log/django/app.log | grep ERROR
tail -f /var/log/celery/worker.log | grep ERROR
```

### 4. Smoke Tests

- [ ] Create product → verify cache warmed
- [ ] Update product → verify cache updated
- [ ] Delete product → verify cache cleared
- [ ] Update vendor → verify cache updated
- [ ] No duplicate events in logs
- [ ] No errors in logs

---

## Rollback Plan

### If Something Goes Wrong

#### Option 1: Quick Fix
```bash
# If minor issue, fix and redeploy
git commit -m "Fix: event system issue"
git push
# Redeploy
```

#### Option 2: Rollback
```bash
# Revert to previous version
git revert HEAD
git push
# Redeploy

# Or checkout previous commit
git checkout <previous-commit-hash>
# Redeploy
```

#### Option 3: Disable Events Temporarily
```python
# In EventBus.dispatch(), add at the top:
def dispatch(event, bg=False):
    logger.warning("Events temporarily disabled")
    return True  # No-op
    
    # ... rest of code
```

---

## Monitoring Checklist

### Day 1 After Deployment
- [ ] Check error logs every hour
- [ ] Monitor Celery queue length
- [ ] Monitor Redis memory usage
- [ ] Verify cache hit rates
- [ ] Check response times

### Week 1 After Deployment
- [ ] Review error logs daily
- [ ] Monitor Celery task success rate
- [ ] Check for any duplicate events
- [ ] Verify cache consistency
- [ ] Collect performance metrics

### Ongoing
- [ ] Set up alerts for Celery failures
- [ ] Set up alerts for Redis issues
- [ ] Monitor cache hit/miss ratio
- [ ] Track event processing times

---

## Common Issues & Solutions

### Issue: Events Not Firing
**Symptoms:** No logs, cache not updating  
**Check:**
- [ ] Is Celery running?
- [ ] Is Redis accessible?
- [ ] Are events registered in EVENT_ROUTES?
- [ ] Is event name spelled correctly?

**Solution:**
```bash
# Restart Celery
sudo systemctl restart celery

# Check Celery status
celery -A marketplace inspect active
```

### Issue: Duplicate Events
**Symptoms:** 2x logs for each event  
**Check:**
- [ ] Are signals still publishing events?
- [ ] Is service layer publishing twice?

**Solution:**
- Verify `signals.py` has no event publishing
- Check service layer only publishes once

### Issue: Cache Not Updating
**Symptoms:** Stale data in cache  
**Check:**
- [ ] Is subscriber executing?
- [ ] Are cache keys correct?
- [ ] Is Redis accessible?

**Solution:**
```bash
# Check subscriber logs
tail -f /var/log/celery/worker.log | grep Subscriber

# Verify Redis
redis-cli ping
redis-cli keys "product:*"
```

### Issue: Slow Response Times
**Symptoms:** Requests taking > 200ms  
**Check:**
- [ ] Are events using bg=True?
- [ ] Is transaction.on_commit() used?
- [ ] Are there blocking operations?

**Solution:**
- Ensure all events use `bg=True`
- Verify `transaction.on_commit()` is used
- Check for sync operations in service layer

---

## Success Criteria

### ✅ Deployment is Successful When:
- [ ] All CRUD operations work correctly
- [ ] Events fire for every state change
- [ ] Cache updates correctly
- [ ] No duplicate events
- [ ] No errors in logs
- [ ] Response times < 100ms
- [ ] Celery tasks complete successfully
- [ ] Redis cache hit rate > 80%

### ✅ System is Healthy When:
- [ ] Celery queue length < 100
- [ ] Redis memory usage stable
- [ ] No failed Celery tasks
- [ ] Cache hit rate > 80%
- [ ] Response times < 100ms
- [ ] No errors in logs

---

## Emergency Contacts

### If You Need Help:
1. Check documentation files:
   - `EVENT_REFACTOR_SUMMARY.md`
   - `EVENT_IMPLEMENTATION_GUIDE.md`
   - `EVENT_QUICK_REFERENCE.md`

2. Check logs:
   - Django: `/var/log/django/app.log`
   - Celery: `/var/log/celery/worker.log`
   - Redis: `redis-cli monitor`

3. Debug commands:
   ```bash
   # Check Celery
   celery -A marketplace inspect active
   celery -A marketplace inspect stats
   
   # Check Redis
   redis-cli info
   redis-cli keys "*"
   
   # Check Django
   python manage.py shell
   >>> from django.core.cache import cache
   >>> cache.get("product:123")
   ```

---

## Final Checklist Before Going Live

- [ ] All local tests pass
- [ ] Code reviewed
- [ ] Documentation complete
- [ ] Rollback plan ready
- [ ] Monitoring set up
- [ ] Team notified
- [ ] Backup taken
- [ ] Deployment window scheduled
- [ ] Stakeholders informed

---

**Good luck with your deployment! 🚀**

Remember: Events are now simple, reliable, and production-ready. Trust the system!
