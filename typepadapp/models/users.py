# Copyright (c) 2009-2010 Six Apart Ltd.
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

import re
from urlparse import urljoin

from django.conf import settings
from django.db import models
from django.contrib.auth.models import SiteProfileNotAvailable, ImproperlyConfigured
from django.core.urlresolvers import reverse, NoReverseMatch
from django.utils.translation import ugettext_lazy as _
from django.core.cache import cache

import remoteobjects
import typepad
import typepadapp.models


class User(typepad.User):
    '''
        Mock Django User model using the TypePad API.
        The following methods override django.contrib.auth User.
    '''

    @property
    def username(self):
        return self.preferred_username

    @property
    def first_name(self):
        return self.display_name

    @property
    def last_name(self):
        return self.display_name

    @property
    def password(self):
        # not aware of password
        raise NotImplementedError

    @property
    def is_staff(self):
        return self.is_superuser or self.is_featured_member

    @property
    def is_active(self):
        return True

    @property
    def is_superuser(self):
        for admin in typepadapp.models.GROUP.admins():
            if self.id == admin.target.id:
                return True
        return False

    @property
    def is_featured_member(self):
        if settings.FEATURED_MEMBER is None: return False
        return settings.FEATURED_MEMBER in (self.xid,
            self.preferred_username)

    @property
    def date_joined(self):
        return None # does this need to be a datetime?

    @property
    def groups(self):
        #return self._groups
        raise NotImplementedError

    @property
    def can_post(self):
        if self.is_active and self.is_staff:
            return True
        return settings.ALLOW_COMMUNITY_POSTS

    @property
    def user_permissions(self):
        #return self._user_permissions
        raise NotImplementedError

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')

    def __unicode__(self):
        return self.username

    def get_absolute_url(self):
        """Relative url to the user's member profile page."""
        try:
            return reverse('member', args=[self.preferred_username or self.url_id])
        except NoReverseMatch:
            return None

    def is_anonymous(self):
        return False

    def is_authenticated(self):
        return True

    def get_full_name(self):
        return self.name

    def set_password(self, raw_password):
        raise NotImplementedError

    def check_password(self, raw_password):
        raise NotImplementedError

    def set_unusable_password(self):
        raise NotImplementedError

    def has_usable_password(self):
        raise NotImplementedError

    def get_group_permissions(self):
        raise NotImplementedError

    def get_all_permissions(self):
        raise NotImplementedError

    def has_perm(self, perm):
        raise NotImplementedError

    def has_perms(self, perm_list):
        raise NotImplementedError

    def has_module_perms(self, module):
        raise NotImplementedError

    def get_and_delete_messages(self):
        # required by django.core.context_processors
        return []

    def email_user(self, subject, message, from_email=None):
        "Sends an e-mail to this User."
        from django.core.mail import send_mail
        send_mail(subject, message, from_email, [self.email])

    # @cached_function
    def get_profile(self):
        """
        Returns site-specific profile for this user. Raises
        SiteProfileNotAvailable if this site does not allow profiles.
        """
        # user profile class from settings
        if not getattr(settings, 'AUTH_PROFILE_MODULE', False):
            raise SiteProfileNotAvailable
        try:
            app_label, model_name = settings.AUTH_PROFILE_MODULE.split('.')
            model = models.get_model(app_label, model_name)
        except (ImportError, ImproperlyConfigured):
            raise SiteProfileNotAvailable
        if model is None:
            error = 'Could not load configured profile model %s.models.%s' % (app_label, model_name)
            if app_label not in settings.INSTALLED_APPS:
                error = '%s. Is %r in INSTALLED_APPS?' % (error, app_label)
            raise ImproperlyConfigured(error)

        try:
            # get the model by user_id field (instead of a user foreign key field)
            profile = model._default_manager.get(user_id__exact=self.id)
        except model.DoesNotExist:
            # UserProfile for this site doesn't exist yet for this TypePad user
            profile = model()
            # user_id should be populated in case this profile is ever saved
            profile.user_id = self.id
        return profile

    def save(self):
        # does nothing yet
        # required by django.contrib.auth login
        pass

    def delete(self):
        # does nothing yet
        pass

    '''
        End Django User model properties and methods
    '''

    def group_events(self, group, start_index=1, max_results=None, **kwargs):
        if max_results is None:
            max_results = settings.EVENTS_PER_PAGE
        return self.events.filter(by_group=group, start_index=start_index,
            max_results=max_results, **kwargs)

    def group_memberships(self, group, **kwargs):
        return self.memberships.filter(by_group=group, **kwargs)

    def group_notifications(self, group, start_index=1, max_results=None, **kwargs):
        if max_results is None:
            max_results = settings.EVENTS_PER_PAGE
        return self.notifications.filter(by_group=group,
            start_index=start_index, max_results=max_results, **kwargs)

    def following(self, group=None, start_index=1, max_results=None, **kwargs):
        if max_results is None:
            max_results = settings.MEMBERS_PER_WIDGET
        if group is not None:
            return self.relationships.filter(following=True, by_group=group,
                start_index=start_index, max_results=max_results, **kwargs)
        return self.relationships.filter(following=True,
            start_index=start_index, max_results=max_results, **kwargs)

    def followers(self, group=None, start_index=1, max_results=None, **kwargs):
        if max_results is None:
            max_results = settings.MEMBERS_PER_WIDGET
        if group is not None:
            return self.relationships.filter(follower=True, by_group=group,
                start_index=start_index, max_results=max_results, **kwargs)
        return self.relationships.filter(follower=True,
            start_index=start_index, max_results=max_results, **kwargs)

    @property
    def edit_url(self):
        try:
            return reverse('edit_profile_url')
        except NoReverseMatch:
            return None

    @property
    def feed_url(self):
        """URL for atom feed of user's activity."""
        try:
            url = self.get_absolute_url().lstrip('/') # remove starting /
            return reverse('feeds', kwargs={'url': url})
        except NoReverseMatch:
            return None

    @property
    def typepad_url(self):
        import logging
        logging.getLogger("typepadapp.models.users").warn(
            'User.typepad_url is deprecated; use User.profile_page_url instead')
        return self.profile_page_url

    @property
    def typepad_edit_url(self):
        import logging
        logging.getLogger("typepadapp.models.users").warn(
            'User.typepad_edit_url is deprecated; use User.profile_edit_page_url instead')
        return self.profile_edit_page_url

    @property
    def typepad_frame_url(self):
        import logging
        logging.getLogger("typepadapp.models.users").warn(
            'User.typepad_frame_url is deprecated; use User.follow_frame_content_url instead')
        return self.follow_frame_content_url

    @property
    def userpic(self):
        """Returns a URL for a userpic for the User.

        The returned URL should be sized for a 50x50 square, but this
        cannot be guaranteed. The img tag should be styled in a way
        that bounds the presentation to 50 pixels square.

        """
        try:
            return self.avatar_link.square(50).url
        except AttributeError:
            pass
        try:
            return reverse('static-serve', kwargs={'path': settings.DEFAULT_USERPIC_PATH})
        except NoReverseMatch:
            pass
        return None


class UserProfile(typepad.UserProfile):

    @property
    def is_superuser(self):
        for admin in typepadapp.models.GROUP.admins():
            if self.id == admin.target.id:
                return True
        return False

    @property
    def is_featured_member(self):
        if settings.FEATURED_MEMBER is None: return False
        return settings.FEATURED_MEMBER in (self.id,
            self.preferred_username)

    @property
    def typepad_frame_url(self):
        import logging
        logging.getLogger("typepadapp.models.users").warn(
            'UserProfile.typepad_frame_url is deprecated; use UserProfile.follow_frame_content_url instead')
        return self.follow_frame_content_url


### Caching support

if settings.FRONTEND_CACHING:
    from typepadapp.caching import cache_link, cache_object, invalidate_rule
    from typepadapp import signals

    def make_user_alias_cache_key(self):
        """Attempts to use a caching key of the user's username, if available."""
        return "objectcache:%s:%s" % (self.cache_namespace, self.preferred_username or self.url_id)
    User.cache_key = property(make_user_alias_cache_key)
    UserProfile.cache_key = property(make_user_alias_cache_key)

    User.get_by_url_id = cache_object(User.get_by_url_id)
    user_invaldator = invalidate_rule(
        key=lambda sender, instance=None, group=None, **kwargs: instance,
        signals=[signals.member_banned, signals.member_unbanned],
        name="user cache invalidation for member_banned, member_unbanned signals")

    UserProfile.get_by_url_id = cache_object(UserProfile.get_by_url_id)
    user_profile_invaldator = invalidate_rule(
        key=lambda sender, instance=None, group=None, **kwargs: UserProfile.get_by_url_id(instance.preferred_username or instance.url_id),
        signals=[signals.member_banned, signals.member_unbanned],
        name="user profile cache invalidation for member_banned, member_unbanned signals")

    User.events = cache_link(User.events)
    user_events_invalidator = invalidate_rule(
        key=lambda sender, group=None, instance=None, **kwargs:
            instance and instance.author and group and [instance.author.notifications.filter(by_group=group),
                instance.author.preferred_username and User.get_by_url_id(instance.author.preferred_username).notifications.filter(by_group=group)],
        signals=[signals.asset_created, signals.asset_deleted],
        name="user notifications for group cache invalidation for asset_created, asset_deleted signals")

    User.notifications = cache_link(User.notifications)
    # signals.asset_created, signals.asset_deleted

    # We can't effectively signal to invalidate these lists because
    # follow/unfollow actions happen on typepad
    User.memberships = cache_link(User.memberships)
    user_memberships_invaldator = invalidate_rule(
        key=lambda sender, instance=None, group=None, **kwargs:
            instance and group and [instance.group_memberships(group),
                instance.preferred_username and User.get_by_url_id(instance.preferred_username).group_memberships(group)],
        signals=[signals.member_banned, signals.member_unbanned, signals.member_joined, signals.member_left],
        name="user membership invalidation for member_banned, member_unbanned, member_joined, member_left signals")

    User.elsewhere_accounts = cache_link(User.elsewhere_accounts)
    # signals.profile_webhook

    User.relationships = cache_link(User.relationships)
    # signals.following_webhook, signals.member_left, signals.member_joined

    # do these endpoints really work??
    # User.comments = cache_link(User.comments)
    # User.assets = cache_link(User.assets)

    User.favorites = cache_link(User.favorites)
    user_favorites_invalidator = invalidate_rule(
        key=lambda sender, instance=None, **kwargs: instance and [instance.author.favorites,
            instance.author.preferred_username and User.get_by_url_id(instance.author.preferred_username).favorites],
        signals=[signals.favorite_created, signals.favorite_deleted],
        name="user favorites stream for favorite created/deleted signals")
