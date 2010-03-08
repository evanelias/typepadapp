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
import random
import sys
from types import MethodType
from urlparse import urlparse
from urllib import urlencode, quote
import re

from django.conf import settings
from django.contrib.sessions.models import Session
from django.core.urlresolvers import reverse
from django.core.exceptions import MiddlewareNotUsed
from django.core.cache import cache
from django.db import DatabaseError
from oauth import oauth

import typepad
from typepadapp.models.auth import OAuthClient
import typepadapp.models
from batchhttp.client import NonBatchResponseError


log = logging.getLogger(__name__)


def gp_signed_url(url, params, http_method='GET'):
    """
    Generate a signed URL using the applications OAuth general purpose token.
    """
    token = oauth.OAuthToken(settings.OAUTH_GENERAL_PURPOSE_KEY, settings.OAUTH_GENERAL_PURPOSE_SECRET)
    consumer = oauth.OAuthConsumer(settings.OAUTH_CONSUMER_KEY, settings.OAUTH_CONSUMER_SECRET)

    req = oauth.OAuthRequest.from_consumer_and_token(
        consumer,
        token=token,
        http_method=http_method,
        http_url=url,
        parameters=params,
    )

    sign_method = oauth.OAuthSignatureMethod_HMAC_SHA1()
    req.set_parameter('oauth_signature_method', sign_method.get_name())
    log.debug('Signing base string %r for web request %s'
        % (sign_method.build_signature_base_string(req, consumer, token),
           url))
    req.sign_request(sign_method, consumer, token)

    return req.to_url()


def get_session_synchronization_url(self, callback_url=None):
    # oauth GET params for session synchronization
    # since the request comes from a script tag
    if not callback_url:
        params = {
            'callback_nonce': self.session.get('callback_nonce'),
            'callback_next': self.build_absolute_uri(),
        }
        callback_url = '%s?%s' % (self.build_absolute_uri(reverse('synchronize')), urlencode(params))

    current_token = self.session.get('oauth_token', None)
    if current_token:
        current_token = current_token.session_sync_token
    else:
        current_token = self.session.get('lost_session_sync_token', '')

    return gp_signed_url(self.oauth_client.session_sync_url,
                         { 'callback_url': callback_url, 'session_sync_token': current_token,
                           'target_object': self.group.id })


def get_oauth_identification_url(self, next):
    params = {
        'callback_nonce': self.session.get('callback_nonce'),
        'callback_next': self.build_absolute_uri(next),
        'signin': '1',
    }
    callback_url = '%s?%s' % (self.build_absolute_uri(reverse('synchronize')), urlencode(params))
    params = { 'callback_url': callback_url, 'target_object': self.group.id }
    params.update(settings.TYPEPAD_IDENTIFY_PARAMS)
    return gp_signed_url(self.oauth_client.oauth_identification_url, params)


class UserAgentMiddleware(object):

    def process_request(self, request):
        """For a logged-in user, adds an authed http object to
        the request. Otherwise, adds the app's own OAuth token.
        This middleware needs to be after the session middleware.
        """

        # static requests don't require auth
        if re.match('/?static/.*', request.path):
            return None

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
        self.app = None
        self.group = None

    def discover_group(self, request):
        log = logging.getLogger('.'.join((self.__module__, self.__class__.__name__)))

        # check for a cached app/group first
        app_key = 'application:%s' % settings.OAUTH_CONSUMER_KEY
        group_key = 'group:%s' % settings.OAUTH_CONSUMER_KEY

        # we cache in-process and in cache to support both situtations
        # where a cache is unavailable (cache is dummy), and situtations
        # where the application persistence is poor (Google App Engine)
        app = self.app or cache.get(app_key)
        group = self.group or cache.get(group_key)
        if app is None or group is None:
            log.info('Loading group info...')

            # Grab the group and app with the default credentials.
            consumer = oauth.OAuthConsumer(settings.OAUTH_CONSUMER_KEY,
                settings.OAUTH_CONSUMER_SECRET)
            token = oauth.OAuthToken(settings.OAUTH_GENERAL_PURPOSE_KEY,
                settings.OAUTH_GENERAL_PURPOSE_SECRET)
            backend = urlparse(settings.BACKEND_URL)
            typepad.client.clear_credentials()
            typepad.client.add_credentials(consumer, token, domain=backend[1])

            typepad.client.batch_request()
            try:
                api_key = typepad.ApiKey.get_by_api_key(
                    settings.OAUTH_CONSUMER_KEY)
                token = typepad.AuthToken.get_by_key_and_token(
                    settings.OAUTH_CONSUMER_KEY,
                    settings.OAUTH_GENERAL_PURPOSE_KEY)
                typepad.client.complete_batch()
            except Exception, exc:
                log.error('Error loading Application %s: %s' % (settings.OAUTH_CONSUMER_KEY, str(exc)))
                raise

            app = api_key.owner
            group = token.target

            log.info("Running for group: %s", group.display_name)

            cache.set(app_key, app, settings.LONG_TERM_CACHE_PERIOD)
            cache.set(group_key, group, settings.LONG_TERM_CACHE_PERIOD)

        if settings.SESSION_COOKIE_NAME is None:
            settings.SESSION_COOKIE_NAME = "sg_%s" % group.url_id

        self.app = app
        self.group = group

        return app, group

    def process_request(self, request):
        """Adds the application and group to the request."""

        if request.path.find('/static/') == 0:
            return None

        app, group = self.discover_group(request)

        typepadapp.models.APPLICATION = app
        typepadapp.models.GROUP = group

        request.application = app
        request.group = group

        return None


class AuthorizationExceptionMiddleware(object):
    """Middleware to catch authorization exceptions raised by the
    batchhttp library."""

    def __init__(self):
        # If we're not using batch requests, disable this middleware.
        if not settings.BATCH_REQUESTS:
            raise MiddlewareNotUsed

    def process_exception(self, request, exception):
        if not hasattr(request, 'typepad_user'):
            return
        if not request.typepad_user.is_authenticated():
            return
        if not isinstance(exception, NonBatchResponseError):
            return
        if exception.status not in (401, 403):
            return

        # Got a 4XX error. Log the user out (destroy session),
        # forget their OAuth token, and 302 them back to the 
        # current page as an anonymous user.

        from django.contrib.auth import logout
        from typepadapp.models import Token

        current_token = request.session.get('oauth_token', None)
        logout(request)
        if current_token is not None:
            try:
                token = Token.objects.get(key=current_token.key)
            except Token.DoesNotExist:
                pass
            else:
                token.delete()

        from django.http import HttpResponseRedirect
        return HttpResponseRedirect(request.build_absolute_uri())
