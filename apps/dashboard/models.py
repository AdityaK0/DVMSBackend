from django.db import models
from apps.vendors.models import Vendor

class Event(models.Model):
    """Store vendor events/campaigns"""
    EVENT_STATUS = [
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='events')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    event_type = models.CharField(max_length=50, blank=True)  # festival, sale, campaign
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    status = models.CharField(max_length=20, choices=EVENT_STATUS, default='draft')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.vendor.business_name}"


class CustomerMessage(models.Model):
    """Track messages sent to customers"""
    MESSAGE_TYPE = [
        ('campaign', 'Campaign'),
        ('notification', 'Notification'),
        ('promotion', 'Promotion'),
    ]
    
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='messages')
    subject = models.CharField(max_length=200)
    message = models.TextField()
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPE, default='notification')
    recipient_count = models.IntegerField(default=0)
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-sent_at']

    def __str__(self):
        return f"{self.subject} - {self.vendor.business_name}"


class Customer(models.Model):
    """Basic customer tracking for vendors"""
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='customers')
    name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_interaction = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('vendor', 'email')

    def __str__(self):
        return f"{self.name} - {self.vendor.business_name}"


class ActivityLog(models.Model):
    """Track vendor activities for Recent Activity feed"""
    ACTIVITY_TYPES = [
        ('product_added', 'Product Added'),
        ('product_updated', 'Product Updated'),
        ('customer_registered', 'Customer Registered'),
        ('event_created', 'Event Created'),
        ('message_sent', 'Message Sent'),
        ('report_generated', 'Report Generated'),
    ]
    
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='activities')
    activity_type = models.CharField(max_length=30, choices=ACTIVITY_TYPES)
    description = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)  # Store additional info
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.activity_type} - {self.vendor.business_name}"