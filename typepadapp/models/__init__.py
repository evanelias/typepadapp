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


def configure_typepad_client():
    typepad.client.endpoint = settings.BACKEND_URL

    log.info('Configuring caching')
    # FIXME: Should the cache directory vary based on the group xid?
    typepad.client.cache = httplib2.FileCache(tempfile.mkdtemp(prefix='httpcache-'))

    if settings.TYPEPAD_COOKIES:
        typepad.client.cookies.update(settings.TYPEPAD_COOKIES)

    if not settings.BATCH_REQUESTS:
        typepad.TypePadObject.batch_requests = False

configure_typepad_client()


def clear_client_request(signal, sender, **kwargs):
    typepad.client.clear_batch()

django.core.signals.request_finished.connect(clear_client_request)
