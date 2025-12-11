"""
Management command to regenerate vendor handle for a SPECIFIC vendor.

⚠️ SAFETY: This command requires a vendor ID to prevent accidental bulk changes.

Usage:
    python manage.py regenerate_handles <vendor_id>
    python manage.py regenerate_handles <vendor_id> --dry-run
"""

from django.core.management.base import BaseCommand, CommandError
from apps.vendors.models import Vendor
from apps.vendors.utils import generate_unique_handle
from apps.portfolio.models import Portfolio
from apps.utils.update_things import update_portfolio_url


class Command(BaseCommand):
    help = 'Regenerate handle for a SPECIFIC vendor (safer than bulk operation)'

    def add_arguments(self, parser):
        parser.add_argument(
            'vendor_id',
            type=int,
            help='Vendor ID to regenerate handle for'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without actually changing it',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Skip confirmation prompt',
        )

    def handle(self, *args, **options):
        vendor_id = options['vendor_id']
        dry_run = options['dry_run']
        force = options['force']
        
        # Get vendor
        try:
            vendor = Vendor.objects.get(id=vendor_id)
        except Vendor.DoesNotExist:
            raise CommandError(f'Vendor with ID {vendor_id} does not exist')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        self.stdout.write(self.style.SUCCESS('\n⚠️  HANDLE REGENERATION'))
        self.stdout.write('─' * 60)
        self.stdout.write(f'Vendor ID: {vendor.id}')
        self.stdout.write(f'Business Name: {vendor.business_name}')
        self.stdout.write(f'Current Handle: {vendor.handle}')
        
        # Get portfolio
        try:
            portfolio = Portfolio.objects.get(vendor=vendor)
            self.stdout.write(f'Current Portfolio URL: {portfolio.portfolio_url}')
        except Portfolio.DoesNotExist:
            portfolio = None
            self.stdout.write('Portfolio: Not found')
        
        self.stdout.write('─' * 60)
        
        # Store old handle
        old_handle = vendor.handle
        
        # Temporarily clear handle to regenerate
        if not dry_run:
            vendor.handle = None
            vendor.save(update_fields=['handle'])
        
        # Generate new handle
        new_handle = generate_unique_handle(vendor.business_name, vendor_id=vendor.id)
        
        self.stdout.write(f'\nProposed New Handle: {new_handle}')
        
        if portfolio:
            if new_handle:
                new_url = f"https://{new_handle}.fordgeindia.online"
                self.stdout.write(f'Proposed New URL: {new_url}')
        
        self.stdout.write('─' * 60)
        
        # Confirmation
        if not force and not dry_run:
            confirm = input('\n⚠️  Regenerate handle for this vendor? (yes/no): ')
            if confirm.lower() != 'yes':
                # Restore old handle
                vendor.handle = old_handle
                vendor.save(update_fields=['handle'])
                self.stdout.write(self.style.ERROR('Aborted. Handle not changed.'))
                return
        
        # Apply changes
        if not dry_run:
            vendor.handle = new_handle
            vendor.save(update_fields=['handle'])
            
            if old_handle != new_handle:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'\n✓ Handle updated: {old_handle} → {new_handle}'
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f'\n  Handle unchanged: {new_handle}'
                    )
                )
            
            # Update portfolio URL
            if portfolio:
                update_portfolio_url(portfolio, vendor_handle=new_handle)
                self.stdout.write(self.style.SUCCESS('✓ Portfolio URL updated'))
                self.stdout.write(f'  New URL: {portfolio.portfolio_url}')
        
        self.stdout.write('\n' + '─' * 60)
        self.stdout.write(self.style.SUCCESS('✅ Handle regeneration complete!'))
        self.stdout.write('─' * 60)
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    '\nThis was a DRY RUN. Run without --dry-run to apply changes.'
                )
            )
