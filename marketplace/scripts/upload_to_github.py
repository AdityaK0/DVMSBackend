import os
import requests
import base64
from django.conf import settings

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'marketplace.settings')
django.setup()
from apps.products.models import ProductImage  # adjust path if different




# ==== CONFIG ====
GITHUB_USERNAME = "AdityaKO2"
GITHUB_REPO = "product-images"
GITHUB_TOKEN = "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"
BRANCH = "main"

# Root path inside repo
BASE_FOLDER = "vendors"

API_BASE_URL = f"https://api.github.com/repos/{GITHUB_USERNAME}/{GITHUB_REPO}/contents"

def upload_to_github(image_url, vendor_id, product_id, filename):
    """Uploads image from URL to GitHub inside vendors/vendor_X/product_Y/ structure."""
    try:
        # 1️⃣ Download image from Cloudinary (or any source)
        response = requests.get(image_url)
        if response.status_code != 200:
            print(f"❌ Failed to fetch image: {image_url}")
            return None

        # 2️⃣ Convert to base64 for GitHub upload
        content_base64 = base64.b64encode(response.content).decode("utf-8")

        # 3️⃣ Prepare GitHub path
        github_path = f"{BASE_FOLDER}/vendor_{vendor_id}/product_{product_id}/{filename}"
        upload_url = f"{API_BASE_URL}/{github_path}"

        # 4️⃣ Make API request to GitHub
        data = {
            "message": f"Add {filename} for vendor {vendor_id}, product {product_id}",
            "content": content_base64,
            "branch": BRANCH
        }

        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json"
        }

        upload_response = requests.put(upload_url, json=data, headers=headers)

        if upload_response.status_code in [200, 201]:
            raw_url = (
                f"https://raw.githubusercontent.com/"
                f"{GITHUB_USERNAME}/{GITHUB_REPO}/{BRANCH}/{github_path}"
            )
            print(f"✅ Uploaded: {raw_url}")
            return raw_url
        else:
            print(f"❌ Upload failed: {upload_response.status_code} - {upload_response.text}")
            return None

    except Exception as e:
        print(f"⚠️ Error uploading {image_url}: {e}")
        return None


def migrate_images_to_github():
    """Main migration process."""
    images = ProductImage.objects.filter(github_image_url__isnull=True)
    print(f"Found {images.count()} images to process...")

    for img in images:
        if not img.image.url:
            print(f"⚠️ Skipping {img.id}: No image_url")
            continue

        product = img.product
        vendor = product.vendor

        vendor_id = vendor.id if vendor else "unknown"
        product_id = product.id
        filename = f"img_{img.id}.jpg"

        new_url = upload_to_github(img.image.url, vendor_id, product_id, filename)

        if new_url:
            img.github_image_url = new_url
            img.save(update_fields=["github_image_url"])
            print(f"✅ DB updated for Image ID {img.id}")
        else:
            print(f"❌ Failed for Image ID {img.id}")

    print("🎯 Migration complete!")

if __name__ == "__main__":
    migrate_images_to_github()
