# apps/portfolio/models.py

from django.db import models
from django.utils.text import slugify
from django.urls import reverse
from cloudinary.models import CloudinaryField
from apps.vendors.models import Vendor
from apps.products.models import Product
from django.utils.timezone import now


class Portfolio(models.Model):
    """Main portfolio model - one per vendor"""
    vendor = models.OneToOneField(
        Vendor, 
        on_delete=models.CASCADE, 
        related_name='portfolio'
    )
    
    # Basic Info
    display_name = models.CharField(max_length=200, help_text="Display name for portfolio")
    tagline = models.CharField(max_length=300, blank=True, help_text="Short tagline/slogan",default="Your Vision Our Product")
    slug = models.SlugField(unique=True, max_length=100)
    business_name_slug = models.SlugField(max_length=200, blank=True, null=True)
    
    
    
    # Content
    about_us = models.TextField(blank=True)
    our_story = models.TextField(blank=True)
    mission = models.TextField(blank=True,default="To provide exceptional products and services that exceed our customers' expectations.")
    vision = models.TextField(blank=True,default="To become the leading provider in our industry, known for innovation and customer satisfaction.")
    
    # Media
    logo = models.URLField(max_length=500, blank=True, null=True)
    banner_image = models.URLField(max_length=500, blank=True, null=True)
    gallery_images = models.JSONField(default=list, blank=True)  # Array of cloudinary URLs
    title = models.CharField(max_length=255, default='My Portfolio')
    featured_products = models.ManyToManyField(Product, blank=True, related_name='featured_in_portfolios')
    carousel_images = models.JSONField(default=list, blank=True) 
    # Design Customization
    theme_color = models.CharField(max_length=7, default='#141414')  # Hex color
    accent_color = models.CharField(max_length=7, default='#ffffff')
    background_color = models.CharField(max_length=7, default='#ffffff')
    text_color = models.CharField(max_length=7, default='#ffffff')
    font_family = models.CharField(
        max_length=50, 
        default='Inter',
        choices=[
            ('Inter', 'Inter'),
            ('Roboto', 'Roboto'),
            ('Open Sans', 'Open Sans'),
            ('Poppins', 'Poppins'),
            ('Montserrat', 'Montserrat'),
        ]
    )
    
    # Layout Options
    LAYOUT_CHOICES = [
        ('modern', 'Modern Grid'),
        ('classic', 'Classic List'),
        ('masonry', 'Masonry Layout'),
        ('minimal', 'Minimal Cards'),
    ]
    layout_style = models.CharField(max_length=20, choices=LAYOUT_CHOICES, default='modern')
    
    # Social Media
    portfolio_url = models.URLField(blank=True)
    facebook_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)
    twitter_url = models.URLField(blank=True)
    linkedin_url = models.URLField(blank=True)
    youtube_url = models.URLField(blank=True)
    website_url = models.URLField(blank=True)
    
    # Display Settings
    show_pricing = models.BooleanField(default=True)
    show_stock_status = models.BooleanField(default=True)
    show_contact_form = models.BooleanField(default=True)
    show_social_links = models.BooleanField(default=True)
    show_testimonials = models.BooleanField(default=True)
    show_gallery = models.BooleanField(default=True)
    
    # Portfolio Settings
    is_public = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False) 
    is_carousel = models.BooleanField(default=False)
    want_to_show_on_platform = models.BooleanField(default=False)# For platform featuring
    custom_domain = models.CharField(max_length=100, blank=True, unique=True, null=True)
    custom_css = models.TextField(blank=True, help_text="Custom CSS for advanced styling")
    
    # SEO
    meta_title = models.CharField(max_length=60, blank=True)
    meta_description = models.CharField(max_length=160, blank=True)
    meta_keywords = models.CharField(max_length=200, blank=True)
    
    # Analytics
    view_count = models.PositiveIntegerField(default=0)
    last_viewed = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']
        verbose_name = 'Portfolio'
        verbose_name_plural = 'Portfolios'
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.display_name or self.vendor.business_name)
            self.slug = base_slug
            # Ensure unique slug
            counter = 1
            while Portfolio.objects.filter(slug=self.slug).exists():
                self.slug = f"{base_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        return reverse('portfolio:public_view', kwargs={'slug': self.slug})
    
    def get_featured_products(self):
        return self.vendor.products.filter(
            is_active=True, 
            is_featured=True,
            is_archived=False
        )[:8]
    
    def get_all_products(self):
        return self.vendor.products.filter(
            is_active=True,
            is_archived=False
        )
    
    def __str__(self):
        return f"{self.display_name or self.vendor.business_name} Portfolio"


class PortfolioCollection(models.Model):
    """Product collections within portfolio"""
    portfolio = models.ForeignKey(
        Portfolio, 
        on_delete=models.CASCADE, 
        related_name='collections'
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    cover_image = CloudinaryField("image", blank=True, null=True)
    products = models.ManyToManyField(Product, related_name='portfolio_collections')
    
    # Display settings
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    
    # SEO
    slug = models.SlugField(max_length=100)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'name']
        unique_together = ['portfolio', 'slug']
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.portfolio.display_name} - {self.name}"                       


class PortfolioTheme(models.Model):
    """Pre-built themes for portfolios"""
    name = models.CharField(max_length=100)
    description = models.TextField()
    preview_image = CloudinaryField('image', folder='portfolio/themes')
    
    # Theme configuration (JSON)
    theme_config = models.JSONField(default=dict)
    # Example: {
    #     "colors": {"primary": "#3B82F6", "secondary": "#10B981"},
    #     "layout": "modern",
    #     "fonts": {"heading": "Poppins", "body": "Inter"}
    # }
    
    is_active = models.BooleanField(default=True)
    is_premium = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['order', 'name']
    
    def __str__(self):
        return self.name
    
    
# apps/portfolio/models.py

# apps/portfolio/models.py

class PortfolioSyncPlan(models.Model):
    portfolio = models.OneToOneField(
        "Portfolio",
        on_delete=models.CASCADE,
        related_name="sync_plan",
    )

    allowed_syncs_per_day = models.PositiveIntegerField(default=5)
    used_syncs_today = models.PositiveIntegerField(default=0)
    extra_syncs_available = models.PositiveIntegerField(default=0)
    last_sync_at = models.DateTimeField(null=True, blank=True)


    def _is_new_day(self) -> bool:
        return not self.last_sync_at or self.last_sync_at.date() != now().date()

    def _reset_today_usage(self):
        if self._is_new_day():
            self.used_syncs_today = 0
            self.save(update_fields=["used_syncs_today"])

    def can_sync(self) -> bool:
        self._reset_today_usage()
        return (
            self.used_syncs_today < self.allowed_syncs_per_day 
            or self.extra_syncs_available > 0
        )

    def consume_sync(self):
        self._reset_today_usage()

        if self.used_syncs_today < self.allowed_syncs_per_day:
            self.used_syncs_today += 1
        else:
            self.extra_syncs_available -= 1

        self.last_sync_at = now()
        self.save(update_fields=["used_syncs_today", "extra_syncs_available", "last_sync_at"])

    @property
    def remaining_syncs(self):
        self._reset_today_usage()
        today_remaining = max(self.allowed_syncs_per_day - self.used_syncs_today, 0)
        return today_remaining + self.extra_syncs_available

    def __str__(self):
        return f"SyncPlan({self.portfolio.display_name})"


