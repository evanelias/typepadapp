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

from django.dispatch import Signal

asset_created = Signal(providing_args=["instance", "group", "parent"])
"""Signal fired when a new group asset is created on TypePad."""
asset_deleted = Signal(providing_args=["instance", "group", "parent"])
"""Signal fired when a group asset is deleted from TypePad."""

favorite_created = Signal(providing_args=["instance", "group", "parent"])
"""Signal fired when a post is favorited by a user."""
favorite_deleted = Signal(providing_args=["instance", "group", "parent"])
"""Signal fired when a post is unfavorited by a user."""

# membership signals
member_joined = Signal(providing_args=["instance", "group", "token"])
"""Signal fired when a TypePad user joins the group."""
member_left = Signal(providing_args=["instance", "group"])
"""Signal fired when a TypePad user leaves the group (note: this is reserved and unsupported at this time)."""
member_banned = Signal(providing_args=["instance", "group"])
"""Signal fired when a member is banned from the group."""
member_unbanned = Signal(providing_args=["instance", "group"])
"""Signal fired when a banned member is unbanned."""

post_save = Signal(providing_args=["instance"])
"""Signal fired upon saving an object to TypePad."""

# issued when app is starting up
post_start = Signal(providing_args=[])
"""Signal fired upon launching the Django application."""

# signals for forthcoming webhooks
# issued when a relationship change occurs on typepad for a member in this group
following_webhook = Signal(providing_args=["instance", "group"])
"""Reserved for future use."""
# issued when user edits their profile on typepad
profile_webhook = Signal(providing_args=["instance", "group"])
"""Reserved for future use."""
# issued when group metadata and administrator list is modified on typepad
group_webhook = Signal(providing_args=["group"])
"""Reserved for future use."""

feedsub_content = Signal(providing_args=["entries", "subscription"])
