from django.db import models
from django.conf import settings
from apps.vendors.models import Vendor


class Event(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='events')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Festival template reference
    festival_template_id = models.CharField(max_length=100, blank=True, null=True)
    
    # Poster and media
    poster_url = models.URLField(max_length=500, blank=True, null=True)
    custom_message = models.TextField(blank=True)
    
    # Selected products for the event
    selected_products = models.JSONField(default=list, blank=True)  # List of product IDs
    
    # Soft delete
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['vendor', 'status']),
            models.Index(fields=['start_date', 'end_date']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.vendor.business_name}"
    
    def soft_delete(self):
        """Soft delete the event"""
        from django.utils import timezone
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()

