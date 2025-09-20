from django.db import models
from django.contrib.auth import get_user_model
from apps.vendors.models import Vendor
from cloudinary.models import CloudinaryField

User = get_user_model()

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Categories'

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
    category = models.CharField(choices=CATEGORIES,max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    stock_quantity = models.IntegerField(default=0)
    min_stock_level = models.IntegerField(default=5)
    sku = models.CharField(max_length=100, unique=True)
    weight = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    dimensions = models.JSONField(default=dict, blank=True)  # {length, width, height}
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    meta_title = models.CharField(max_length=200, blank=True)
    meta_description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    @property
    def is_in_stock(self):
        return self.stock_quantity > 0

    @property
    def is_low_stock(self):
        return self.stock_quantity <= self.min_stock_level

class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    # image = CloudinaryField('image', folder='products')  # handled by Cloudinary
    image = CloudinaryField('image')
    image_url = models.URLField(max_length=500, blank=True) 
    image_b64 = models.TextField(null=True)
    alt_text = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image for {self.product.name}"