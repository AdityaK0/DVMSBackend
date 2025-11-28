from django.utils import timezone
from .serializers import SubscriptionSerializer
from apps.core.cache_decorators import redis_cached

class SubscriptionService:

    @staticmethod
    @redis_cached("subscription",ttl=60*60*10)
    def get_vendor_subscription(vendor):
        """
        Fetch vendor subscription. If expired, deactivate automatically.
        Returns subscription or None.
        """
        print("this will be printed again after 10 hours only ")
    
        
        sub = getattr(vendor, "subscription", None)
        if not sub:
            return None

        # Auto-deactivate only when needed
        if sub.end_date and sub.end_date < timezone.now() and sub.is_active:
            sub.is_active = False
            sub.save(update_fields=["is_active"])

        return SubscriptionSerializer(sub).data
