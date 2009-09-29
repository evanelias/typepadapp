# Copyright (c) 2009 Six Apart Ltd.
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
from types import MethodType
from urlparse import urlparse
from urllib import urlencode, quote

from django.conf import settings
from django.core.urlresolvers import reverse
from django.core.exceptions import MiddlewareNotUsed
from django.db import DatabaseError
from oauth import oauth

import typepad
from typepadapp.models.auth import OAuthClient
import typepadapp.models
from batchhttp.client import NonBatchResponseError


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
    return gp_signed_url(self.oauth_client.oauth_identification_url,
        { 'callback_url': callback_url, 'target_object': self.group.id })


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
        log = logging.getLogger('.'.join((self.__module__, self.__class__.__name__)))

        log.info('Loading group info...')
        app, group = None, None

        # Grab the group and app with the default credentials.
        consumer = oauth.OAuthConsumer(settings.OAUTH_CONSUMER_KEY, settings.OAUTH_CONSUMER_SECRET)
        token = oauth.OAuthToken(settings.OAUTH_GENERAL_PURPOSE_KEY, settings.OAUTH_GENERAL_PURPOSE_SECRET)
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

        typepad.client.batch_request()
        try:
            group.admin_list = group.memberships.filter(admin=True)
            typepad.client.complete_batch()
        except Exception, exc:
            log.error('Error loading Group %s: %s', group.id, str(exc))
            raise

        log.info("Running for group: %s", group.display_name)

        if settings.SESSION_COOKIE_NAME is None:
            settings.SESSION_COOKIE_NAME = "sg_%s" % group.url_id

        self.application = app
        self.group = group
        return app, group

    def process_request(self, request):
        """Adds the application and group to the request."""

        if self.application is None or self.group is None:
            self.discover_group(request)

        typepadapp.models.GROUP = self.group
        typepadapp.models.APPLICATION = self.application

        request.application = self.application
        request.group = self.group

        return None


class AuthorizationExceptionMiddleware(object):
    """Middleware to catch authorization exceptions raised by the
    batchhttp library."""

    def __init__(self):
        # If we're not using batch requests, disable this middleware.
        if not settings.BATCH_REQUESTS:
            raise MiddlewareNotUsed

    def process_exception(self, request, exception):
        if hasattr(request, 'user') and request.user.is_authenticated() and \
            isinstance(exception, NonBatchResponseError) and \
            exception.status in (401, 403):

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


class ConfigurationMiddleware(object):
    def __init__(self):
        # If we're not in debug mode, disable this middleware.
        if not settings.DEBUG:
            raise MiddlewareNotUsed

    def process_request(self, request):
        # If any of the OAUTH_* settings are empty, or don't exist, return the
        # "It worked!" page.
        try:
            if not (settings.OAUTH_CONSUMER_KEY and settings.OAUTH_CONSUMER_SECRET and
                    settings.OAUTH_GENERAL_PURPOSE_KEY and settings.OAUTH_GENERAL_PURPOSE_SECRET):
                return incomplete_configuration(request)
        except AttributeError:
            return incomplete_configuration(request)


# Incomplete configuration view.
def incomplete_configuration(request):
    from django.template import Template, Context
    from django.http import HttpResponse

    "Create an incomplete configuration error response."
    t = Template(CONFIGURATION_TEMPLATE, name='Incomplete configuration template')
    c = Context({
        'project_name': settings.SETTINGS_MODULE.split('.')[0]
    })
    return HttpResponse(t.render(c), mimetype='text/html')


CONFIGURATION_TEMPLATE = """
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:at="http://www.sixapart.com/ns/at" id="sixapart-standard">
<head>
  <style type="text/css">
    html * { padding:0; margin:0; }
    body * { padding:10px 20px; }
    body * * { padding:0; }
    body { font:small sans-serif; }
    body>div { border-bottom:1px solid #ddd; }
    h1 { font-weight:normal; }
    h2 { margin-bottom:.8em; }
    h2 span { font-size:80%; color:#666; font-weight:normal; }
    h3 { margin:1em 0 .5em 0; }
    h4 { margin:0 0 .5em 0; font-weight: normal; }
    table { border:1px solid #ccc; border-collapse: collapse; width:100%; background:white; }
    tbody td, tbody th { vertical-align:top; padding:2px 3px; }
    thead th { padding:1px 6px 1px 3px; background:#fefefe; text-align:left; font-weight:normal; font-size:11px; border:1px solid #ddd; }
    tbody th { width:12em; text-align:right; color:#666; padding-right:.5em; }
    ul { margin-left: 2em; margin-top: 1em; }
    #summary { background: #e0ebff; }
    #summary h2 { font-weight: normal; color: #666; }
    #explanation { background:#eee; }
    #instructions { background:#f6f6f6; }
    #summary table { border:none; background:transparent; }
  </style>
</head>

<body>
<div id="summary">
  <h1>It worked!</h1>
  <h2>Congratulations on your new TypePad-powered website.</h2>
</div>

<div id="instructions">
  <p>Of course, you haven't actually done any work yet. Here's what to do next:</p>
  <ul>
    <li>Register your application on TypePad at <a href="#">[some url should go here]</a>, and get an application key and general purpose token.</li>
    <li>Edit the <code>OAUTH_*</code> settings in <code>{{ project_name }}/local_settings.py</code> to use your application's credentials.</li>
    <li>If you plan on using a database other than sqlite, edit the <code>DATABASE_*</code> settings in <code>{{ project_name }}/local_settings.py</code>.</li>
    <li>Create new TypePad apps to customize your site by running <code>python {{ project_name }}/manage.py typepadapp [appname]</code>.</li>
    <li>Initialize your database by running <code>python {{ project_name }}/manage.py syncdb</code>.</li>
    <li>Launch your site by running <code>python {{ project_name }}/manage.py runserver</code>.</li>
  </ul>
</div>

<div id="explanation">
  <p>
    You're seeing this message because you have <code>DEBUG = True</code> in your
    Django settings file and you haven't finished configuring this installation.
    Get to work!
  </p>
</div>
</body>
</html>
"""
