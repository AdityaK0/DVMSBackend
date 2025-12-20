from django.db import models
# Create your models here.
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.db.models import Q, UniqueConstraint
from django.db.models.functions import Lower
from ..vendors.models import Vendor

class UserManager(BaseUserManager):

    def create_user(self, username, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)

        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", "admin")   # 👈 IMPORTANT FIX

        return self.create_user(username, email, password, **extra_fields)

class User(AbstractUser):
    ROLE_CHOICES = [
        ('customer', 'Customer'),
        ('vendor', 'Vendor'),
        ('admin', 'Admin'),
    ]
    name = models.CharField(max_length=300, blank=True, null=True)
    email = models.EmailField(unique=True)  # enforce unique at DB level
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='vendor')
    phone_number = models.CharField(max_length=20, blank=True, null=True, db_index=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    
    objects = UserManager()

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            # Case-insensitive unique email (PostgreSQL)
            UniqueConstraint(Lower("email"), name="unique_user_email_ci"),
            # Avoid duplicate active usernames (case-insensitive)
            UniqueConstraint(
                Lower("username"),
                name="unique_active_username_ci",
                condition=Q(is_active=True),
            ),
        ]
        
    # indexes = [
    #     models.Index(fields=["role", "is_active"]),
    #     models.Index(Lower("email")),
    # ]

    def __str__(self):
        return f"{self.username} ({self.role})"

    @property
    def full_name(self):
        return self.name or f"{self.first_name} {self.last_name}".strip()

class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    street_address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100)
    is_default = models.BooleanField(default=False)
    zip_code = models.CharField(max_length=100,null=True)
    address_type = models.CharField(max_length=20, choices=[
        ('shipping', 'Shipping'),
        ('billing', 'Billing'),
        ('both', 'Both')
    ], default='both')
    longitude = models.CharField(max_length=20,null=True)
    latitude = models.CharField(max_length=20,null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=Q(is_default=True),
                name="unique_default_address_per_user",
            ),
        ]

    def __str__(self):
        return f"{self.street_address}, {self.city}"
