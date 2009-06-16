from assets import *
from auth import *
from groups import *
from users import *
from profiles import *


APPLICATION, GROUP = None, None


## TODO move this
import logging
import tempfile
import sys
from urlparse import urlparse

import httplib2
from django.conf import settings
from django.core.cache import cache
import django.core.signals
from oauth import oauth

import typepad


def configure_logging():
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

configure_logging()


log = logging.getLogger('typepadapp.models')


class DjangoHttplib2Cache(object):

    """Adapts the Django low-level caching API to the httplib2 HTTP cache
    interface, passing through the supported calls after prefixing all keys
    with ``httpcache_``."""

    def get(self, key):
        return cache.get('httpcache_%s' % (key,))

    def set(self, key, value):
        cache.set('httpcache_%s' % (key,), value)

    def delete(self, key):
        cache.delete('httpcache_%s' % (key,))


def configure_typepad_client():
    typepad.client.endpoint = settings.BACKEND_URL

    log.info('Configuring HTTP caching')
    typepad.client.cache = DjangoHttplib2Cache()

    if settings.TYPEPAD_COOKIES:
        typepad.client.cookies.update(settings.TYPEPAD_COOKIES)

    if not settings.BATCH_REQUESTS:
        typepad.TypePadObject.batch_requests = False

configure_typepad_client()


def clear_client_request(signal, sender, **kwargs):
    typepad.client.clear_batch()

django.core.signals.request_finished.connect(clear_client_request)
