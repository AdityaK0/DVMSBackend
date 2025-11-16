# Events & Festival Campaign Tool - API Reference

## Overview

Complete DRF module for automated events and festival campaign management. All endpoints require vendor authentication.

**Base URL:** `/api/vendor/`

## Authentication

All endpoints require:
- JWT Authentication
- Vendor role (`request.user.role == 'vendor'`)

---

## 1. Event CRUD API

### List Events
```
GET /api/vendor/events/
```
Returns paginated list of events for the authenticated vendor.

**Response:**
```json
{
  "count": 10,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "title": "Diwali Sale",
      "description": "...",
      "start_date": "2024-11-01T00:00:00Z",
      "end_date": "2024-11-15T00:00:00Z",
      "status": "active",
      "vendor_name": "My Business",
      ...
    }
  ]
}
```

### Create Event
```
POST /api/vendor/events/
```

**Request Body:**
```json
{
  "title": "Diwali Sale",
  "description": "Special Diwali offers",
  "start_date": "2024-11-01T00:00:00Z",
  "end_date": "2024-11-15T00:00:00Z",
  "status": "draft",
  "festival_template_id": "diwali",
  "custom_message": "Flat 40% off!",
  "selected_products": [1, 2, 3]
}
```

**Validation:**
- `start_date` must be before `end_date`
- `status` must be: `draft`, `scheduled`, `active`, `completed`, `cancelled`
- `selected_products` must belong to vendor

### Get Event Detail
```
GET /api/vendor/events/{id}/
```

### Update Event
```
PUT /api/vendor/events/{id}/
PATCH /api/vendor/events/{id}/
```

### Delete Event (Soft Delete)
```
DELETE /api/vendor/events/{id}/
```
Soft deletes the event (sets `is_deleted=True`).

### Duplicate Event
```
POST /api/vendor/events/{id}/duplicate/
```
Creates a copy of the event with status set to `draft`.

---

## 2. Festival Templates API

### List Festival Templates
```
GET /api/vendor/events/festivals/
```

**Response:**
```json
[
  {
    "id": "diwali",
    "name": "Diwali Festival",
    "preset_message": "🎉 Celebrate Diwali...",
    "preset_colors": {
      "primary": "#F97316",
      "secondary": "#FFA500",
      "accent": "#FFD700"
    },
    "preset_date_range": {
      "start": "2024-11-01",
      "end": "2024-11-15"
    },
    "background": "/static/festivals/diwali.png",
    "hashtags": ["#DiwaliSale", "#FestivalOffers"],
    "recommended_products": 4
  }
]
```

**Available Templates:**
- `diwali`, `holi`, `dussehra`, `christmas`, `new_year`, `eid`, `independence_day`, `republic_day`, `valentines`, `summer_sale`

---

## 3. Poster Generation API

### Generate Poster
```
POST /api/vendor/events/{id}/poster/generate/
```

**Request Body:**
```json
{
  "template_id": "diwali",
  "selected_products": [22, 18, 21],
  "custom_message": "Flat 40% off!"
}
```

**Response:**
```json
{
  "poster_url": "https://res.cloudinary.com/.../event_1_poster.png"
}
```

**Process:**
1. Loads festival template
2. Fetches vendor info and product images
3. Generates poster with Pillow
4. Uploads to Cloudinary
5. Returns poster URL

---

## 4. Product Recommendations API

### Get Recommended Products
```
GET /api/vendor/events/recommend-products/?limit=10
```

**Query Parameters:**
- `limit` (optional, default: 10): Number of products to return

**Response:**
```json
[
  {
    "id": 1,
    "name": "Product Name",
    "price": "100.00",
    "image": "https://...",
    "is_in_stock": true,
    "stock_quantity": 10,
    "is_featured": true
  }
]
```

**Priority Logic:**
1. Featured products
2. Most viewed (placeholder)
3. Highest stock
4. Random active products

---

## 5. WhatsApp Campaign Logging API

### Log Campaign
```
POST /api/vendor/events/{id}/campaign/send/
```

**Note:** This does NOT send WhatsApp messages. Frontend should open:
```
https://wa.me/{phone}?text={encoded_msg}
```

**Request Body:**
```json
{
  "message_text": "Check out our Diwali sale!",
  "poster_url": "https://...",
  "sent_to_phone": "+1234567890",
  "status": "sent"
}
```

**Response:**
```json
{
  "id": 1,
  "event": 1,
  "event_title": "Diwali Sale",
  "message_text": "Check out our Diwali sale!",
  "poster_url": "https://...",
  "sent_to_phone": "+1234567890",
  "status": "sent",
  "click_count": 0,
  "created_at": "2024-11-01T10:00:00Z"
}
```

---

## 6. Event Analytics API

### Get Analytics
```
GET /api/vendor/events/{id}/analytics/?days=30
```

**Query Parameters:**
- `days` (optional, default: 30): Number of days to look back

**Response:**
```json
{
  "total_views": 150,
  "total_clicks": 45,
  "total_shares": 12,
  "total_leads": 8,
  "daily_breakdown": [
    {
      "date": "2024-11-01",
      "views": 50,
      "clicks": 15,
      "shares": 4,
      "leads": 2
    }
  ]
}
```

### Update Analytics
```
POST /api/vendor/events/{id}/analytics/update/
```

**Request Body:**
```json
{
  "date": "2024-11-01",
  "views": 5,
  "clicks": 3,
  "shares": 1,
  "leads": 0
}
```

**Use Cases:**
- User clicked WhatsApp link
- User downloaded poster
- User viewed event page
- User shared event

---

## 7. Event Publish Workflow

### Publish Event
```
POST /api/vendor/events/{id}/publish/
```

**Process:**
1. Validates event is complete (has title)
2. Sets `status = 'active'`
3. Updates `start_date = now()` if not already started
4. Creates analytics entry for today
5. Returns success response

**Response:**
```json
{
  "message": "Event published successfully.",
  "event": {
    "id": 1,
    "title": "Diwali Sale",
    "status": "active",
    ...
  }
}
```

---

## Permissions

### IsVendor
- Requires: `request.user.role == 'vendor'`
- Applied to all endpoints

### IsVendorOwner
- Ensures vendor can only access their own events
- Automatically enforced by ViewSet queryset filtering

---

## Error Responses

### 400 Bad Request
```json
{
  "error": "End date must be after start date."
}
```

### 401 Unauthorized
```json
{
  "detail": "Authentication credentials were not provided."
}
```

### 403 Forbidden
```json
{
  "detail": "You do not have permission to perform this action."
}
```

### 404 Not Found
```json
{
  "detail": "Not found."
}
```

---

## Models

### Event
- `vendor` (FK to Vendor)
- `title`, `description`
- `start_date`, `end_date`
- `status` (draft, scheduled, active, completed, cancelled)
- `festival_template_id`
- `poster_url`
- `custom_message`
- `selected_products` (JSON array of product IDs)
- `is_deleted`, `deleted_at` (soft delete)

### CampaignLog
- `event` (FK to Event)
- `message_text`
- `poster_url`
- `sent_to_phone`
- `status` (sent, failed)
- `click_count`
- `created_at`

### EventAnalytics
- `event` (FK to Event)
- `date`
- `views`, `clicks`, `shares`, `leads`
- `created_at`, `updated_at`

---

## OpenAPI Schema

DRF automatically generates OpenAPI schema. Access via:
- `/api/vendor/` (browsable API)
- Or use `drf-spectacular` for Swagger/OpenAPI 3.0

---

## Testing

Run tests:
```bash
python manage.py test apps.events
```

Test coverage includes:
- Event CRUD operations
- Festival templates
- Product recommendations
- Campaign logging
- Analytics
- Permissions
- Vendor isolation

