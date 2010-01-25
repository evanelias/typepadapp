from django_kvstore import models

import urllib
from oauth import oauth


class Token(models.Model, oauth.OAuthToken):
    """ Local database storage for user
        OAuth tokens.
    """
    session_sync_token = models.Field(pk=True)
    key = models.Field()
    secret = models.Field()

    def __unicode__(self):
        return self.key

    def to_string(self, only_key=False):
        # so this can be used in place of an oauth.OAuthToken
        if only_key:
            return urllib.urlencode({'oauth_token': self.key})
        return urllib.urlencode({'oauth_token': self.key, 'oauth_token_secret': self.secret})
