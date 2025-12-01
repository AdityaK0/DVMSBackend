# products/signals.py

"""
Product signals.

NOTE: Event publishing has been moved to the service layer.
This file is kept for other signal-based logic if needed in the future.

DO NOT publish events from signals - use service layer instead to avoid:
- Duplicate event publishing
- Transaction safety issues
- Debugging complexity
"""

from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from apps.products.models import Product

