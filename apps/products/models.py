from django.db import models
from django.contrib.auth import get_user_model
from apps.vendors.models import Vendor
from cloudinary.models import CloudinaryField

User = get_user_model()

class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, blank=True, null=True)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='categories', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('name', 'vendor')  # vendor-specific names
        indexes = [
            models.Index(fields=["vendor", "is_active"]),
            models.Index(fields=["parent"]),
        ]

    def __str__(self):
        return self.name



class Product(models.Model):
    CATEGORIES = [
        ("clothing","clothing"),("electronics","electonics"),
        ("sports","sports")
    ]
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='products')
    name = models.CharField(max_length=200)
    description = models.TextField()
    # category = models.CharField(choices=CATEGORIES,max_length=100)
    category = models.ForeignKey(
        'Category',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products'
    )
    image_urls = models.JSONField(default=list, blank=True)
    primary_image = models.URLField(max_length=500, blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    stock_quantity = models.PositiveIntegerField(default=0)
    min_stock_level = models.PositiveIntegerField(default=5)
    sku = models.CharField(max_length=100, db_index=True)
    # weight = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    sizes = models.JSONField(default=list, blank=True)
    gender = models.CharField(max_length=100, blank=True, null=True)
    
    dimensions = models.JSONField(default=dict, blank=True)  # {length, width, height}
    is_active = models.BooleanField(default=True, db_index=True)
    is_featured = models.BooleanField(default=False, db_index=True)
    is_archived = models.BooleanField(default=False, db_index=True)
    meta_title = models.CharField(max_length=200, blank=True)
    meta_description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('vendor', 'sku')
        indexes = [
            models.Index(fields=["vendor", "is_active", "is_archived"]),
            models.Index(fields=["vendor", "is_featured"]),
            models.Index(fields=["category", "is_active"]),
        ]
    

    def __str__(self):
        return self.name

    @property
    def is_in_stock(self):
        return self.stock_quantity > 0

    @property
    def is_low_stock(self):
        return self.stock_quantity <= self.min_stock_level
