import logging
import tempfile
import sys
from urlparse import urlparse

import httplib2
from django.conf import settings
import django.core.cache
from django.core.cache.backends.base import InvalidCacheBackendError
import django.core.signals
from django.utils.encoding import smart_unicode
from oauth import oauth
HAS_MEMCACHED = False
try:
    import django.core.cache.backends.memcached as memcached
    HAS_MEMCACHED = True
except InvalidCacheBackendError:
    pass

import typepad
from typepadapp.signals import post_start


def configure_logging(**kwargs):
    log = logging.getLogger('')
    for handler in log.handlers:
        log.removeHandler(handler)
    log.setLevel(settings.LOG_LEVEL)

    handler = logging.StreamHandler()
    formatter = logging.Formatter(settings.LOG_FORMAT)
    handler.setFormatter(formatter)
    log.addHandler(handler)

    log.info('Reconfigured logging')

    for logger, level in settings.LOG_LEVELS.items():
        log = logging.getLogger(logger)
        log.setLevel(level)

post_start.connect(configure_logging)


class DjangoHttplib2Cache(object):

    """Adapts the Django low-level caching API to the httplib2 HTTP cache
    interface, passing through the supported calls after prefixing all keys
    with ``httpcache_``."""

    def __init__(self, cache=None):
        if cache is None:
            cache = django.core.cache.cache
        self.is_memcached = HAS_MEMCACHED and isinstance(cache, memcached.CacheClass)
        self.cache = cache

    def get(self, key):
        val = self.cache.get('httpcache_%s' % (key,))
        # Django's memcache backend upgrades everything to unicode, so do
        # handle it with care; httplib2 expects data to come back as
        # bytes, not unicode
        if self.is_memcached:
            if val is None:
                return val
            return smart_unicode(val, errors='replace').encode('utf8')
        return val

    def set(self, key, value):
        # Don't store invalid unicode strings.
        if self.is_memcached and isinstance(value, str):
            value = value.decode('utf8', 'replace')
        self.cache.set('httpcache_%s' % (key,), value)

    def delete(self, key):
        self.cache.delete('httpcache_%s' % (key,))


def configure_typepad_client(**kwargs):
    typepad.client.endpoint = settings.BACKEND_URL

    log = logging.getLogger('typepadapp.utils.loading')
    log.info('Configuring HTTP caching')
    typepad.client.cache = DjangoHttplib2Cache()

    if settings.TYPEPAD_COOKIES:
        typepad.client.cookies.update(settings.TYPEPAD_COOKIES)

    if not settings.BATCH_REQUESTS:
        typepad.TypePadObject.batch_requests = False

post_start.connect(configure_typepad_client)


def clear_client_request(signal, sender, **kwargs):
    typepad.client.clear_batch()

django.core.signals.request_finished.connect(clear_client_request)
