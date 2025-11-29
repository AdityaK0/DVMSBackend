import threading
_cache_state = threading.local()

def disable_cache():
    _cache_state.disabled = True

def enable_cache():
    _cache_state.disabled = False

def is_cache_disabled():
    return getattr(_cache_state, "disabled", False)
