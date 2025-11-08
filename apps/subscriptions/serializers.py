# marketplace/apps/subscriptions/serializers.py
from rest_framework import serializers
from .models import Subscription, SubscriptionPlan, PaymentTransaction


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    """Serializer for subscription plans."""
    
    class Meta:
        model = SubscriptionPlan
        fields = [
            'id', 'name', 'plan_type', 'description', 'price', 
            'price_in_paise', 'duration_days', 'sync_limit', 
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class PaymentTransactionSerializer(serializers.ModelSerializer):
    """Serializer for payment transactions."""
    plan_name = serializers.CharField(source='plan.name', read_only=True)
    vendor_name = serializers.CharField(source='vendor.business_name', read_only=True)
    amount_in_rupees = serializers.SerializerMethodField()
    
    class Meta:
        model = PaymentTransaction
        fields = [
            'id', 'vendor', 'vendor_name', 'plan', 'plan_name',
            'razorpay_order_id', 'razorpay_payment_id', 'razorpay_signature',
            'amount', 'amount_in_rupees', 'currency', 'status', 
            'error_message', 'created_at', 'updated_at', 'verified_at'
        ]
        read_only_fields = [
            'id', 'vendor', 'razorpay_order_id', 'created_at', 
            'updated_at', 'verified_at'
        ]
    
    def get_amount_in_rupees(self, obj):
        """Convert paise to rupees for display."""
        return float(obj.amount) / 100


class SubscriptionSerializer(serializers.ModelSerializer):
    """Serializer for vendor subscriptions."""
    plan_name = serializers.CharField(source='plan.name', read_only=True)
    vendor_name = serializers.CharField(source='vendor.business_name', read_only=True)
    days_remaining = serializers.ReadOnlyField()
    
    class Meta:
        model = Subscription
        fields = [
            'id', 'vendor', 'vendor_name', 'plan', 'plan_name',
            'start_date', 'end_date', 'is_active', 'amount', 
            'order_id', 'payment_id', 'days_remaining',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'start_date', 'end_date', 'is_active', 
            'created_at', 'updated_at', 'days_remaining'
        ]
