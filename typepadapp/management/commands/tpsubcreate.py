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

import logging
from optparse import make_option
import os
import random
from string import ascii_letters, digits
import sys
from urlparse import urlparse, urlunsplit

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand, CommandError
from django.core.urlresolvers import reverse
from oauth import oauth
import typepad

from typepadapp.management.base import ExtendOption


class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option('-d', '--domain',
            action='store',
            help='The domain at which your site is available (if not configured in Sites)'),
        make_option('--secret',
            action='store_true',
            help='If provided, subscribe using a secret and Authenticated Content Distribution'),
        make_option('-n', '--name',
            action='store',
            dest='name',
            type='string',
            metavar='<name>',
            help='The name to use for this feed subscription'),
        make_option('-p', '--post-as',
            action='store',
            dest='post_as_user_id',
            type='string',
            metavar='<user_id>',
            help='A TypePad user id to use for the author of posts created with group subscriptions (defaults to developer of this application)'),
        ExtendOption('-f', '--filter',
            action='extend',
            dest='filter',
            type='string',
            metavar='<filter>',
            help='One or more filters to apply for this subscription'),
        )

    help = "Creates a feed subscription for your TypePad application."
    args = "<feedurl> [...]"

    def handle(self, *feed_idents, **options):

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

        if len(feed_idents) == 0:
            raise CommandError("At least one feed URL parameter is required")

        filters = options['filter'] or []

        # Setup for OAuth authentication
        consumer = oauth.OAuthConsumer(settings.OAUTH_CONSUMER_KEY, settings.OAUTH_CONSUMER_SECRET)
        token = oauth.OAuthToken(settings.OAUTH_GENERAL_PURPOSE_KEY, settings.OAUTH_GENERAL_PURPOSE_SECRET)
        backend = urlparse(typepad.client.endpoint)
        typepad.client.add_credentials(consumer, token, domain=backend[1])

        group = None
        if hasattr(settings, 'GROUP_ID'):
            typepad.client.batch_request()
            group = typepad.Group.get_by_url_id(settings.GROUP_ID)
            typepad.client.complete_batch()

        if group:
            for setting in ('OAUTH_SUPERUSER_KEY', 'OAUTH_SUPERUSER_SECRET'):
                if not hasattr(settings, setting):
                    raise CommandError("%s setting is required" % setting)

            token = oauth.OAuthToken(settings.OAUTH_SUPERUSER_KEY, settings.OAUTH_SUPERUSER_SECRET)
            typepad.client.clear_credentials()
            typepad.client.add_credentials(consumer, token, domain=backend[1])

            if options['post_as_user_id'] is not None:
                post_user = options['post_as_user_id']
            else:
                typepad.client.batch_request()
                u = typepad.User.get_self()
                typepad.client.complete_batch()
                post_user = u.url_id

            try:
                group.create_external_feed_subscription(
                    feed_idents=feed_idents,
                    filter_rules=filters,
                    post_as_user_id=post_user,
                )
            except Exception, exc:
                logging.getLogger(__name__).exception(exc)
        else:
            domain = options['domain']
            if not domain:
                current_site = Site.objects.get_current()
                domain = current_site.domain
                if domain == 'example.com':
                    raise CommandError("No --domain parameter was given, and your Django 'sites' have not been configured")

            name = options['name']
            if not name:
                raise CommandError("A -n <name> parameter is required")

            if options['secret']:
                secret = ''.join(random.choice(ascii_letters+digits) for x in xrange(0,20))
            else:
                secret = None

            # generate a verification token
            verify_token = ''.join(random.choice(ascii_letters+digits) for x in xrange(0,20))

            # Create a new Subscription object; keep a record of the feeds and filters defined
            from typepadapp.models.feedsub import Subscription
            s = Subscription()
            s.verify_token = verify_token
            s.verified = False
            s.name = options.get('name')
            if secret is not None:
                s.secret = secret
            s.feeds = "\n".join(feed_idents)
            s.filters = "\n".join(filters)
            s.save()

            try:
                callback_path = reverse('typepadapp.views.feedsub.callback', kwargs={'sub_id': str(s.id)})
                callback_url = urlunsplit(('http', domain, callback_path, '', ''))

                application = typepad.Application.get_by_id(settings.APPLICATION_ID)
                resp = application.create_external_feed_subscription(
                    callback_url=callback_url,
                    feed_idents=feed_idents,
                    filter_rules=filters,
                    secret=secret,
                    verify_token=verify_token)
            except Exception, exc:
                resp = None
                logging.getLogger(__name__).exception(exc)

            if resp:
                # Meanwhile TypePad hit our callback, so reload the object to
                # preserve the new "verified" value.
                s = Subscription.objects.get(verify_token=verify_token)
                s.url_id = resp.subscription.url_id
                s.save()
                print "Created subscription %s." % s.url_id
            else:
                s.delete()
                print "Subscription failed."
