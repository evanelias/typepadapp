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
from typepadapp.utils.cached import cached_function

USER_CACHE_PERIOD = 0

class User(typepad.User):
    '''
        Mock Django User model using the TypePad API.
        The following methods override django.contrib.auth User.
    '''

    if USER_CACHE_PERIOD:
        # Django-level caching of user objects
        @classmethod
        def get_by_url_id(cls, url_id):
            user = cache.get('user:%s' % url_id)
            if user is None:
                user = super(User, cls).get_by_url_id(url_id)
            else:
                loc = user['location']
                data = user['data']
                user = cls.from_dict(data)
                user._location = loc
                user._delivered = True
            return user

        def update_from_dict(self, data):
            super(User, self).update_from_dict(data)
            if hasattr(self, '_location') and self._location is not None:
                user = { 'data': self._originaldata, 'location': self._location }
                cache.set('user:%s' % self.url_id, user, USER_CACHE_PERIOD)
                if self.username is not None:
                    cache.set('user:%s' % self.username, user, USER_CACHE_PERIOD)
            return self

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
        return self.is_superuser

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

    @cached_function
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

    assets = typepad.fields.Link(typepad.ListOf('Asset'))

    def group_events(self, group, start_index=1, max_results=settings.EVENTS_PER_PAGE):
        return self.events.filter(by_group=group, start_index=start_index, max_results=max_results)

    def group_assets(self, group, start_index=1, max_results=settings.EVENTS_PER_PAGE, type=None):
        args = {
            'by_group': group,
            'start_index': start_index,
            'max_results': max_results,
        }
        if type is not None:
            args[type] = True
        return self.assets.filter(**args)

    def group_comments(self, group, start_index=1, max_results=settings.COMMENTS_PER_PAGE):
        return self.comments.filter(by_group=group, start_index=start_index, max_results=max_results)

    def group_notifications(self, group, start_index=1, max_results=settings.EVENTS_PER_PAGE):
        return self.notifications.filter(by_group=group, start_index=start_index, max_results=max_results)

    def following(self, group=None, start_index=1, max_results=settings.MEMBERS_PER_WIDGET):
        return self.relationships.filter(following=True, by_group=group, start_index=start_index, max_results=max_results)

    def followers(self, group=None, start_index=1, max_results=settings.MEMBERS_PER_WIDGET):
        return self.relationships.filter(follower=True, by_group=group, start_index=start_index, max_results=max_results)
    
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
        try:
            return self.links['alternate'].href
        except (TypeError, KeyError):
            # fail silently?
            return None
    
    @property
    def typepad_edit_url(self):
        try:
            return self.links['profile-edit-page'].href
        except (TypeError, KeyError):
            # fail silently?
            return None
    
    @property
    def typepad_membership_management_url(self):
        try:
            return self.links['membership-management-page'].href
        except (TypeError, KeyError):
            # fail silently?
            return None
    
    @property
    def typepad_frame_url(self):
        return self.links['follow-frame-content'].href

    @property
    def userpic(self):
        try:
            return self.links['rel__avatar']['width__50'].href
        except (TypeError, KeyError):
            pass
        try:
            return reverse('static-serve', kwargs={'path': settings.DEFAULT_USERPIC_PATH})
        except NoReverseMatch:
            pass
        return None
