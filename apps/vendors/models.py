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
    business_email = models.EmailField(unique=True,null=True)
    business_type = models.CharField(max_length=25, choices=BUSSINES_TYPE, default='other')
    business_phone = models.CharField(max_length=20,unique=True,null=True)
    whatsapp_number = models.CharField(max_length=20, blank=True, null=True)
    gstin = models.CharField(max_length=20, blank=True)
    website = models.URLField(blank=True,null=True)
    telegram_chat_id = models.CharField(max_length=40, blank=True, null=True)
    logo = models.URLField(blank=True,null=True)
    is_onboarded = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    secret = models.CharField(
    max_length=10,
    blank=True,
    null=True,
    default=generate_secret
    )
    secret_expires_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.business_name
    

    @property
    def total_products(self):
        return self.products.filter(is_active=True).count()

    @property
    def average_rating(self):
        # This would be calculated from product reviews
        return 0.0