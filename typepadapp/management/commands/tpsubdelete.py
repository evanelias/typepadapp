# Copyright (c) 2010 Six Apart Ltd.
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

import os
import sys
import hashlib
from oauth import oauth

from optparse import make_option
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

import typepad


class Command(BaseCommand):

    help = "Deletes a TypePad external feed subscription."
    args = "<subscription_id> [...]"

    def handle(self, *args, **kwargs):

        for setting in ('OAUTH_CONSUMER_KEY', 'OAUTH_CONSUMER_SECRET', 'OAUTH_GENERAL_PURPOSE_KEY',
            'OAUTH_GENERAL_PURPOSE_SECRET'):
            if not hasattr(settings, setting):
                raise CommandError("%s setting is undefined" % setting)

        try:
            typepad.client.endpoint = settings.BACKEND_URL
        except AttributeError:
            typepad.client.endpoint = 'https://api.typepad.com'

        # apply any TYPEPAD_COOKIES declared
        try:
            typepad.client.cookies.update(settings.TYPEPAD_COOKIES)
        except AttributeError:
            pass

        # Setup for OAuth authentication
        consumer = oauth.OAuthConsumer(settings.OAUTH_CONSUMER_KEY, settings.OAUTH_CONSUMER_SECRET)
        if hasattr(settings, 'GROUP_ID'):
            for setting in ('OAUTH_SUPERUSER_KEY', 'OAUTH_SUPERUSER_SECRET'):
                if not hasattr(settings, setting):
                    raise CommandError("%s setting is required" % setting)

            token = oauth.OAuthToken(settings.OAUTH_SUPERUSER_KEY, settings.OAUTH_SUPERUSER_SECRET)
        else:
            token = oauth.OAuthToken(settings.OAUTH_GENERAL_PURPOSE_KEY, settings.OAUTH_GENERAL_PURPOSE_SECRET)
        typepad.client.add_credentials(consumer, token)

        # TBD: offer some kind of confirmation??

        for sub_id in args:
            typepad.client.batch_request()
            subscription = typepad.ExternalFeedSubscription.get_by_url_id(sub_id).delete()
            typepad.client.complete_batch()

            from typepadapp.models.feedsub import Subscription
            try:
                s = Subscription.objects.get(url_id=sub_id)
                s.delete()
            except Subscription.DoesNotExist:
                pass
