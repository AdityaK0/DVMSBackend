# apps/core/management/commands/init_sqlite_cache.py
from django.core.management.base import BaseCommand
from django.conf import settings
import sqlite3
import os


# need speed and more concurrency this can be easily used 

# PRAGMA journal_mode = WAL;    
# PRAGMA synchronous = NORMAL;

# else below is normally i will prefer to use to see the current logs and data 


SCHEMAS = {
    
    
    "product": """
        PRAGMA journal_mode = WAL;
        PRAGMA synchronous = NORMAL;
        CREATE TABLE IF NOT EXISTS cache_product (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL UNIQUE,
            vendor_id INTEGER NOT NULL,
            data TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_cache_product_vendor ON cache_product(vendor_id);
        CREATE INDEX IF NOT EXISTS idx_cache_product_updated_at ON cache_product(updated_at);
    """,
    
    
    "vendor": """
        PRAGMA journal_mode = WAL;
        PRAGMA synchronous = NORMAL;
        CREATE TABLE IF NOT EXISTS cache_vendor (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vendor_id INTEGER NOT NULL UNIQUE,
            data TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_cache_vendor_updated_at ON cache_vendor(updated_at);
    """,
    
    
    "user": """
        PRAGMA journal_mode = WAL;
        PRAGMA synchronous = NORMAL;
        CREATE TABLE IF NOT EXISTS cache_user (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            data TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_cache_user_updated_at ON cache_user(updated_at);
    """,
}

class Command(BaseCommand):
    help = "Initialize sqlite cache DB files and tables"

    def handle(self, *args, **options):
        outdir = settings.SQLITE_CACHE_DIR
        os.makedirs(outdir, exist_ok=True)
        for name, schema in SCHEMAS.items():
            db_path = settings.SQLITE_CACHE_FILES.get(name)
            if not db_path:
                self.stdout.write(self.style.WARNING(f"No DB path configured for {name}"))
                continue
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            for stmt in schema.split(";"):
                stmt = stmt.strip()
                if not stmt:
                    continue
                try:
                    cur.execute(stmt)
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Failed to execute on {name}: {e}"))
            conn.commit()
            conn.close()
            self.stdout.write(self.style.SUCCESS(f"Initialized {db_path}"))
