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
