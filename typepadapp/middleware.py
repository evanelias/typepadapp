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

        request.oauth_client = OAuthClient()
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


class ApplicationMiddleware:
    
    def process_request(self, request):
        """Adds the application and group to the request."""
        request.application = typepadapp.models.APPLICATION
        request.group = typepadapp.models.GROUP
        return None
