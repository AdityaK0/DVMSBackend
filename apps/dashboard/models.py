from django.db import models
from apps.vendors.models import Vendor
from django.conf import settings 



class Customer(models.Model):
    """Basic customer tracking for vendors"""
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='customers')
    name = models.CharField(max_length=200)
    email = models.EmailField(null=True, blank=True) 
    phone = models.CharField(max_length=20, blank=True, db_index=True)  # ✅ Add index for phone lookup
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    bought = models.IntegerField(default=0)
    last_interaction = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('vendor', 'phone')
        indexes = [
            models.Index(fields=['vendor', 'is_active']),  # ✅ Common filter: active customers per vendor
            models.Index(fields=['vendor', '-created_at']), # ✅ OPTIMIZATION: Critical for default customer list sort
        ]

    def __str__(self):
        return f"{self.name} - {self.vendor.business_name}"



class Invoice(models.Model):
    vendor = models.ForeignKey(
        "vendors.Vendor",
        on_delete=models.CASCADE,
        related_name="invoices"
    )
    customer_name = models.CharField(max_length=150, blank=True, null=True)
    customer_phone = models.CharField(max_length=20)

    items = models.JSONField(default=list)  # Stores item array from frontend

    # ✅ CRITICAL FIX: Use DecimalField for money to avoid float precision errors
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    pending_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    is_udhaari = models.BooleanField(default=False)  # ✅ Add index for filtering
    invoice_date = models.DateField()
    is_edited = models.BooleanField(default=False)

    is_locked = models.BooleanField(default=False)  # NEW: prevents item edits

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Invoice #{self.id} - {self.customer_phone}"

    class Meta:
        indexes = [
            models.Index(fields=["vendor", "invoice_date"]),
            models.Index(fields=["vendor", "is_udhaari"]),  # ✅ Filter by udhaari status
            models.Index(fields=["vendor", "pending_amount"]),  # ✅ Pending invoices query
            models.Index(fields=["vendor", "customer_phone"]),  # ✅ Customer invoice lookup
            models.Index(fields=["vendor", "-created_at"]),  # ✅ Recent invoices (descending)
        ]


class InvoicePayment(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=12, decimal_places=2)  #CRITICAL FIX: Use DecimalField
    note = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)  #Add index for sorting

    class Meta:
        indexes = [
            models.Index(fields=['invoice', '-created_at']),  # ✅ Payment history per invoice
        ]

    def __str__(self):
        return f"Payment of {self.amount} for Invoice #{self.invoice_id}"



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
        db_index=False, # Removed single index, covered by composite
    )

    # structure: {"field": {"old": <value>, "new": <value>}, ...}
    changes = models.JSONField(default=dict, blank=True)

    ip_address = models.CharField(max_length=50, null=True, blank=True)
    device_info = models.CharField(max_length=255, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=['invoice', '-created_at']),  # ✅ Changelog history per invoice
            models.Index(fields=['vendor', 'change_type']),  # ✅ Filter by change type per vendor
            models.Index(fields=['vendor', '-created_at']),  # ✅ Recent changes per vendor
        ]

    def __str__(self):
        return f"Invoice #{self.invoice_id} changes at {self.created_at}"