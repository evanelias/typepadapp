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

from django.core.urlresolvers import reverse, NoReverseMatch
from django.utils.translation import ugettext as _
from django.conf import settings

from remoteobjects import fields, RemoteObject

import typepad
from typepad.tpobject import ListObject

from typepadapp import signals
import typepadapp.models


class ListObjectSignalDispatcher(object):
    """
    Override the post method of ListObject so we can signal when
    an asset is created.

    """
    def post(self, obj, *args, **kwargs):
        super(ListObjectSignalDispatcher, self).post(obj, *args, **kwargs)
        signals.post_save.send(sender=self.__class__, instance=obj)
ListObject.__bases__ = (ListObjectSignalDispatcher,) + ListObject.__bases__


# Additional methods for all asset models:
class Asset(typepad.Asset):

    def __unicode__(self):
        return self.title or self.content

    def __str__(self):
        return self.__unicode__()

    def get_absolute_url(self):
        """Relative url to the asset permalink page."""
        if self.is_local:
            try:
                return reverse('asset', args=[self.url_id])
            except NoReverseMatch:
                pass

        return self.permalink_url

    @property
    def feed_url(self):
        """URL for atom feed of entry comments."""
        try:
            url = self.get_absolute_url()[1:] # remove starting /
            return reverse('feeds', kwargs={'url': url})
        except NoReverseMatch:
            return None

    @property
    def type_id(self):
        object_type = self.primary_object_type() or self.object_type
        if object_type is None: return None
        return object_type.split(':')[2].lower()

    @property
    def type_label(self):
        """ Provides a localized string identifying the type of asset. """
        return _(self.type_id)

    @property
    def is_comment(self):
        """ Boolean property identifying whether the asset is a comment or not. """
        return self.type_id == 'comment'

    @property
    def is_local(self):
        """ Boolean property identifying whether the asset belongs to the
        group assigned to typepadapp.models.GROUP. """
        try:
            return typepadapp.models.GROUP.id in self.groups
        except:
            return False

    def get_comments(self, start_index=1, max_results=None, **kwargs):
        if max_results is None:
            max_results = settings.COMMENTS_PER_PAGE
        return self.comments.filter(start_index=start_index, max_results=max_results, **kwargs)

    @property
    def user(self):
        """ An alias for the author property. """
        return self.author


def asset_ref_type_id(self):
    object_type = self.object_type or self.object_types[0]
    if object_type is None: return None
    return object_type.split(':')[2].lower()

def asset_ref_type_label(self):
    return _(self.type_id)

# Extend AssetRef so that type_id, type_label work on asset references
# also
typepad.api.AssetRef.type_id = property(asset_ref_type_id)
typepad.api.AssetRef.type_label = property(asset_ref_type_label)


class Comment(typepad.Comment, Asset):

    def get_absolute_url(self):
        """Relative URL to the comment anchor on the asset permalink page."""
        try:
            return '%s#comment-%s' % (reverse('asset', args=[self.in_reply_to.url_id]), self.url_id)
        except NoReverseMatch:
            return None


class Favorite(typepad.Favorite, Asset):
    pass


class Post(typepad.Post, Asset):

    def save(self, group=None):
        # Warning - this only handles create, not update
        # so don't call this more than once
        assert group, "group parameter is unassigned"
        posts = group.post_assets
        posts.post(self)


class Audio(typepad.Audio, Asset):

    @property
    def link(self):
        return self.audio_link.url

    def save(self, file=None, group=None):
        # Warning - this only handles create, not update
        # so don't call this more than once
        assert group, "group parameter is unassigned"
        assert file, "file parameter is unassigned"
        self.groups = [ group.id ]
        resp, cont = typepad.api.browser_upload.upload(
            self, file, post_type=self.type_id, redirect_to='http://example.com/none')
        typepad.api.browser_upload.raise_error_for_response(resp, self)


class Video(typepad.Video, Asset):

    class ConduitError:
        def __init__(self, message):
            self.message = message

    def get_html(self):
        return self.video_link.embed_code

    def set_html(self, value):
        self.video_link.embed_code = value

    html = property(get_html, set_html)

    def get_link(self):
        return self.video_link.permalink_url

    def set_link(self, value):
        self.video_link = typepad.VideoLink(permalink_url=value)

    link = property(get_link, set_link)

    def save(self, group=None):
        # Warning - this only handles create, not update
        # so don't call this more than once
        assert group, "group parameter is unassigned"
        videos = group.video_assets
        try:
            videos.post(self)
        except (videos.RequestError, videos.ServerError), ex:
            # Bad video?
            try:
                reason = ex.response_error
            except AttributeError: # no reason from the API?
                reason = _('You have entered a URL that is either invalid or a URL for a video that can no longer be found.')
            raise self.ConduitError(reason)


class Photo(typepad.Photo, Asset):

    @property
    def link(self):
        try:
            return self.image_link.url
        except AttributeError:
            return None

    def save(self, file=None, group=None):
        # Warning - this only handles create, not update
        # so don't call this more than once
        assert group, "group parameter is unassigned"
        assert file, "file parameter is unassigned"
        self.groups = [ group.id ]
        resp, cont = typepad.api.browser_upload.upload(
            self, file, post_type=self.type_id, redirect_to='http://example.com/none')
        typepad.api.browser_upload.raise_error_for_response(resp, self)


class LinkAsset(typepad.LinkAsset, Asset):

    @property
    def link_title(self):
        """ Returns a title suitable for displaying the link asset title.

        This handles the case where a link asset has a link (which is
        a required field) but no title. If no actual title exists for
        the link, a cleaned-up version of the URL itself (eliminating the
        'http'/'https' protocol, any credentials that may be present, any
        query parameters and any trailing slash and obvious index page names).

        Another approach may be to attempt to retrieve the title of the HTML
        that may be returned from the link, but this would be an option upon
        creation of the asset, not upon rendering.
        """
        try:
            title = self.title
            assert title is not None and title != ''
            return title
        except:
            pass

        # use link as the display'd value; needs a shave and a haircut tho
        link = self.link
        link = re.sub('^https?://(?:.+?@)?', '', link)
        link = re.sub('^www\.', '', link)
        link = re.sub('\?.+$', '', link)
        link = re.sub('/(?:default|index)(\.\w+)?$', '', link)
        link = re.sub('/$', '', link)
        return link

    def get_link(self):
        import logging
        logging.getLogger("typepadapp.models.assets").warn(
            'LinkAsset.link is deprecated; use LinkAsset.target_url instead')
        return self.target_url

    def set_link(self, value):
        import logging
        logging.getLogger("typepadapp.models.assets").warn(
            'LinkAsset.link is deprecated; use LinkAsset.target_url instead')
        self.target_url = value

    link = property(get_link, set_link)

    def save(self, group=None):
        # Warning - this only handles create, not update
        # so don't call this more than once
        assert group, "group parameter is unassigned"
        links = group.link_assets
        links.post(self)


class Event(typepad.Event):

    @property
    def verb(self):
        try:
            return self.verbs[0]
        except IndexError:
            # No verbs
            return None

    @property
    def is_new_asset(self):
        return self.verb == 'tag:api.typepad.com,2009:NewAsset'

    @property
    def is_added_favorite(self):
        return self.verb == 'tag:api.typepad.com,2009:AddedFavorite'

    @property
    def is_local_asset(self):
        return self.object and isinstance(self.object, Asset) \
            and self.object.is_local

### Cache support

if settings.FRONTEND_CACHING:
    from typepadapp.caching import cache_link, cache_object, invalidate_rule

    # this is so we cache all Post, Video, Comment, etc., assets using
    # the same namespace.
    Asset.cache_namespace = "Asset"
    Favorite.cache_namespace = "Favorite"

    Asset.get_by_url_id = cache_object(Asset.get_by_url_id)
    asset_invalidator_for_comments = invalidate_rule(
        key=lambda sender, instance=None, **kwargs:
            isinstance(instance, Comment) and Asset.get_by_url_id(instance.in_reply_to.url_id),
        signals=[signals.asset_created, signals.asset_deleted],
        name="asset object invalidation for commenting")
    asset_invalidator_for_favorites = invalidate_rule(
        key=lambda sender, parent=None, **kwargs: parent,
        signals=[signals.favorite_created, signals.favorite_deleted],
        name="asset object invalidation for favoriting")

    Asset.comments = cache_link(Asset.comments)
    asset_comments_invalidator = invalidate_rule(
        key=lambda sender, instance=None, **kwargs:
            isinstance(instance, Comment) and Asset.get_by_url_id(instance.in_reply_to.url_id).comments,
        signals=[signals.asset_created, signals.asset_deleted],
        name="asset comments list invalidation for commenting")

    Asset.favorites = cache_link(Asset.favorites)
    # cache invalidation for asset object cache when a favorite is created/deleted
    asset_favorites_invalidator = invalidate_rule(
        key=lambda sender, parent=None, **kwargs: parent and parent.favorites,
        signals=[signals.favorite_created, signals.favorite_deleted],
        name="asset favorite list invalidation for favoriting")
