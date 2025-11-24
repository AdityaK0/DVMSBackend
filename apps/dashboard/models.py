from django.db import models
from apps.vendors.models import Vendor
from django.conf import settings 


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
    



class Invoice(models.Model):
    vendor = models.ForeignKey(
        "vendors.Vendor",
        on_delete=models.CASCADE,
        related_name="invoices"
    )
    customer_name = models.CharField(max_length=150, blank=True, null=True)
    customer_phone = models.CharField(max_length=20, db_index=True)

    items = models.JSONField(default=list)  # Stores item array from frontend

    total_amount = models.FloatField()
    paid_amount = models.FloatField(default=0)
    pending_amount = models.FloatField(default=0)

    is_udhaari = models.BooleanField(default=False)
    invoice_date = models.DateField()
    is_edited = models.BooleanField(default=False)

    is_locked = models.BooleanField(default=False)  # NEW: prevents item edits

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Invoice #{self.id} - {self.customer_phone}"


class InvoicePayment(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="payments")
    amount = models.FloatField()
    note = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment of {self.amount} for Invoice #{self.invoice_id}"


# dashboard/models.py

class InvoiceChangeLog(models.Model):
    CHANGE_TYPE_CHOICES = [
        ("update", "Update"),
        ("manual_adjust", "Manual Adjust"),
        ("payment", "Payment"),
    ]

    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name="change_logs",
    )
    vendor = models.ForeignKey(
        Vendor,
        on_delete=models.CASCADE,
        related_name="invoice_change_logs",
    )
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invoice_changes",
    )

    change_type = models.CharField(
        max_length=50,
        choices=CHANGE_TYPE_CHOICES,
        default="update",
    )

    # structure: {"field": {"old": <value>, "new": <value>}, ...}
    changes = models.JSONField(default=dict)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Invoice #{self.invoice_id} changes at {self.created_at}"