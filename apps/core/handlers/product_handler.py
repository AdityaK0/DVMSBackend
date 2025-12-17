# core/handlers/product_handler.py

import logging
from django.core.cache import cache
from apps.vendors.models import VendorStats
from django.db import transaction
logger = logging.getLogger(__name__)

class ProductCreatedSubscriber:
    """
    Authoritative handler for product.created
    Updates VendorStats counters safely.
    """
    critical = True 

    def __call__(self, event):
        vendor_id = event.metadata["vendor_id"]
        is_active = event.metadata.get("is_active", True)

        try:
            with transaction.atomic():
                stats = VendorStats.objects.select_for_update().get(
                    vendor_id=vendor_id
                )

                stats.total_products += 1

                if is_active:
                    stats.active_products += 1
                else:
                    stats.inactive_products += 1

                stats.save(update_fields=[
                    "total_products",
                    "active_products",
                    "inactive_products"
                ])

                logger.info(
                    f"VendorStats updated for vendor={vendor_id} "
                    f"(total={stats.total_products})"
                )

        except VendorStats.DoesNotExist:
            # This should NEVER happen if onboarding is correct
            logger.critical(
                f"VendorStats missing for vendor_id={vendor_id}"
            )
            raise

        except Exception:
            logger.exception("ProductCreatedSubscriber failed")
            raise

class ProductUpdatedSubscriber:
    """
    Authoritative handler for product.updated.
    Handles is_active state transitions.
    """
    critical = True

    def __call__(self, event):
        vendor_id = event.metadata["vendor_id"]
        old_is_active = event.metadata.get("old_is_active")
        new_is_active = event.metadata.get("new_is_active")

        if old_is_active == new_is_active:
            logger.info("ProductUpdated: is_active unchanged, skipping stats update")
            return

        try:
            with transaction.atomic():
                stats = VendorStats.objects.select_for_update().get(
                    vendor_id=vendor_id
                )

                if old_is_active and not new_is_active:
                    stats.active_products -= 1
                    stats.inactive_products += 1

                elif not old_is_active and new_is_active:
                    stats.active_products += 1
                    stats.inactive_products -= 1

                stats.save(update_fields=[
                    "active_products",
                    "inactive_products"
                ])

                logger.info(
                    f"VendorStats updated for vendor={vendor_id} "
                    f"(active={stats.active_products}, inactive={stats.inactive_products})"
                )

        except VendorStats.DoesNotExist:
            logger.critical(f"VendorStats missing for vendor_id={vendor_id}")
            raise

        except Exception:
            logger.exception("ProductUpdatedSubscriber failed")
            raise


class ProductDeletedSubscriber:
    """
    Authoritative handler for product.deleted.
    Decrements VendorStats counters safely.
    """
    critical = True

    def __call__(self, event):
        vendor_id = event.metadata["vendor_id"]
        was_active = event.metadata.get("was_active", True)

        try:
            with transaction.atomic():
                stats = VendorStats.objects.select_for_update().get(
                    vendor_id=vendor_id
                )

                stats.total_products -= 1

                if was_active:
                    stats.active_products -= 1
                else:
                    stats.inactive_products -= 1

                # Safety guard (never go negative)
                stats.total_products = max(stats.total_products, 0)
                stats.active_products = max(stats.active_products, 0)
                stats.inactive_products = max(stats.inactive_products, 0)

                stats.save(update_fields=[
                    "total_products",
                    "active_products",
                    "inactive_products"
                ])

                logger.info(
                    f"VendorStats decremented for vendor={vendor_id} "
                    f"(total={stats.total_products})"
                )

        except VendorStats.DoesNotExist:
            logger.critical(f"VendorStats missing for vendor_id={vendor_id}")
            raise

        except Exception:
            logger.exception("ProductDeletedSubscriber failed")
            raise