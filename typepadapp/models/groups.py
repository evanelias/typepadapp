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

from django.core.cache import cache
from django.conf import settings

import typepad
from typepadapp.models.assets import Event
from typepadapp import signals


class Group(typepad.Group):

    admin_list = None

    def __init__(self):
        self.admin_list = None

    def admins(self):
        if self.admin_list is None:
            admin_list_key = 'group:%s:admin_list' % self.url_id

            admin_list = cache.get(admin_list_key)
            if admin_list is None:
                typepad.client.batch_request()
                try:
                    admin_list = self.memberships.filter(admin=True)
                    typepad.client.complete_batch()
                except Exception, exc:
                    log.error('Error loading admin list %s: %s', self.url_id, str(exc))
                    raise

                cache.set(admin_list_key, admin_list)

            self.admin_list = admin_list

        return self.admin_list

    def cache_prefix(self):
        key = 'cacheprefix:Group:%s' % self.xid
        prefix = cache.get(key)
        if prefix is None:
            prefix = 1
            cache.set(key, prefix)
        return prefix

    def cache_touch(self):
        try:
            cache.incr(str('cacheprefix:Group:%s' % self.xid))
        except ValueError:
            # ignore in the event that the prefix doesn't exist
            pass


### Cache support

if settings.FRONTEND_CACHING:
    from typepadapp.caching import cache_link, cache_object, \
        invalidate_link, invalidate_object

    # Cache population/invalidation
    Group.get_by_url_id = cache_object(Group.get_by_url_id)
    # invalidate with: signals.group_webhook

    Group.events = cache_link(Group.events)
    group_events_invalidator = invalidate_link(
        key=lambda sender, group=None, **kwargs:
            group and ('/groups/%s/events.json' % group.xid),
        signals=[signals.asset_created, signals.asset_deleted],
        name="Group events invalidation for asset_created/asset_deleted signal")

    Group.memberships = cache_link(Group.memberships)
    # invalidate with signals.member_joined, signals.member_left
