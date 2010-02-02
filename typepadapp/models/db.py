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
        typepad_id = models.CharField(max_length=50, unique=True)
        created = models.DateTimeField(auto_now_add=True)

        class Meta:
            app_label = 'typepadapp'
            db_table = 'typepadapp_usermap'
