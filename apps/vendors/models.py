from email.policy import default
from django.db import models
from django.conf import settings
from cloudinary.models import CloudinaryField

import uuid

def generate_secret():
    return uuid.uuid4().hex[:8]

class Vendor(models.Model):
    BUSSINES_TYPE = [
        ('clothing', 'Clothing'),
        ('electronics', 'Electronics'),
        ('furniture', 'Furniture'),
        ('other', 'Other'),
    ]
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,related_name="vendor")
    business_name = models.CharField(max_length=200)
    business_name_slug = models.SlugField(max_length=200, blank=True, null=True)
    business_description = models.TextField(blank=True)
    business_email = models.EmailField(unique=True, null=True, db_index=True)
    business_type = models.CharField(max_length=25, choices=BUSSINES_TYPE, default='other')
    business_phone = models.CharField(max_length=20, unique=True, null=True, db_index=True)
    whatsapp_number = models.CharField(max_length=20, blank=True, null=True)
    gstin = models.CharField(max_length=20, blank=True)
    website = models.URLField(blank=True,null=True)
    telegram_chat_id = models.CharField(max_length=40, blank=True, null=True)
    logo = models.URLField(blank=True, null=True)
    is_onboarded = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    secret = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        default=generate_secret,
        db_index=True,
    )
    secret_expires_at = models.DateTimeField(null=True, blank=True)
    geolocation = models.JSONField(null=True, blank=True)

    def __str__(self):
        return self.business_name
    

    @property
    def total_products(self):
        return self.products.filter(is_active=True).count()

    @property
    def average_rating(self):
        # This would be calculated from product reviews
        return 0.0
    
    
    
from django.db import models
from django.utils import timezone

class Event(models.Model):
    """
    System-wide events created by admin.
    Example: Diwali, Holi, Christmas, Winter Sale, Independence Day, etc.
    Vendors ONLY use these templates.
    """

    STATUS_CHOICES = [
        ('upcoming', 'Upcoming'),
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('inactive', 'Inactive'),  # Admin manually disables
    ]

    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)

    # Optional default festival-specific style
    default_message = models.TextField(blank=True)
    default_colors = models.JSONField(default=dict, blank=True)

    # Timeline
    start_date = models.DateField()
    end_date = models.DateField()

    # Admin control or automated status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='upcoming')

    is_active = models.BooleanField(default=True)  # for admin to turn off entirely

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name

    def auto_update_status(self):
        """Automatically updates event status based on date timeline."""
        today = timezone.now().date()

        if not self.is_active:
            self.status = 'inactive'

        elif today < self.start_date:
            self.status = 'upcoming'

        elif self.start_date <= today <= self.end_date:
            self.status = 'active'

        elif today > self.end_date:
            self.status = 'expired'

        self.save(update_fields=['status'])


class PosterTemplate(models.Model):
    """
    Poster designs for an event (festival).
    Admin uploads multiple posters per event.
    """
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='posters')

    name = models.CharField(max_length=200)
    thumbnail = models.URLField(max_length=500)

    # Contains:
    # - HTML template
    # - dynamic fields
    # - fonts/colors
    design_schema = models.JSONField(default=dict,null=True)
    html_template = models.TextField() 

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.name} - {self.event.name}"

