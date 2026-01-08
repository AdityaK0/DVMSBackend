import os
import uuid
import requests
from urllib.parse import urlparse

import boto3
from django.conf import settings
from django.core.management.base import BaseCommand
from apps.products.models import Product


class Command(BaseCommand):
    help = "Migrate product images from old S3 to new S3 bucket (skip failures)"

    def handle(self, *args, **options):
        s3 = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME,
        )

        products = Product.objects.exclude(image_urls=[])

        self.stdout.write(f"Found {products.count()} products")

        for product in products:
            self.stdout.write(f"\n▶ Product {product.id}")

            old_urls = product.image_urls or []
            if not old_urls:
                continue

            # Deduplicate but preserve order
            seen = set()
            unique_urls = []
            for url in old_urls:
                if url not in seen:
                    seen.add(url)
                    unique_urls.append(url)

            migrated_urls = []

            for old_url in unique_urls:
                try:
                    new_url = self.migrate_single_image(
                        s3=s3,
                        vendor_id=product.vendor_id,
                        old_url=old_url,
                    )
                    if new_url:
                        migrated_urls.append(new_url)
                except Exception as e:
                    self.stderr.write(
                        f"⚠️  Skipping image for product {product.id}: {old_url}\n"
                        f"    Reason: {e}"
                    )
                    continue

            if not migrated_urls:
                self.stderr.write(
                    f"❌ No images migrated for product {product.id}, skipping DB update"
                )
                continue

            # PRIMARY IMAGE = FIRST IMAGE
            product.image_urls = migrated_urls
            product.primary_image = migrated_urls[0]

            product.save(update_fields=["image_urls", "primary_image"])

        self.stdout.write(self.style.SUCCESS("\n✅ Product image migration completed"))

    def migrate_single_image(self, *, s3, vendor_id, old_url):
        """
        Downloads image from old public URL and uploads to new S3.
        Skips upload if already migrated.
        """

        # Already migrated → skip
        if old_url.startswith(settings.AWS_S3_BASE_URL):
            return old_url

        parsed = urlparse(old_url)
        filename = os.path.basename(parsed.path) or f"{uuid.uuid4()}.jpg"

        s3_key = f"vendor/{vendor_id}/products/{filename}"
        new_url = f"{settings.AWS_S3_BASE_URL}/{s3_key}"

        response = requests.get(old_url, timeout=20)
        response.raise_for_status()

        s3.put_object(
            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
            Key=s3_key,
            Body=response.content,
            ContentType=response.headers.get("Content-Type", "image/jpeg"),
            CacheControl="public, max-age=31536000, immutable",
        )

        return new_url
