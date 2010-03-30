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

import binascii
import hmac
import logging
import urllib

from urlparse import urlparse, urlunparse
from django import http
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse, NoReverseMatch
from oauth import oauth

from typepadapp.models import OAuthClient, Token
from typepadapp import signals


log = logging.getLogger('typepadapp.views.auth')


def parameterize_url(url, params):
    """
    Adds query string parameters to a URL that may already contain a query string.
    """
    url = list(urlparse(url))
    params = urllib.urlencode(params)
    if url[4]:
        url[4] = '%s&%s' % (url[4], params)
    else:
        url[4] = params
    return urlunparse(url)


def register(request):
    """ OAuth registration prep.
    
    Fetch request token then redirect to authorization page.
    """
    # fetch request token
    client = OAuthClient(request.application)

    # redirect to authorization url, next param specifies final redirect URL.
    callback = request.build_absolute_uri(reverse('authorize'))
    next = request.GET.get('next', HOME_URL)
    callback = parameterize_url(callback, {'next': next})

    token = client.fetch_request_token(callback)
    request.session['request_token'] = token.to_string()

    url = client.authorize_token({ 'target_object': request.group.id })

    return http.HttpResponseRedirect(url)


def login(request):
    """Redirect to the TypePad OAuth identification page, which 
    will redirect back to the synchronization URL after authenticating
    the user."""
    return http.HttpResponseRedirect(request.get_oauth_identification_url(request.GET.get('next', HOME_URL)))


def authorize(request):
    """ OAuth authorization.
    
    Exchange request token for an access token,
    login user and store token in user session.
    """
    # request token
    request_token = request.session.get('request_token', None)
    if not request_token:
        return http.HttpResponse("No un-authed token cookie")
    del request.session['request_token']

    # exchange request token for access token
    client = OAuthClient(request.application)
    client.set_token_from_string(request_token)
    verifier = request.GET.get('oauth_verifier')
    access_token = client.fetch_access_token(verifier=verifier)

    # authorize and login user
    from django.contrib.auth import authenticate, login
    authed_user = authenticate(oauth_client=client)
    login(request, authed_user)

    # store the token key / secret in the database so we can recover
    # it later if the session expires
    token, created = Token.objects.get_or_create(
        session_sync_token=request.GET['session_sync_token'],
        defaults={'key': access_token.key, 'secret': access_token.secret}
    )
    if created:
        # this is a new user or at least a new session sync token
        signals.member_joined.send(sender=authorize, instance=authed_user,
            group=request.group)
    else:
        # update token with current access token
        token.key = access_token.key
        token.secret = access_token.secret
        token.save()

    # oauth token in authed user session
    request.session['oauth_token'] = token

    # go to the welcome url, next url, or home.
    abs_home_url = request.build_absolute_uri(HOME_URL)
    next_url = request.GET.get('next', abs_home_url)
    if settings.WELCOME_URL is not None:
        if not next_url or next_url == abs_home_url:
            next_url = settings.WELCOME_URL
    return http.HttpResponseRedirect(next_url)


class StupidDataStore(oauth.OAuthDataStore):
    """A simple oauth.OAuthDataStore implementation for GP tokens.

    The oauth.OAuthServer class needs to be provided a data store
    from which it can lookup consumer and access token information.
    Since we have to verify the OAuth URI that is returned to us
    by TypePad, which is signed with our OAuth credentials, we need
    a simple data store that will only return our credentials, else
    raise an error.

    """

    def lookup_token(self, token_type, token):
        if token_type == 'access' and \
            token == settings.OAUTH_GENERAL_PURPOSE_KEY:
                return oauth.OAuthToken(settings.OAUTH_GENERAL_PURPOSE_KEY,
                                        settings.OAUTH_GENERAL_PURPOSE_SECRET)
        return None

    def lookup_consumer(self, key):
        if key == settings.OAUTH_CONSUMER_KEY:
            return oauth.OAuthConsumer(settings.OAUTH_CONSUMER_KEY,
                                       settings.OAUTH_CONSUMER_SECRET)
        return None

    def lookup_nonce(self, oauth_consumer, oauth_token, nonce, timestamp=None):
        return None


def synchronize(request):
    """Session synchronization.

    If a nonce is present, make sure it exists in the user's session and
    verify the signature. If successful, try to log the user in using the
    oauth token key specified in the query string.

    """
    from django.contrib.auth import authenticate, login, logout

    # check query string, then session for next param. default to index.
    next = request.GET.get('callback_next', HOME_URL)
    nonce = request.GET.get('callback_nonce')

    if not nonce:
        return http.HttpResponse('No nonce.')
    else:
        callback_nonce = request.session.get('callback_nonce')
        if callback_nonce is not None:
            # Delete the nonce to prevent replay attacks.
            del request.session['callback_nonce']

        session_sync_token = request.GET.get('session_sync_token')

        # log the user out / clear the existing session.
        logout(request)

        # Validate the request.
        if nonce != callback_nonce:
            # nonce's don't match, either a bug or someone's playing games
            return http.HttpResponseRedirect(next)

        oauth_request = oauth.OAuthRequest.from_request(request.method,
                                                        request.build_absolute_uri(),
                                                        parameters=dict(request.GET.items()),
                                                        query_string=request.environ.get('QUERY_STRING', ''))
        oauth_server = oauth.OAuthServer(StupidDataStore())
        oauth_server.add_signature_method(oauth.OAuthSignatureMethod_HMAC_SHA1())
        try:
            consumer, gp_token, params = oauth_server.verify_request(oauth_request)
        except oauth.OAuthError, ex:
            # OAuth signature is invalid. Something's fishy. Don't log them in.
            return http.HttpResponse(ex.message, status=400)

        # The register URL needs to retain the 'next' querystring param so we
        # can redirect to the correct place once registeration is complete.
        register_url = parameterize_url(reverse('register'), {'next': next})

        if session_sync_token:
            # If a token was returned, create a session loggin the user
            # in with the new token. Otherwise we just log the user out.
            try:
                token = Token.objects.get(session_sync_token=session_sync_token)
            except ObjectDoesNotExist:
                # We lost the token somehow.
                if request.GET.get('signin', False):
                    # They clicked sign in, but we don't have the token
                    # so we redirect to the register auth flow so we're issued
                    # a new token.
                    return http.HttpResponseRedirect(register_url)
                else:
                    # In this case we store the lost token in the user's session. In future
                    # session sync requests this "lost" token will be used instead of the
                    # logged in users' token for the `current_token` param. That way we don't 
                    # get stuck in a loop.
                    request.session['lost_session_sync_token'] = session_sync_token
                    return http.HttpResponseRedirect(next)
            client = OAuthClient(request.application)
            client.token = token

            # Everything's copasetic. Authorize and login user.
            authed_user = authenticate(oauth_client=client)
            login(request, authed_user)
            request.session['oauth_token'] = token
        else:
            if request.GET.get('signin', False):
                # If there's no token returned and the user clicked 'signin' then
                # they haven't auth'd this site to access their info. Send them
                # to register instead.
                return http.HttpResponseRedirect(register_url)

        return http.HttpResponseRedirect(next)


def logout(request):
    """Logout of Motion and TypePad."""
    from django.contrib.auth import logout
    logout(request)
    # redirect to logout of typepad
    url = request.application.signout_url
    url = parameterize_url(url, { 'callback_url':
        request.build_absolute_uri(HOME_URL) })
    return http.HttpResponseRedirect(url)


try:
    HOME_URL = reverse('home')
except NoReverseMatch:
    HOME_URL = '/'
    log.warning('Could not find a view "home"; using default: %s', HOME_URL)
except Exception, exc:
    log.error('Unexpected exception looking for "home" view: %s', str(exc))
else:
    log.debug('Successfully looked up HOME_URL: %s', HOME_URL)
