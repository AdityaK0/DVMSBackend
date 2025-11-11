"""
Sync ONE vendor's Portfolio related data to Elasticsearch.
This script is executed only when vendor clicks "Publish site".
"""

import os
import django
from elasticsearch.helpers import bulk
from elasticsearch import Elasticsearch
import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)  #  ensures marketplace/apps becomes importable

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "marketplace.settings")
django.setup()

from apps.vendors.models import Vendor
from apps.products.models import Product
# from apps.portfolio.models import Portfolio, PortfolioCollection
from apps.portfolio.service import PortfolioService
from apps.products.service import get_vendor_products_combined



es = Elasticsearch("http://localhost:9205")


# ------------------ SERIALIZERS ------------------

def serialize_vendor(vendor):
    return {
        "_index": "vendor_index",
        "_id": vendor.id,

        # ES mapped fields
        "business_name": vendor.business_name,
        "business_name_slug": vendor.business_name_slug,
        "business_description": vendor.business_description,
        "business_email": vendor.business_email,
        "business_type": vendor.business_type,
        "business_phone": vendor.business_phone,
        "whatsapp_number": vendor.whatsapp_number,
        "gstin": vendor.gstin,
        "website": vendor.website,
        "user": vendor.user_id,  # FK stored as keyword

        # only fields that exist in mapping
        "is_onboarded": vendor.is_onboarded,
        "is_active": vendor.is_active,
        "is_verified": vendor.is_verified,

        "created_at": vendor.created_at,
        "updated_at": vendor.updated_at,
    }

def serialize_product(product): # currently not using this but will use this 
    return {
        "_index": "product_index",
        "_id": product.id,

        "vendor": product.vendor_id,  # ✅ must match ES mapping field type: keyword

        "name": product.name,
        "description": product.description,
        "category": product.category.name if product.category else None,

        "price": float(product.price),
        "cost_price": float(product.cost_price) if product.cost_price else None,
        "stock_quantity": product.stock_quantity,
        "min_stock_level": product.min_stock_level,
        "sku": product.sku,
        "weight": float(product.weight) if product.weight else None,
        "dimensions": product.dimensions,

        "is_active": product.is_active,
        "is_featured": product.is_featured,
        "is_archived": product.is_archived,

        "meta_title": product.meta_title,
        "meta_description": product.meta_description,

        "created_at": product.created_at,
        "updated_at": product.updated_at,
    }

def serialize_product_listing(vendor):
    """Sync ALL active vendor products to Elasticsearch regardless of count"""

    # from apps.portfolio.service import get_vendor_products_combined

    page = 1
    page_size = 500
    docs = []

    while True:
        result = get_vendor_products_combined(
            vendor=vendor,
            request=None,
            page=page,
            page_size=page_size,
            query="",
            include_private=False,
        )

        products = result["results"]
        print(f"📦 Fetching page {page} -> {len(products)} products")
        vendorID = vendor.id
        vendor_name = vendor.business_name
        

        if not products:
            break  # exit loop when no more products

        # convert each product into ES doc format
        for p in products:
            docs.append({
                "_index": "product_index",
                "_id": p["id"],
                "_source": {
                    **p,
                    "vendor_id": vendorID,
                    "vendor_name": vendor_name,
                    "business_name_slug": vendor.business_name_slug,  # added  this fetch the product as per business name
                }
            })

        # stop when last page
        if not result["has_next"]:
            break

        page += 1  # continue to next page

    print(f"✅ Prepared total {len(docs)} product docs")
    return docs

def serialize_portfolio(vendor_id):
    data = PortfolioService.get_public_vendor_portfolio(
        business_name=Vendor.objects.get(id=vendor_id).business_name_slug
    )

    return {
        "_index": "portfolio_index",
        "_id": data["id"],
        "_source": data,   # <-- store final JSON as-is
    }

def serialize_collections(vendor):
    data = PortfolioService.get_vendor_collections(vendor)
    docs = []

    for col in data:      # col is already in API ready format
        docs.append({
            "_index": "portfoliocollection_index",
            "_id": col["id"],
            "_source": {
                **col,
                "business_name_slug": vendor.business_name_slug  # added  this fetch the product as per business name
            }
        })

    print(f"📦 Prepared {len(docs)} collections docs")
    return docs


# ------------------ SYNC FUNCTION ------------------

def sync_vendor(vendor_id):
    print(f"🔄 Syncing vendor {vendor_id}...")

    vendor = Vendor.objects.get(id=vendor_id)

    plan = PortfolioService.create_vendor_sync_plan(vendor)

    if not plan.can_sync():
        return {"status": "blocked", "reason": "sync_limit_reached"}

    portfolio_doc = serialize_portfolio(vendor_id)
    collection_docs = serialize_collections(vendor)
    product_docs = serialize_product_listing(vendor)

    documents = [portfolio_doc] + collection_docs + product_docs

    doc_count = len(documents)
    print(f"== Preparing {doc_count} documents... ==")

    bulk(es, documents)

    plan.consume_sync()  # 🔥 Deduct usage

    print(f"==  ES updated for vendor {vendor.business_name} ==")

    return {
        "status": "success",
        "synced_docs": doc_count,
    }



if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise Exception("❌ Please pass vendor ID. Example: python -m scripts.es.sync_vendor_to_es 5")

    vendor_id = int(sys.argv[1])
    sync_vendor(vendor_id)
