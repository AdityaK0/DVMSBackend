# marketplace/apps/subscriptions/serializers.py
from rest_framework import serializers
from .models import Subscription

class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = ['id', 'vendor', 'start_date', 'end_date', 'is_active', 'amount', 'order_id', 'payment_id', 'created_at']
        read_only_fields = ['id', 'start_date', 'end_date', 'is_active', 'created_at']
