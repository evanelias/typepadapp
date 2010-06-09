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

from django.core.cache import cache
from django.conf import settings
import typepad

from typepadapp.models.assets import Event, Post
from typepadapp import signals


log = logging.getLogger(__name__)


class Blog(typepad.Blog):

    # A bit low-level for this lib... might be better to move this into
    # python-typepad-api, if possible.
    def discover_external_post_asset(self, permalink=''):
        """ Support for the /blogs/<id>/discover-external-post-asset endpoint.
        Takes a permalink string and returns a typepadapp.models.assets.Post. """
        
        assert permalink, "permalink parameter is unassigned"
        
        # Hit the endpoint manually
        url = '%s/blogs/%s/discover-external-post-asset.json' % (settings.BACKEND_URL, self.url_id)
        request_body = json.dumps({ 'permalinkUrl': permalink })
        response, content = typepad.client.request(url, method='POST', body=request_body)
        
        # Convert the "asset" part of the response into a real typepadapp.models.assets.Post
        # object.  But to do so, we need to hack in a content-location header which specifies
        # the independent location of the asset, since this endpoint does not supply one.
        content_obj = json.loads(content)
        response['content-location'] = '%s/assets/%s.json' % (settings.BACKEND_URL, content_obj['asset']['urlId'])
        post = Post()
        post.update_from_response(url, response, json.dumps(content_obj['asset']))
        return post
    
### Cache support
### TODO: implement cache invalidation
if settings.FRONTEND_CACHING:
    from typepadapp.caching import cache_link, cache_object, invalidate_rule

    # Cache population/invalidation
    Blog.get_by_url_id = cache_object(Blog.get_by_url_id)

    # invalidation not yet implemented!