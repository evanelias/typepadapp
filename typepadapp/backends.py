import logging
from urlparse import urlparse

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
import httplib2

import typepad
from typepadapp.models import User


class TypePadBackend(object):
    """Custom User authentication backend for
    authenticating against the TypePad API.
    """

    def authenticate(self, oauth_client):
        """Verify authentication by calling get_self on the User.

        This will verify against the API endpoint for returning
        the authenticated user.
        """
        http = typepad.client
        http.clear_credentials()

        backend = urlparse(settings.BACKEND_URL)
        http.add_credentials(oauth_client.consumer, oauth_client.token,
            domain=backend[1])

        typepad.client.batch_request()
        u = User.get_self(http=http)
        try:
            typepad.client.complete_batch()
        except (User.Unauthorized, User.Forbidden):
            u = AnonymousUser()

        return u

    def get_user(self, user_id):
        """Return the authed TypePad user"""
        return User.get_by_id(user_id)
