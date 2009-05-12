import logging
from django.core.cache import cache


class CachedProperty(object):
    """ Cached property descriptor.
        The object with the cached property
        must also have an id property.
        This is still very much in-progress.
        TODO add update?
    """

    def __init__(self, func):
        self.func = func

    def key(self, obj):
        return 'CachedProperty_%s_%s_%s' % \
            (obj.__class__.__name__, self.func.__name__, obj._location)

    def __get__(self, obj, type=None):
        key = self.key(obj)
        # local memory
        if not hasattr(self, key):
            # cache system
            val = cache.get(key)
            if val is None:
                # expensive
                val = self.func(obj)
                cache.set(key, val)
                logging.debug('%s from db' % key)
            else:
                logging.debug('%s from cache' % key)
            setattr(self, key, val)
        else:
            logging.debug('%s from mem' % key)
        return getattr(self, key)

    def __delete__(self, obj):
        # hmm... use this to clear the cache
        key = self.key(obj)
        delattr(self, key)
        cache.delete(key)

# pretty decorator
cached_property = CachedProperty

def cached_function(func):
    """ Pretty decorator for functions. """

    cached = CachedProperty(func)

    def cached_func(self):
        return cached.__get__(self)

    return cached_func