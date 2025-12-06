"""
Management command to update all portfolio URLs to use vendor handles.
Run this once after deploying the handle system.

Usage:
    python manage.py update_portfolio_urls
"""

from django.core.management.base import BaseCommand
from apps.vendors.models import Vendor
from apps.portfolio.models import Portfolio
from apps.utils.update_things import update_portfolio_url


class Command(BaseCommand):
    help = 'Update all portfolio URLs to use vendor handles instead of slugs'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting portfolio URL update...'))
        
        portfolios = Portfolio.objects.select_related('vendor').all()
        updated_count = 0
        skipped_count = 0
        
        for portfolio in portfolios:
            vendor = portfolio.vendor
            
            if not vendor.handle:
                self.stdout.write(
                    self.style.WARNING(
                        f'Skipping vendor {vendor.id} ({vendor.business_name}) - no handle'
                    )
                )
                skipped_count += 1
                continue
            
            old_url = portfolio.portfolio_url
            update_portfolio_url(portfolio, vendor_handle=vendor.handle)
            new_url = portfolio.portfolio_url
            
            if old_url != new_url:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✓ Updated vendor {vendor.id} ({vendor.business_name})\n'
                        f'  Old: {old_url}\n'
                        f'  New: {new_url}'
                    )
                )
                updated_count += 1
            else:
                self.stdout.write(
                    f'  Vendor {vendor.id} ({vendor.business_name}) - URL already correct'
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n✅ Portfolio URL update complete!\n'
                f'   Updated: {updated_count}\n'
                f'   Skipped: {skipped_count}\n'
                f'   Total: {portfolios.count()}'
            )
        )
