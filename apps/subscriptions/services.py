from django.utils import timezone
from .serializers import SubscriptionSerializer
from apps.core.cache_decorators import redis_cached
from .models import Subscription

class SubscriptionService:

    @staticmethod
    @redis_cached("subscription:vendor", "vendor_id", ttl=60 * 15)  # ✅ Standardized key: subscription:vendor:{vendor_id}
    def get_vendor_subscription(vendor_id):
        """
        Fetch vendor subscription. If expired, deactivate automatically.
        Returns subscription or None.
        """
        sub = Subscription.objects.filter(
            vendor_id=vendor_id
        ).select_related("plan").first()
    
        
        if not sub:
            return None

        # Auto-deactivate only when needed
        if sub.end_date and sub.end_date < timezone.now() and sub.is_active:
            sub.is_active = False
            sub.save(update_fields=["is_active"])

        return SubscriptionSerializer(sub).data
