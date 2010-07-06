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

from django.db import models
from django.core.exceptions import ObjectDoesNotExist

import urllib
from oauth import oauth


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

    @classmethod
    def get(cls, key):
        try:
            return cls.objects.get(session_sync_token=key)
        except ObjectDoesNotExist:
            return None

    class Meta:
        app_label = 'typepadapp'
        db_table = 'typepadapp_token'


user_model = models.get_model('auth', 'User')
if user_model and user_model._meta.installed:

    class UserForTypePadUser(models.Model):
        user = models.ForeignKey('auth.User', related_name='typepad_map', unique=True)
        typepad_id = models.CharField(max_length=50, unique=True, verbose_name='TypePad ID')
        created = models.DateTimeField(auto_now_add=True)

        class Meta:
            app_label = 'typepadapp'
            db_table = 'typepadapp_usermap'
            verbose_name = 'user for TypePad user'
            verbose_name_plural = 'users for TypePad users'


class Subscription(models.Model):
    """Model for holding a local reference to a TypePad feed subscription.

    """
    name = models.CharField(max_length=200)
    url_id = models.CharField(max_length=200, verbose_name='URL ID')
    feeds = models.TextField(help_text='The feed identifiers associated with this subscription, one per line')
    filters = models.TextField(blank=True, help_text='The filters associated with this subscription, one per line')
    secret = models.CharField(max_length=200, blank=True)
    verified = models.BooleanField(help_text='Whether TypePad verified this subscription yet')
    verify_token = models.CharField(max_length=200)

    def __str__(self):
        return self.name or self.url_id

    def __unicode__(self):
        return self.name or self.url_id

    class Meta:
        app_label = 'typepadapp'
        db_table = 'typepadapp_subscription'
