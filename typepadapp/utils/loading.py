# Copyright (c) 2009-2010 Six Apart Ltd.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# * Neither the name of Six Apart Ltd. nor the names of its contributors may
#   be used to endorse or promote products derived from this software without
#   specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

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
        # for our http cache, this is typically for things we don't
        # even want to cache, like OAuth communications
        if len(key) > 250:
            return None

        val = self.cache.get('httpcache_%s' % (key,))
        # Django's memcache backend upgrades everything to unicode, so do
        # handle it with care; httplib2 expects data to come back as
        # bytes, not unicode
        if self.is_memcached:
            if val is None:
                return val
            if isinstance(val, str):
                return smart_unicode(val, errors='replace').encode('utf8')
        return val

    def set(self, key, value):
        if len(key) > 250:
            return

        # Don't store invalid unicode strings.
        if self.is_memcached and isinstance(value, str):
            value = value.decode('utf8', 'replace')
        self.cache.set('httpcache_%s' % (key,), value)

    def delete(self, key):
        if len(key) > 250:
            return

        self.cache.delete('httpcache_%s' % (key,))


def configure_typepad_client(**kwargs):
    if settings.FRONTEND_CACHING:
        # this will create a typepad.client that caches
        from typepadapp.caching import CachingTypePadClient
        # lets increase that timeout to 20 seconds
        typepad.client = CachingTypePadClient(timeout=20)

    if not typepad.client:
        typepad.client = TypePadClient()

    typepad.client.endpoint = settings.BACKEND_URL

    log = logging.getLogger('typepadapp.utils.loading')
    # log.info('Configuring HTTP caching')
    # typepad.client.cache = DjangoHttplib2Cache()

    if settings.TYPEPAD_COOKIES:
        typepad.client.cookies.update(settings.TYPEPAD_COOKIES)

    if not settings.BATCH_REQUESTS:
        typepad.TypePadObject.batch_requests = False

post_start.connect(configure_typepad_client)


def clear_client_request(signal, sender, **kwargs):
    typepad.client.clear_batch()

django.core.signals.request_finished.connect(clear_client_request)
