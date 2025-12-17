import logging
from django.db import transaction
from apps.vendors.models import VendorStats

logger = logging.getLogger(__name__)


class CustomerCreatedSubscriber:
    """
    Authoritative handler for customer.created
    Increments customer counters.
    """
    critical = True

    def __call__(self, event):
        vendor_id = event.metadata["vendor_id"]
        is_active = event.data.get("is_active", True)

        try:
            with transaction.atomic():
                stats = VendorStats.objects.select_for_update().get(
                    vendor_id=vendor_id
                )

                stats.total_customers += 1

                if is_active:
                    stats.active_customers += 1
                else:
                    stats.inactive_customers += 1

                stats.save(update_fields=[
                    "total_customers",
                    "active_customers",
                    "inactive_customers",
                ])

                logger.info(
                    f"CustomerCreated → VendorStats updated "
                    f"(vendor={vendor_id}, total={stats.total_customers})"
                )

        except VendorStats.DoesNotExist:
            logger.critical(f"VendorStats missing for vendor_id={vendor_id}")
            raise

        except Exception:
            logger.exception("CustomerCreatedSubscriber failed")
            raise


class CustomerUpdatedSubscriber:
    """
    Authoritative handler for customer.updated
    Handles is_active transitions.
    """
    critical = True

    def __call__(self, event):
        vendor_id = event.metadata["vendor_id"]
        old_is_active = event.metadata.get("old_is_active")
        new_is_active = event.metadata.get("new_is_active")

        # No meaningful change → skip
        if old_is_active == new_is_active:
            return

        try:
            with transaction.atomic():
                stats = VendorStats.objects.select_for_update().get(
                    vendor_id=vendor_id
                )

                if old_is_active and not new_is_active:
                    stats.active_customers -= 1
                    stats.inactive_customers += 1

                elif not old_is_active and new_is_active:
                    stats.active_customers += 1
                    stats.inactive_customers -= 1

                stats.active_customers = max(stats.active_customers, 0)
                stats.inactive_customers = max(stats.inactive_customers, 0)

                stats.save(update_fields=[
                    "active_customers",
                    "inactive_customers",
                ])

                logger.info(
                    f"CustomerUpdated → VendorStats updated "
                    f"(vendor={vendor_id})"
                )

        except VendorStats.DoesNotExist:
            logger.critical(f"VendorStats missing for vendor_id={vendor_id}")
            raise

        except Exception:
            logger.exception("CustomerUpdatedSubscriber failed")
            raise


class CustomerDeletedSubscriber:
    """
    Authoritative handler for customer.deleted
    Decrements customer counters.
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

                stats.total_customers -= 1

                if was_active:
                    stats.active_customers -= 1
                else:
                    stats.inactive_customers -= 1

                # Safety guards
                stats.total_customers = max(stats.total_customers, 0)
                stats.active_customers = max(stats.active_customers, 0)
                stats.inactive_customers = max(stats.inactive_customers, 0)

                stats.save(update_fields=[
                    "total_customers",
                    "active_customers",
                    "inactive_customers",
                ])

                logger.info(
                    f"CustomerDeleted → VendorStats updated "
                    f"(vendor={vendor_id})"
                )

        except VendorStats.DoesNotExist:
            logger.critical(f"VendorStats missing for vendor_id={vendor_id}")
            raise

        except Exception:
            logger.exception("CustomerDeletedSubscriber failed")
            raise
