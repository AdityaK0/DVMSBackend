from django.core.management.base import BaseCommand
from django.conf import settings
import sqlite3

class Command(BaseCommand):
    help = "Checkpoint WAL for a specific sqlite cache (e.g., product, vendor, user)"

    def add_arguments(self, parser):
        parser.add_argument("model", type=str, help="Cache model: product/vendor/user")

    def handle(self, *args, **options):
        model = options["model"]
        db_path = settings.SQLITE_CACHE_FILES.get(model)

        if not db_path:
            self.stdout.write(self.style.ERROR(f"Unknown model: {model}"))
            return

        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("PRAGMA wal_checkpoint(FULL)")
        conn.close()

        self.stdout.write(self.style.SUCCESS(f"Checkpoint completed for {model}"))
