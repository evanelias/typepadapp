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
import urllib

from django.conf import settings
from django.db import models

import typepad
import typepadapp.models
from oauth import oauth


class OAuthClient(typepad.OAuthClient):

    def __init__(self, app):
        self.set_consumer(settings.OAUTH_CONSUMER_KEY, secret = settings.OAUTH_CONSUMER_SECRET,)

        self.request_token_url = app.oauth_request_token_url
        self.access_token_url = app.oauth_access_token_url
        self.authorization_url = app.oauth_authorization_url
        self.session_sync_url = app.session_sync_script_url
        self.oauth_identification_url = app.oauth_identification_url


class Token(models.Model, oauth.OAuthToken):
    """ Local database storage for user
        OAuth tokens.
    """
    session_sync_token = models.CharField(max_length=32, unique=True)
    key = models.CharField(max_length=32, unique=True)
    secret = models.CharField(max_length=32)

    def __unicode__(self):
        return self.key

    def to_string(self, only_key=False):
        # so this can be used in place of an oauth.OAuthToken
        if only_key:
            return urllib.urlencode({'oauth_token': self.key})
        return urllib.urlencode({'oauth_token': self.key, 'oauth_token_secret': self.secret})
        
    class Meta:
        app_label = 'typepadapp'
        db_table = 'typepadapp_token'
