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
asset_deleted = Signal(providing_args=["instance", "group", "parent"])

favorite_created = Signal(providing_args=["instance", "group", "parent"])
favorite_deleted = Signal(providing_args=["instance", "group", "parent"])

# membership signals
member_joined = Signal(providing_args=["instance", "group"])
member_left = Signal(providing_args=["instance", "group"])
member_banned = Signal(providing_args=["instance", "group"])
member_unbanned = Signal(providing_args=["instance", "group"])

post_save = Signal(providing_args=["instance"])

# issued when app is starting up
post_start = Signal(providing_args=[])

# signals for forthcoming webhooks
# issued when a relationship change occurs on typepad for a member in this group
following_webhook = Signal(providing_args=["instance", "group"])
# issued when user edits their profile on typepad
profile_webhook = Signal(providing_args=["instance", "group"])
# issued when group metadata and administrator list is modified on typepad
group_webhook = Signal(providing_args=["group"])
