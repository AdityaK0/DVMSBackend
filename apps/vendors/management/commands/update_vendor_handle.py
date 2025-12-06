"""
Admin-only management command to update vendor handle and business name.

⚠️ USE WITH CAUTION - This bypasses normal validation!

Usage:
    python manage.py update_vendor_handle <vendor_id> --handle <new_handle>
    python manage.py update_vendor_handle <vendor_id> --business-name "New Name"
    python manage.py update_vendor_handle <vendor_id> --handle <new_handle> --business-name "New Name"
"""

from django.core.management.base import BaseCommand, CommandError
from apps.vendors.models import Vendor
from apps.portfolio.models import Portfolio
from apps.utils.update_things import update_portfolio_url
from django.utils.text import slugify


class Command(BaseCommand):
    help = 'Admin-only: Update vendor handle and/or business name (bypasses normal restrictions)'

    def add_arguments(self, parser):
        parser.add_argument(
            'vendor_id',
            type=int,
            help='Vendor ID to update'
        )
        parser.add_argument(
            '--handle',
            type=str,
            help='New handle for the vendor'
        )
        parser.add_argument(
            '--business-name',
            type=str,
            help='New business name for the vendor'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Skip confirmation prompt'
        )

    def handle(self, *args, **options):
        vendor_id = options['vendor_id']
        new_handle = options.get('handle')
        new_business_name = options.get('business_name')
        force = options['force']

        if not new_handle and not new_business_name:
            raise CommandError('You must specify at least --handle or --business-name')

        # Get vendor
        try:
            vendor = Vendor.objects.get(id=vendor_id)
        except Vendor.DoesNotExist:
            raise CommandError(f'Vendor with ID {vendor_id} does not exist')

        # Show current state
        self.stdout.write(self.style.WARNING('\n⚠️  ADMIN OVERRIDE - HANDLE/NAME UPDATE'))
        self.stdout.write('─' * 60)
        self.stdout.write(f'Vendor ID: {vendor.id}')
        self.stdout.write(f'Current Business Name: {vendor.business_name}')
        self.stdout.write(f'Current Handle: {vendor.handle}')
        self.stdout.write(f'Current Portfolio URL: {vendor.portfolio.portfolio_url if hasattr(vendor, "portfolio") else "N/A"}')
        self.stdout.write('─' * 60)

        # Show proposed changes
        if new_business_name:
            self.stdout.write(f'New Business Name: {new_business_name}')
        if new_handle:
            self.stdout.write(f'New Handle: {new_handle}')
            # Check if handle is already taken
            if Vendor.objects.filter(handle=new_handle).exclude(id=vendor_id).exists():
                raise CommandError(f'Handle "{new_handle}" is already taken by another vendor!')
        
        self.stdout.write('─' * 60)

        # Confirmation
        if not force:
            confirm = input('\n  This will update the vendor. Continue? (yes/no): ')
            if confirm.lower() != 'yes':
                self.stdout.write(self.style.ERROR('Aborted.'))
                return

        # Perform updates
        old_handle = vendor.handle
        old_name = vendor.business_name

        if new_business_name:
            vendor.business_name = new_business_name
            vendor.business_name_slug = slugify(f"{new_business_name}-{vendor.id}")
            self.stdout.write(self.style.SUCCESS(f'✓ Updated business name: {old_name} → {new_business_name}'))

        if new_handle:
            vendor.handle = new_handle
            self.stdout.write(self.style.SUCCESS(f'✓ Updated handle: {old_handle} → {new_handle}'))

        vendor.save()

        # Update portfolio URL if handle changed
        if new_handle:
            try:
                portfolio = Portfolio.objects.get(vendor=vendor)
                old_url = portfolio.portfolio_url
                update_portfolio_url(portfolio, vendor_handle=new_handle)
                self.stdout.write(self.style.SUCCESS(f'✓ Updated portfolio URL'))
                self.stdout.write(f'  Old: {old_url}')
                self.stdout.write(f'  New: {portfolio.portfolio_url}')
            except Portfolio.DoesNotExist:
                self.stdout.write(self.style.WARNING('  No portfolio found for this vendor'))

        self.stdout.write('\n' + '─' * 60)
        self.stdout.write(self.style.SUCCESS('✅ Vendor updated successfully!'))
        self.stdout.write('─' * 60)
        self.stdout.write(f'Vendor ID: {vendor.id}')
        self.stdout.write(f'Business Name: {vendor.business_name}')
        self.stdout.write(f'Handle: {vendor.handle}')
        if hasattr(vendor, 'portfolio'):
            self.stdout.write(f'Portfolio URL: {vendor.portfolio.portfolio_url}')
        self.stdout.write('─' * 60)
