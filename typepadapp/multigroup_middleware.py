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
import re
import logging
import typepad
from urlparse import urlparse
from urllib import urlencode, quote
from oauth import oauth
from django.conf import settings


class GroupSettings(object):
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
        return dir(self) + self.real_settings.get_all_members() + self.group_settings.keys()


class MultiGroupMiddleware(object):

    def __init__(self):
        settings._wrapped = GroupSettings(settings._wrapped)

    def load_group_settings(self, host):

        from django.core.cache import cache

        settings_for_host = cache.get('settings_by_host:%s' % host)

        if settings_for_host is None:
            host_dir = os.path.join(settings.ROOT_DIR, 'groups', host)
            if os.path.isdir(host_dir):
                settings_file = os.path.join(host_dir, 'settings.py')
                if os.path.exists(settings_file):
                    import imp
                    fp = file(settings_file, 'r')
                    try:
                        mod = imp.load_module('%s group settings' % host, fp, settings_file, ("py", "r", imp.PY_SOURCE))
                        settings_for_host = {}
                        for setting in dir(mod):
                            if setting == setting.upper():
                                settings_for_host[setting] = getattr(mod, setting)
                    finally:
                        if fp:
                            fp.close()
                cache.set('settings_by_host:%s' % host, settings_for_host)

        if settings_for_host is None:
            settings_for_host = {}

        return settings_for_host

    def discover_group(self, request):

        log = logging.getLogger('.'.join((self.__module__, self.__class__.__name__)))

        # normalize hostname for mapping host to settings
        # remove the common 'www' subdomain and any port #s
        host = request.META['HTTP_HOST'].lower()
        host = re.sub(r'^www\.', '', host)
        host = re.sub(r':\d+$', '', host)

        app_key = 'app_by_host:%s' % host
        group_key = 'group_by_host:%s' % host

        from django.core.cache import cache

        app = cache.get(app_key)
        group = cache.get(group_key)

        if settings.group_host != host:
            group_settings = self.load_group_settings(host)
            # update groupsettingsholder to use these group settings
            settings.group_host = host
            settings.group_settings = group_settings

        if typepad.client.endpoint != settings.BACKEND_URL:
            typepad.client.endpoint = settings.BACKEND_URL

        if app and group: return app, group

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

            if group is None or not len(group.admin_list):
                typepad.client.batch_request()
                try:
                    group.admin_list = group.memberships.filter(admin=True)
                    typepad.client.complete_batch()
                except Exception, exc:
                    log.error('Error loading Group %s: %s', group.id, str(exc))
                    raise

            cache.set(app_key, app)
            cache.set(group_key, group)

        log.info("Running for group: %s", group.display_name)

        if settings.SESSION_COOKIE_NAME is None:
            settings.SESSION_COOKIE_NAME = "sg_%s" % group.url_id

        return app, group

    def process_request(self, request):
        """Adds the application and group to the request."""

        # static requests don't require auth
        if re.match('/?static/.*', request.path):
            return None

        app, group = self.discover_group(request)

        import typepadapp.models
        typepadapp.models.GROUP = group

        request.application = app
        request.group = group

        return None
