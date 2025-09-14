from django.db import models
# Create your models here.
from django.contrib.auth.models import AbstractUser
from django.db import models
from ..vendors.models import Vendor

class User(AbstractUser):
    ROLE_CHOICES = [
        ('customer', 'Customer'),
        ('vendor', 'Vendor'),
        ('admin', 'Admin'),
    ]
    name = models.CharField(max_length=300, blank=True, null=True)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES,default='vendor')
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # groups = models.ManyToManyField(
    #     "auth.Group",
    #     related_name="customuser_groups",  # Change the related_name
    #     blank=True
    # )
    # user_permissions = models.ManyToManyField(
    #     "auth.Permission",
    #     related_name="customuser_permissions",  # Change the related_name
    #     blank=True
    # )

    def __str__(self):
        return f"{self.username} ({self.role})"

class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    street_address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100)
    is_default = models.BooleanField(default=False)
    address_type = models.CharField(max_length=20, choices=[
        ('shipping', 'Shipping'),
        ('billing', 'Billing'),
        ('both', 'Both')
    ], default='both')
    longitude = models.CharField(max_length=20,null=True)
    latitude = models.CharField(max_length=20,null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.street_address}, {self.city}"

class CustomerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer_profile')
    date_of_birth = models.DateField(blank=True, null=True)
    preferences = models.JSONField(default=dict, blank=True)
    loyalty_points = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Customer Profile: {self.user.username}"

class VendorProfile(models.Model):
    vendor = models.OneToOneField(Vendor, on_delete=models.CASCADE, related_name='profile')
    business_license = models.CharField(max_length=100, blank=True)
    tax_id = models.CharField(max_length=50, blank=True)
    is_verified = models.BooleanField(default=False)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    total_orders = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Vendor Profile: {self.vendor.business_name}"

# class VendorProfile(models.Model):
#     user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='vendor_profile')
#     business_name = models.CharField(max_length=200)
#     business_description = models.TextField(blank=True)
#     business_license = models.CharField(max_length=100, blank=True)
#     tax_id = models.CharField(max_length=50, blank=True)
#     is_verified = models.BooleanField(default=False)
#     rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
#     total_orders = models.IntegerField(default=0)
#     created_at = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return f"Vendor: {self.business_name}"