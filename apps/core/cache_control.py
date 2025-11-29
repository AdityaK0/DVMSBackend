# import threading
# _cache_state = threading.local()

# def disable_cache():
#     _cache_state.disabled = True

# def enable_cache():
#     _cache_state.disabled = False

# def is_cache_disabled():
#     return getattr(_cache_state, "disabled", False)

# apps/core/cache_control.py
import contextvars

_cache_disabled = contextvars.ContextVar("cache_disabled", default=False)

def disable_cache():
    _cache_disabled.set(True)

def enable_cache():
    _cache_disabled.set(False)

def is_cache_disabled():
    return _cache_disabled.get()
