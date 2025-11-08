from django.db import models
from django.utils import timezone
from django.conf import settings
from apps.vendors.models import Vendor
from decimal import Decimal

class SubscriptionPlan(models.Model):
    """
    Subscription plans available for vendors.
    """
    PLAN_TYPES = [
        ('free', 'Free'),
        ('basic', 'Basic'),
        ('premium', 'Premium'),
        ('enterprise', 'Enterprise'),
    ]
    
    name = models.CharField(max_length=100)
    plan_type = models.CharField(max_length=20, choices=PLAN_TYPES, default='basic')
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Price in INR")
    price_in_paise = models.IntegerField(help_text="Price in paise for Razorpay")
    duration_days = models.IntegerField(default=30)
    sync_limit = models.IntegerField(default=10, help_text="Number of syncs allowed per month")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        # Auto-calculate paise from rupees
        if self.price:
            self.price_in_paise = int(self.price * 100)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.name} - ₹{self.price}"


class PaymentTransaction(models.Model):
    """
    Track all payment transactions with Razorpay.
    This ensures we have a proof-based payment system.
    """
    STATUS_CHOICES = [
        ('created', 'Order Created'),
        ('authorized', 'Payment Authorized'),
        ('captured', 'Payment Captured'),
        ('failed', 'Payment Failed'),
        ('cancelled', 'Payment Cancelled'),
    ]
    
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='payment_transactions')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Razorpay IDs
    razorpay_order_id = models.CharField(max_length=255, unique=True)
    razorpay_payment_id = models.CharField(max_length=255, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=255, blank=True, null=True)
    
    # Transaction details
    amount = models.IntegerField(help_text="Amount in paise")
    currency = models.CharField(max_length=3, default='INR')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='created')
    
    # Metadata
    error_message = models.TextField(blank=True, null=True)
    razorpay_response = models.JSONField(default=dict, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['vendor', 'status']),
            models.Index(fields=['razorpay_order_id']),
        ]
    
    def __str__(self):
        return f"Transaction {self.razorpay_order_id} - {self.status}"
    
    def mark_as_captured(self, payment_id, signature):
        """Mark transaction as successfully captured."""
        self.razorpay_payment_id = payment_id
        self.razorpay_signature = signature
        self.status = 'captured'
        self.verified_at = timezone.now()
        self.save(update_fields=['razorpay_payment_id', 'razorpay_signature', 'status', 'verified_at', 'updated_at'])
    
    def mark_as_failed(self, error_msg):
        """Mark transaction as failed."""
        self.status = 'failed'
        self.error_message = error_msg
        self.save(update_fields=['status', 'error_message', 'updated_at'])


class Subscription(models.Model):
    """
    Active subscription for a vendor.
    Only created after successful payment verification.
    """
    vendor = models.OneToOneField(Vendor, on_delete=models.CASCADE, related_name='subscription')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.SET_NULL, null=True, blank=True)
    transaction = models.ForeignKey(PaymentTransaction, on_delete=models.SET_NULL, null=True, blank=True)
    
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=False)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=1.00)  # ₹1 default
    after_webhook_called = models.BooleanField(default=False)
    
    # Legacy fields (kept for backward compatibility)
    order_id = models.CharField(max_length=255, blank=True, null=True)
    payment_id = models.CharField(max_length=255, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    
    def save(self, *args, **kwargs):
            # Auto-set end_date if missing
        if not self.end_date and self.start_date:
            duration = self.plan.duration_days if self.plan else 30
            self.end_date = self.start_date + timezone.timedelta(days=duration)
        
        # Respect manually set is_active, otherwise infer
        if 'is_active' not in kwargs and self.is_active is None:
            self.is_active = self.end_date and (self.end_date > timezone.now())

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.vendor.business_name} subscription ({'active' if self.is_active else 'inactive'})"
    
    @property
    def days_remaining(self):
        """Calculate days remaining in subscription."""
        if not self.end_date or not self.is_active:
            return 0
        delta = self.end_date - timezone.now()
        return max(0, delta.days)
