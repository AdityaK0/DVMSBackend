from django.core.management.base import BaseCommand
from django.db import transaction

from apps.vendors.models import Vendor, VendorStats
from apps.products.models import Product
from apps.dashboard.models import Customer


class Command(BaseCommand):
    help = "Backfill VendorStats for existing vendors"

    def handle(self, *args, **options):
        self.stdout.write("🔄 Backfilling VendorStats...")

        vendors = Vendor.objects.all()

        for vendor in vendors:
            with transaction.atomic():

                stats, created = VendorStats.objects.select_for_update().get_or_create(
                    vendor=vendor,
                    defaults={
                        "total_products": 0,
                        "active_products": 0,
                        "inactive_products": 0,
                        "total_customers": 0,
                        "active_customers": 0,
                        "inactive_customers": 0,
                    }
                )

                # Recalculate only if created
                if created:
                    total_products = Product.objects.filter(
                        vendor=vendor,
                        is_archived=False
                    ).count()

                    active_products = Product.objects.filter(
                        vendor=vendor,
                        is_active=True,
                        is_archived=False
                    ).count()

                    inactive_products = total_products - active_products

                    total_customers = Customer.objects.filter(
                        vendor=vendor
                    ).count()

                    active_customers = Customer.objects.filter(
                        vendor=vendor,
                        is_active=True
                    ).count()

                    inactive_customers = total_customers - active_customers

                    stats.total_products = total_products
                    stats.active_products = active_products
                    stats.inactive_products = inactive_products
                    stats.total_customers = total_customers
                    stats.active_customers = active_customers
                    stats.inactive_customers = inactive_customers

                    stats.save()

                    self.stdout.write(
                        f"✅ Stats created for vendor {vendor.id}"
                    )
                else:
                    self.stdout.write(
                        f"⏭️  VendorStats already exists for vendor {vendor.id}"
                    )

        self.stdout.write("🎉 Backfill complete")
