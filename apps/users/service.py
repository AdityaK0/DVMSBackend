from apps.users.models import User
from .serializers import UserSerializer
from apps.core.cache_decorators import redis_cached
import logging

logger = logging.getLogger(__name__)


from apps.users.models import User
class UserService:
    
    @staticmethod
    @redis_cached("user:context", "user_id", ttl=60 * 5)  # ✅ Standardized key: user:context:{user_id}
    def get_user(user_id):
        """
        Returns complete authenticated user context:
        - user info
        - addresses
        """ 
        user = (
            User.objects
            .select_related("vendor")
            .prefetch_related(
                "addresses",
                "vendor__user__addresses"
            )
            .get(id=user_id)
        )

        data = {
            "user": UserSerializer(user).data,
        }
        return data
