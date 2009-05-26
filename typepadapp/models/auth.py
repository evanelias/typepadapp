import logging
import urllib

from django.conf import settings
from django.db import models

import typepad
import typepadapp.models


class OAuthClient(typepad.OAuthClient):

    def __init__(self, app):
        self.set_consumer(settings.OAUTH_CONSUMER_KEY, secret = settings.OAUTH_CONSUMER_SECRET,)
        self.callback_url = settings.OAUTH_CALLBACK_URL

        self.request_token_url = app.oauth_request_token
        self.access_token_url = app.oauth_access_token_endpoint
        self.authorization_url = app.oauth_authorization_page
        self.session_sync_url = app.session_sync_script
        self.oauth_identification_url = app.oauth_identification_page


class Token(models.Model):
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
