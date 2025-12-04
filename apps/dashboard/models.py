from django.db import models
from apps.vendors.models import Vendor
from django.conf import settings 


class Customer(models.Model):
    """Basic customer tracking for vendors"""
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='customers')
    name = models.CharField(max_length=200)
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    bought = models.IntegerField(default=0)
    last_interaction = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('vendor', 'phone')

    def __str__(self):
        return f"{self.name} - {self.vendor.business_name}"



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
        ("create", "Invoice Created"),
        ("update", "Invoice Updated"),
        ("payment", "Payment Added"),
        ("delete", "Invoice Deleted"),
        ("status", "Status Change"),
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
    changes = models.JSONField(default=dict, blank=True)

    ip_address = models.CharField(max_length=50, null=True, blank=True)
    device_info = models.CharField(max_length=255, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Invoice #{self.invoice_id} changes at {self.created_at}"