from django.core.management.base import BaseCommand
from scripts.es.sync_vendor_to_es import sync_vendor


class Command(BaseCommand):
    help = "Sync specific vendor data to Elasticsearch"

    def add_arguments(self, parser):
        parser.add_argument("vendor_id", type=int, help="Vendor ID to sync")

    def handle(self, *args, **kwargs):
        sync_vendor(kwargs["vendor_id"])
        self.stdout.write(self.style.SUCCESS(f"Vendor synced ({kwargs['vendor_id']})"))
