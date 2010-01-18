"""
MultiGroupMiddleware
    determines group appropriate for the request
    looks at domain
    loads settings from group-specific settings file
    loads app, group if not already cached
    sets gp credentials for this group
    populates request.urlconf if there are group specific urls
        request.urlconf can provide a different set of urlconfs per request
    populates group specific settings
"""

import os
import sys
import threading
import re
import logging
import typepad
from urlparse import urlparse
from urllib import urlencode, quote
from oauth import oauth

from django.conf import settings
import django.core.urlresolvers
from django.core.cache import cache


log = logging.getLogger('typepadapp.middleware.group')


class SingleGroupMiddleware(object):

    app = None
    group = None

    def __init__(self):
        pass

    def discover_group(self, request):
        log = logging.getLogger('.'.join((self.__module__, self.__class__.__name__)))

        # check for a cached app/group first
        app_key = 'application:%s' % settings.OAUTH_CONSUMER_KEY
        group_key = 'group:%s' % settings.OAUTH_CONSUMER_KEY

        # we cache in-process and in cache to support both situtations
        # where a cache is unavailable (cache is dummy), and situtations
        # where the application persistence is poor (Google App Engine)
        app = self.app or cache.get(app_key)
        group = self.group or cache.get(group_key)
        if app is None or group is None:
            log.info('Loading group info...')

            # Grab the group and app with the default credentials.
            consumer = oauth.OAuthConsumer(settings.OAUTH_CONSUMER_KEY,
                settings.OAUTH_CONSUMER_SECRET)
            token = oauth.OAuthToken(settings.OAUTH_GENERAL_PURPOSE_KEY,
                settings.OAUTH_GENERAL_PURPOSE_SECRET)
            backend = urlparse(settings.BACKEND_URL)
            typepad.client.clear_credentials()
            typepad.client.add_credentials(consumer, token, domain=backend[1])

            typepad.client.batch_request()
            try:
                api_key = typepad.ApiKey.get_by_api_key(
                    settings.OAUTH_CONSUMER_KEY)
                token = typepad.AuthToken.get_by_key_and_token(
                    settings.OAUTH_CONSUMER_KEY,
                    settings.OAUTH_GENERAL_PURPOSE_KEY)
                typepad.client.complete_batch()
            except Exception, exc:
                log.error('Error loading Application %s: %s' % (settings.OAUTH_CONSUMER_KEY, str(exc)))
                raise

            app = api_key.owner
            group = token.target

            log.info("Running for group: %s", group.display_name)

            cache.set(app_key, app, settings.LONG_TERM_CACHE_PERIOD)
            cache.set(group_key, group, settings.LONG_TERM_CACHE_PERIOD)

        if settings.SESSION_COOKIE_NAME is None:
            settings.SESSION_COOKIE_NAME = "sg_%s" % group.url_id

        self.app = app
        self.group = group

        return app, group

    def process_request(self, request):
        """Adds the application and group to the request."""

        if request.path.find('/static/') == 0:
            return None

        app, group = self.discover_group(request)

        request.application = app
        request.group = group

        return None


class GroupSettings(threading.local):
    """
    Holder for user configured settings.
    """
    # SETTINGS_MODULE doesn't make much sense in the manually configured
    # (standalone) case.
    SETTINGS_MODULE = None

    def __init__(self, real_settings):
        """
        Requests for configuration variables not in this class are satisfied
        from the module specified in default_settings (if possible).
        """
        self.real_settings = real_settings
        self.group_settings = {}
        self.group_host = ''

    def __getattr__(self, name):
        if name in self.group_settings:
            return self.group_settings[name]
        return getattr(self.real_settings, name)

    def get_all_members(self):
        return dir(self) + self.real_settings.get_all_members() \
            + self.group_settings.keys()


class MultiGroupMiddleware(object):

    def __init__(self):
        settings._wrapped = GroupSettings(settings._wrapped)

    def load_group_settings(self, host):

        settings_for_host = cache.get('settings_by_host:%s' % host)

        if settings_for_host is None:
            if hasattr(settings, 'APP_FOR_HOST'):
                app = settings.APP_FOR_HOST.get(host, None)
                if app is not None:
                    mod = app + '.settings'
                    if mod in sys.modules:
                        mod = sys.modules[mod]
                    else:
                        mod = __import__(mod).settings

                    settings_for_host = {}
                    for setting in dir(mod):
                        if setting == setting.upper():
                            settings_for_host[setting] = getattr(mod, setting)

                    cache.set('settings_by_host:%s' % host, settings_for_host)

        return settings_for_host or {}

    def discover_group(self, request):

        # normalize hostname for mapping host to settings
        # remove the common 'www' subdomain and any port #s
        host = request.get_host()
        host = re.sub(r'^www\.', '', host)
        host = re.sub(r':\d+$', '', host)

        app_key = 'app_by_host:%s' % host
        group_key = 'group_by_host:%s' % host

        app = cache.get(app_key)
        group = cache.get(group_key)

        if settings.group_host != host:
            group_settings = self.load_group_settings(host)
            # update groupsettingsholder to use these group settings
            settings.group_host = host
            settings.group_settings = group_settings

        if typepad.client.endpoint != settings.BACKEND_URL:
            typepad.client.endpoint = settings.BACKEND_URL

        if app and group:
            return app, group

        log.info('Loading group info for host %s...' % host)

        if app is None or group is None:
            # Grab the group and app with the default credentials.
            consumer = oauth.OAuthConsumer(settings.OAUTH_CONSUMER_KEY,
                settings.OAUTH_CONSUMER_SECRET)
            token = oauth.OAuthToken(settings.OAUTH_GENERAL_PURPOSE_KEY,
                settings.OAUTH_GENERAL_PURPOSE_SECRET)
            backend = urlparse(settings.BACKEND_URL)
            typepad.client.clear_credentials()
            typepad.client.add_credentials(consumer, token, domain=backend[1])

            typepad.client.batch_request()
            try:
                api_key = typepad.ApiKey.get_by_api_key(
                    settings.OAUTH_CONSUMER_KEY)
                token = typepad.AuthToken.get_by_key_and_token(
                    settings.OAUTH_CONSUMER_KEY,
                    settings.OAUTH_GENERAL_PURPOSE_KEY)
                typepad.client.complete_batch()
            except Exception, exc:
                log.error('Error loading Application %s: %s' % (settings.OAUTH_CONSUMER_KEY, str(exc)))
                raise

            app = api_key.owner
            if group is None:
                group = token.target

            cache.set(app_key, app, settings.LONG_TERM_CACHE_PERIOD)
            cache.set(group_key, group, settings.LONG_TERM_CACHE_PERIOD)

        log.info("Running for group: %s", group.display_name)

        if settings.SESSION_COOKIE_NAME is None:
            settings.SESSION_COOKIE_NAME = "sg_%s" % group.url_id

        return app, group

    def process_request(self, request):
        """Adds the application and group to the request."""

        # clear resolver cache just so we don't reverse a url to the
        # wrong thing or run the wrong view
        django.core.urlresolvers.clear_url_caches()

        app, group = self.discover_group(request)

        request.urlconf = settings.ROOT_URLCONF

        request.application = app
        request.group = group

        return None
