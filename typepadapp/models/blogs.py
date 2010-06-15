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

import logging
import time
import simplejson as json
import httplib2
from urlparse import urljoin

from django.core.cache import cache
from django.conf import settings
from typepadapp.models.assets import Event, Post, Comment
from typepadapp import signals
import typepad

log = logging.getLogger(__name__)


class Blog(typepad.Blog):

    def discover_external_post_asset(self, permalink):
        """ Support for the /blogs/<id>/discover-external-post-asset endpoint.
        Takes a permalink string and returns a Post. """

        body = json.dumps({ 'permalinkUrl': permalink })
        headers = {'content-type': self.content_types[0]}
        url = urljoin(typepad.client.endpoint, '/blogs/%s/discover-external-post-asset.json' % self.url_id)
        request = self.get_request(url=url, method='POST', body=body, headers=headers)
        response, content = typepad.client.request(**request)

        class ExternalPostAsset(typepad.TypePadObject):
            asset = typepad.fields.Object('Post')
        obj = ExternalPostAsset()
        obj.update_from_response(url, response, content)
        return obj.asset


class AnonymousComment(Comment):
    name = typepad.fields.Field()
    email = typepad.fields.Field()

    
### Cache support
### TODO: implement cache invalidation
if settings.FRONTEND_CACHING:
    from typepadapp.caching import cache_link, cache_object, invalidate_rule

    # Cache population/invalidation
    Blog.get_by_url_id = cache_object(Blog.get_by_url_id)

    # invalidation not yet implemented!