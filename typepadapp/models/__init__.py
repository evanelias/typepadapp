from assets import *
from auth import *
from groups import *
from users import *
from profiles import *


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


def discover_group():
    log.info('Loading group info...')
    app, group = None, None

    # FIXME: Shouldn't need to do oauth manually here
    consumer = oauth.OAuthConsumer(settings.OAUTH_CONSUMER_KEY, settings.OAUTH_CONSUMER_SECRET)
    token = oauth.OAuthToken(settings.OAUTH_GENERAL_PURPOSE_KEY, settings.OAUTH_GENERAL_PURPOSE_SECRET)
    backend = urlparse(settings.BACKEND_URL)
    typepad.client.clear_credentials()
    typepad.client.add_credentials(consumer, token, domain=backend[1])

    typepad.client.batch_request()
    # FIXME: handle failure here...
    try:
        app = typepad.Application.get_by_api_key(settings.TYPEPAD_API_KEY)
        typepad.client.complete_batch()
    except Exception, exc:
        log.error('Error loading Application %s: %s' % (settings.OAUTH_CONSUMER_KEY, str(exc)))
        raise

    group = app.owner

    # FIXME: shouldn't need to do a separate batch request for the group here
    # we already have the group data through APPLICATION.owner...
    typepad.client.batch_request()
    try:
        group.admin_list = group.memberships.filter(admin=True)
        typepad.client.complete_batch()
    except Exception, exc:
        log.error('Error loading Group %s: %s', app.owner.id, str(exc))
        raise

    log.info("Running for group: %s", group.display_name)

    if settings.SESSION_COOKIE_NAME is None:
        settings.SESSION_COOKIE_NAME = "sg_%s" % group.id

    return app, group


try:
    APPLICATION, GROUP = discover_group()
except Exception:
    import sys
    if 'manage.py' not in ' '.join(sys.argv) or 'runserver' in sys.argv:
        raise


def clear_client_request(signal, sender, **kwargs):
    typepad.client.clear_batch()

django.core.signals.request_finished.connect(clear_client_request)
