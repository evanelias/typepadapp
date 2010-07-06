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
import random
from string import ascii_letters, digits
import hashlib
from oauth import oauth
from urlparse import urlparse, urlunsplit

from optparse import make_option
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.core.urlresolvers import reverse

import typepad

from typepadapp.management.base import ExtendOption


class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option('-d', '--domain',
            action='store',
            help='The domain at which your site is available (if not configured in Sites)'),
        make_option('-n', '--name',
            action='store',
            dest='name',
            type='string',
            metavar='<name>',
            help='Updates the name used for this feed subscription'),
        ExtendOption('-r', '--remove',
            action='extend',
            dest='remove_feed',
            type='string',
            metavar='<feed>',
            help='One or more feeds to remove for this subscription'),
        ExtendOption('-a', '--add',
            action='extend',
            dest='add_feed',
            type='string',
            metavar='<feed>',
            help='One or more feeds to add for this subscription'),
        make_option('-u', '--unfilter',
            action='store_true',
            dest='unfilter',
            help='Specify to remove all filters for this subscription'),
        ExtendOption('-f', '--filter',
            action='extend',
            dest='filter',
            type='string',
            metavar='<filter>',
            help='One or more filters to apply for this subscription'),
        make_option('-p', '--post_as',
            action='store',
            dest='post_as',
            type='string',
            metavar='<user_id>',
            help='Updates the TypePad user used as the author for posts created from subscriptions'),
        )

    help = "Makes updates to an existing a feed subscription for your TypePad application."
    args = "<subscription_id>"

    def handle(self, sub_id, *args, **options):

        for setting in ('OAUTH_CONSUMER_KEY', 'OAUTH_CONSUMER_SECRET', 'OAUTH_GENERAL_PURPOSE_KEY',
            'OAUTH_GENERAL_PURPOSE_SECRET'):
            if not hasattr(settings, setting):
                raise CommandError("%s setting is required" % setting)

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
            group = True
        else:
            token = oauth.OAuthToken(settings.OAUTH_GENERAL_PURPOSE_KEY, settings.OAUTH_GENERAL_PURPOSE_SECRET)
            group = False
        backend = urlparse(typepad.client.endpoint)
        typepad.client.add_credentials(consumer, token, domain=backend[1])

        typepad.client.batch_request()
        sub = typepad.ExternalFeedSubscription.get_by_url_id(sub_id)
        typepad.client.complete_batch()

        from typepadapp.models.feedsub import Subscription
        if not group:
            # Create a new Subscription object; keep a record of the feeds and filters defined
            try:
                s = Subscription.objects.get(url_id=sub_id)
            except Subscription.DoesNotExist:
                raise CommandError("Could not find subscription %s in local table." % sub_id)

        # process updates based on switches; types of updates:

        # updating the name (local change only)
        if not group:
            if options['name'] is not None:
                s.name = options['name']
                s.save()
                print "Updated subscription name: %s" % s.name

        feed_list = set(s.feeds.split("\n"))
        # updating the feeds; adding a feed:
        if options['add_feed'] is not None:
            sub.add_feeds(feed_idents=options['add_feed'])
            for feed in options['add_feed']:
                feed_list.add(feed)
                print "Added feed: %s" % feed

        # updating the feeds; removing a feed:
        if options['remove_feed'] is not None:
            sub.remove_feeds(feed_idents=options['remove_feed'])
            for feed in options['remove_feed']:
                feed_list.discard(feed)
                print "Removed feed: %s" % feed

        if not group and (options['add_feed'] is not None or options['remove_feed'] is not None):
            s.feeds = "\n".join(feed_list)
            s.save()

        # updating the filters (replaces existing filter set)
        if options['filter'] is not None:
            filters = options['filter']
            sub.update_filters(filter_rules=filters)
            if not group:
                s.filters = "\n".join(filters)
                s.save()
            print "Assigned new filters to subscription: %s" % ", ".join(filters)

        # clearing the filters
        if options['unfilter']:
            sub.update_filters(filter_rules=[])
            if not group:
                s.filters = ""
                s.save()
            print "Cleared all existing filters for subscription."

        # update callback: for non-group based subscriptions
        if not group and options['domain']:
            domain = options['domain']
            callback_path = reverse('typepadapp.views.feedsub.callback', kwargs={'sub_id': str(s.id)})
            callback_url = urlunsplit(('http', domain, callback_path, '', ''))

            verify_token = ''.join(random.choice(ascii_letters+digits) for x in xrange(0,20))
            s.verify_token = verify_token
            s.verified = False
            s.save()

            sub.update_notification_settings(callback_url=callback_url, verify_token=verify_token)
            print "Assigned new callback URL: %s" % callback_url

        # update 'post-as-user' setting (for groups only)
        if group and options['post_as']:
            typepad.client.batch_request()
            author = typepad.User.get_by_url_id(options['post_as'])
            typepad.client.complete_batch()

            sub.update_user(post_as_user_id=options['post_as'])
            print "Updated author for subscription to %s (%s)" % (author.display_name, author.url_id)
