from copy import deepcopy

_cached_services = None

def save_to_cache(data):
    """Save a copy of the lastest successful database response."""
    global _cached_services
    _cached_services = deepcopy(data)


def get_cached_services():
    """Return the lastest successful cached response."""
    return deepcopy(_cached_services)