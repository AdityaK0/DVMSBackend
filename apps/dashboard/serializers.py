from rest_framework import serializers
from .models import  CustomerMessage, Customer, ActivityLog

class DashboardStatsSerializer(serializers.Serializer):
    """Serializer for dashboard statistics"""
    total_products = serializers.IntegerField()
    products_change_percentage = serializers.FloatField()
    active_customers = serializers.IntegerField()
    customers_change_percentage = serializers.FloatField()
    events_this_month = serializers.IntegerField()
    events_change = serializers.IntegerField()
    messages_sent = serializers.IntegerField()
    messages_change_percentage = serializers.FloatField()


class ActivityLogSerializer(serializers.ModelSerializer):
    """Serializer for activity logs"""
    icon = serializers.SerializerMethodField()
    time_ago = serializers.SerializerMethodField()
    
    class Meta:
        model = ActivityLog
        fields = ['id', 'activity_type', 'description', 'icon', 'time_ago', 'created_at']
    
    def get_icon(self, obj):
        """Return icon emoji based on activity type"""
        icon_map = {
            'product_added': '📦',
            'product_updated': '📦',
            'customer_registered': '👤',
            'event_created': '🎪',
            'message_sent': '💬',
            'report_generated': '📊',
        }
        return icon_map.get(obj.activity_type, '📋')
    
    def get_time_ago(self, obj):
        """Calculate human-readable time ago"""
        from django.utils import timezone
        from datetime import timedelta
        
        now = timezone.now()
        diff = now - obj.created_at
        
        if diff < timedelta(hours=1):
            minutes = int(diff.total_seconds() / 60)
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        elif diff < timedelta(days=1):
            hours = int(diff.total_seconds() / 3600)
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif diff < timedelta(days=7):
            days = diff.days
            return f"{days} day{'s' if days != 1 else ''} ago"
        else:
            return obj.created_at.strftime("%b %d, %Y")


# class EventSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Event
#         fields = ['id', 'name', 'description', 'event_type', 'start_date', 
#                   'end_date', 'status', 'created_at']
#         read_only_fields = ['created_at']


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ['id', 'name', 'email', 'phone', 'is_active', 'created_at']
        read_only_fields = ['registered_at']


class CustomerMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerMessage
        fields = ['id', 'subject', 'message', 'message_type', 
                  'recipient_count', 'sent_at']
        read_only_fields = ['sent_at']
        
        
 
# dashboard/serializers.py

from rest_framework import serializers
from .models import Invoice, InvoiceChangeLog

class InvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = [
            "id",
            "customer_name",
            "customer_phone",
            "items",
            "total_amount",
            "paid_amount",
            "pending_amount",
            "is_udhaari",
            "invoice_date",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def validate(self, data):
        """
        Enforce consistency:
        1. Recalculate total_amount from items.
        2. Validate price/qty.
        3. Compute pending_amount based on total, paid, and is_udhaari.
        """
        # Handle partial updates: fallback to instance data if field missing
        items = data.get("items")
        if items is None and self.instance:
            items = self.instance.items
        
        # If items is still None (e.g. create without items), default to empty list
        items = items or []

        if not items:
             # For create, we require items. For update, if we ended up with no items, that's an issue.
             raise serializers.ValidationError({"items": "At least one item is required."})

        calculated_total = 0.0
        validated_items = []

        for item in items:
            # item might be a dict or OrderedDict
            name = item.get("name", "").strip()
            try:
                price = float(item.get("price", 0))
                qty = float(item.get("qty", 1))
            except (ValueError, TypeError):
                raise serializers.ValidationError({"items": "Price and Quantity must be valid numbers."})

            if not name:
                raise serializers.ValidationError({"items": "Item name is required."})
            if price < 0:
                raise serializers.ValidationError({"items": f"Price for '{name}' cannot be negative."})
            if qty < 1:
                raise serializers.ValidationError({"items": f"Quantity for '{name}' must be at least 1."})

            total = price * qty
            calculated_total += total
            
            validated_items.append({
                "name": name,
                "price": price,
                "qty": qty,
                "total": total
            })

        # Always override items and total_amount
        data["items"] = validated_items
        data["total_amount"] = calculated_total

        # Paid Amount
        paid_amount = data.get("paid_amount")
        if paid_amount is None and self.instance:
            paid_amount = self.instance.paid_amount
        paid_amount = float(paid_amount or 0)

        if paid_amount < 0:
            raise serializers.ValidationError({"paid_amount": "Paid amount cannot be negative."})
        data["paid_amount"] = paid_amount

        # Udhaari Status
        is_udhaari = data.get("is_udhaari")
        if is_udhaari is None and self.instance:
            is_udhaari = self.instance.is_udhaari
        # Default to False if not found anywhere (e.g. create)
        if is_udhaari is None:
            is_udhaari = False

        # Compute Pending Amount
        if not is_udhaari:
            data["pending_amount"] = 0.0
        else:
            pending = calculated_total - paid_amount
            data["pending_amount"] = max(pending, 0.0)

        return data


class InvoiceChangeLogSerializer(serializers.ModelSerializer):
    changed_by = serializers.SerializerMethodField()

    class Meta:
        model = InvoiceChangeLog
        fields = ["id", "change_type", "changes", "created_at", "changed_by"]

    def get_changed_by(self, obj):
        if obj.changed_by:
            return obj.changed_by.get_full_name() or obj.changed_by.username
        return None

