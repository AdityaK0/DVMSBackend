from django.db import models
from django.conf import settings
from cloudinary.models import CloudinaryField
from django.utils.text import slugify



class Vendor(models.Model):
    BUSSINES_TYPE = [
        ('clothing', 'Clothing'),
        ('electronics', 'Electronics'),
        ('furniture', 'Furniture'),
        ('other', 'Other'),
    ]
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,related_name="vendor")
    business_name = models.CharField(max_length=200)
    business_name_slug = models.SlugField(max_length=200, unique=True, blank=True) 
    business_description = models.TextField(blank=True)
    business_email = models.EmailField(unique=True,null=True)
    business_type = models.CharField(max_length=25, choices=BUSSINES_TYPE, default='other')
    business_phone = models.CharField(max_length=20)
    gstin = models.CharField(max_length=20, blank=True)
    website = models.URLField(blank=True,null=True)
    # logo = models.ImageField(upload_to='vendor_logos/', blank=True)
    logo = CloudinaryField('image', folder='vendors', blank=True, null=True)
    is_onboarded = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.business_name
    
    def save(self, *args, **kwargs):
        # Create slug only once after instance has an ID
        if not self.pk:  # new instance, no ID yet
            super().save(*args, **kwargs)
            self.business_name_slug = f"{slugify(self.business_name)}-{self.id}"
            return super().save(update_fields=["business_name_slug"])

        # For existing instances — only regenerate if business_name changed
        # Use model's internal _state tracking: compare dirty fields
        if "business_name" in self.get_dirty_fields():
            self.business_name_slug = f"{slugify(self.business_name)}-{self.id}"

        super().save(*args, **kwargs)

    def get_dirty_fields(self):
        """Return a dict of fields that have changed."""
        if not self.pk:
            return {}
        old = type(self).objects.get(pk=self.pk)
        dirty = {}
        for field in self._meta.fields:
            name = field.attname
            if getattr(old, name) != getattr(self, name):
                dirty[name] = getattr(self, name)
        return dirty
    
        
    @property
    def total_products(self):
        return self.products.filter(is_active=True).count()

    @property
    def average_rating(self):
        # This would be calculated from product reviews
        return 0.0