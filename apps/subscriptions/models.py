from django.db import models
from django.utils import timezone
from django.conf import settings
from apps.vendors.models import Vendor

class Subscription(models.Model):
    vendor = models.OneToOneField(Vendor, on_delete=models.CASCADE, related_name='subscription')
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=False)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=1.00)  # ₹1 default
    order_id = models.CharField(max_length=255, blank=True, null=True)
    payment_id = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # If end_date not specified, set to 30 days from start_date
        if not self.end_date and self.start_date:
            self.end_date = self.start_date + timezone.timedelta(days=30)
        # update is_active according to end_date
        self.is_active = self.end_date and (self.end_date > timezone.now())
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.vendor.business_name} subscription ({'active' if self.is_active else 'inactive'})"
