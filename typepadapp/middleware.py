import logging
import random
from types import MethodType
from urlparse import urlparse
from urllib import urlencode, quote

from django.conf import settings
from django.core.urlresolvers import reverse
from oauth import oauth

import typepad
from typepadapp.models.auth import OAuthClient
import typepadapp.models


def gp_signed_url(url, params):
    """
    Generate a signed URL using the applications OAuth general purpose token.
    """
    token = oauth.OAuthToken(settings.OAUTH_GENERAL_PURPOSE_KEY, settings.OAUTH_GENERAL_PURPOSE_SECRET)
    consumer = oauth.OAuthConsumer(settings.OAUTH_CONSUMER_KEY, settings.OAUTH_CONSUMER_SECRET)

    req = oauth.OAuthRequest.from_consumer_and_token(
        consumer,
        token = token,
        http_method = 'GET',
        http_url = url,
        parameters = params,
    )
    req.sign_request(oauth.OAuthSignatureMethod_HMAC_SHA1(), consumer, token)
    return req.to_url()


def get_session_synchronization_url(self, callback_url=None):
    # oauth GET params for session synchronization
    # since the request comes from a script tag
    if not callback_url:
        params = {
            'callback_nonce': self.session.get('callback_nonce'),
            'callback_next': self.build_absolute_uri(),
        }
        # TODO: Er, seems like we should be urlencoding the params here but that breaks things. Giving up on figuring out why that is for the moment.
        #callback_url = '%s?%s' % (self.build_absolute_uri(reverse('synchronize')), urlencode(params))
        callback_url = '%s?%s' % (self.build_absolute_uri(reverse('synchronize')), '&'.join(['='.join(i) for i in params.items()]))

    current_token = self.session.get('oauth_token', None)
    if current_token:
        current_token = current_token.session_sync_token
    else:
        current_token = self.session.get('lost_session_sync_token', '')

    return gp_signed_url(self.oauth_client.session_sync_url,
                         { 'callback_url': callback_url, 'session_sync_token': current_token })


def get_oauth_identification_url(self, next):
    params = {
        'callback_nonce': self.session.get('callback_nonce'),
        'callback_next': self.build_absolute_uri(next),
        'signin': '1',
    }
    # TODO: same question as above w/ urlencoding.
    callback_url = '%s?%s' % (self.build_absolute_uri(reverse('synchronize')), '&'.join(['='.join(i) for i in params.items()]))
    return gp_signed_url(self.oauth_client.oauth_identification_url, { 'callback_url': callback_url })


class UserAgentMiddleware:

    def process_request(self, request):
        """For a logged-in user, adds an authed http object to
        the request. Otherwise, adds the app's own OAuth token.
        This middleware needs to be after the session middleware.
        """

        request.oauth_client = OAuthClient(request.application)
        typepad.client.clear_credentials()

        # Make sure there's a nonce in the session to use
        # in generating the synchronization URI.
        if not request.session.get('callback_nonce'):
            request.session['callback_nonce'] = ''.join([str(random.randint(0,9)) for i in xrange(8)])

        token = request.session.get('oauth_token')
        if token is None:
            request.oauth_client.token = oauth.OAuthToken(settings.OAUTH_GENERAL_PURPOSE_KEY, settings.OAUTH_GENERAL_PURPOSE_SECRET)
        else:
            request.oauth_client.token = token

        backend = urlparse(settings.BACKEND_URL)
        typepad.client.add_credentials(request.oauth_client.consumer,
            request.oauth_client.token, domain=backend[1])

        # install get_session_synchronization_url & get_oauth_identification_url method on request object
        setattr(request, 'get_session_synchronization_url',
                MethodType(get_session_synchronization_url, request, request.__class__))
        setattr(request, 'get_oauth_identification_url',
                MethodType(get_oauth_identification_url, request, request.__class__))

        return None


class ApplicationMiddleware(object):

    def __init__(self):
        self.application = None
        self.group = None

    def discover_group(self, request):
        # TODO: pick a group based on the request, not global settings.

        log = logging.getLogger('.'.join((self.__module__, self.__class__.__name__)))

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

        self.application = app
        self.group = group
        return app, group

    def process_request(self, request):
        """Adds the application and group to the request."""

        if self.application is None or self.group is None:
            self.discover_group(request)

        # TODO: Don't pretend these are singletons once we always pull them
        # from the request.
        typepadapp.models.GROUP = self.group
        typepadapp.models.APPLICATION = self.application

        request.application = self.application
        request.group = self.group

        return None
