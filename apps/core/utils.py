from django.core.cache import cache

def invalidate_user_cache(user_id=None,vendor_id=None):
    
    if user_id:
        keys = [
            f"user:{user_id}",       # your @redis_cached key
            f"auth_user:{user_id}",         # CachedJWTAuthentication
            f"user_vendor_id:{user_id}"     # vendor id cache
            f"subscription:{user_id}"
        ]
    
    if vendor_id:
        keys + [
            
        ]    

    for key in keys:
        cache.delete(key)



def invalidate_subscription_cache(user_id=None):
    
    if user_id:
        keys = [
            f"user:{user_id}",       # your @redis_cached key
            f"auth_user:{user_id}",         # CachedJWTAuthentication
            f"user_vendor_id:{user_id}"     # vendor id cache
            f"subscription:{user_id}"
        ]
        

    for key in keys:
        cache.delete(key)