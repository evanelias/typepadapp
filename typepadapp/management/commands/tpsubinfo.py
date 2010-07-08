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
from urlparse import urlparse

from optparse import make_option
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

import typepad


class Command(BaseCommand):

    help = "Provides information about an individual feed subscription."
    args = "[<subscription_id> [...]]"

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
            token = oauth.OAuthToken(settings.OAUTH_SUPERUSER_KEY, settings.OAUTH_SUPERUSER_SECRET)
        else:
            token = oauth.OAuthToken(settings.OAUTH_GENERAL_PURPOSE_KEY, settings.OAUTH_GENERAL_PURPOSE_SECRET)
        backend = urlparse(typepad.client.endpoint)
        typepad.client.add_credentials(consumer, token, domain=backend[1])

        if len(args) == 0:
            return self.list()

        for sub_id in args:
            typepad.client.batch_request()
            subscription = typepad.ExternalFeedSubscription.get_by_url_id(sub_id)
            feeds = subscription.feeds
            try:
                typepad.client.complete_batch()
            except typepad.ExternalFeedSubscription.NotFound:
                print "No such subscription %s" % sub_id
                continue

            print "Subscription Id: %s" % subscription.url_id
            if not hasattr(settings, 'GROUP_ID'):
                print "Callback URL: %s (%s)" % (subscription.callback_url, subscription.callback_status)
            print "Feeds:"
            for feed in feeds:
                print "\t%s" % feed
            if len(subscription.filter_rules) > 0:
                print "Filter rules:"
                for filter in subscription.filter_rules:
                    print "\t%s" % filter
            if subscription.post_as_user_id:
                print "Post as User: %s" % ''.join(subscription.post_as_user_id)

    def list(self):

        group = None
        app = None
        subs = None
        if hasattr(settings, 'GROUP_ID'):
            typepad.client.batch_request()
            group = typepad.Group.get_by_url_id(settings.GROUP_ID)
            subs = group.external_feed_subscriptions
            typepad.client.complete_batch()
        elif hasattr(settings, 'APPLICATION_ID'):
            typepad.client.batch_request()
            app = typepad.Application.get_by_id(settings.APPLICATION_ID)
            subs = app.external_feed_subscriptions
            typepad.client.complete_batch()
        else:
            raise CommandError("Your settings module must have either an APPLICATION_ID or GROUP_ID setting")

        print "Subscriptions:"
        from typepadapp.models.feedsub import Subscription
        for sub in subs:
            try:
                sub_model = Subscription.objects.get(url_id=sub.url_id)
                verified = (sub_model.verified and "verified") or "unverified"
                print "\t%s (%s) %s" % (sub_model, sub.url_id, verified)
            except Subscription.DoesNotExist:
                print "\t%s (no local record)" % sub.url_id

