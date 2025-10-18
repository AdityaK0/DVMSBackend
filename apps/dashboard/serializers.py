from rest_framework import serializers
from .models import Event, CustomerMessage, Customer, ActivityLog

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


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = ['id', 'name', 'description', 'event_type', 'start_date', 
                  'end_date', 'status', 'created_at']
        read_only_fields = ['created_at']


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