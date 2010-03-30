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

# Typepadapp application settings.
import os
import logging

TYPEPAD_COOKIES = {}
"""A dictionary of additional cookies (values, keyed on cookie names) to send
when making API requests to TypePad.

Use this setting if you're trying to use another API server besides TypePad
that requires additional cookies in its API requests. By default, no additional
cookies are sent.

"""

TYPEPAD_IDENTIFY_PARAMS = {}
"""A dictionary of additional parameters to pass when sending a user agent to
identify on TypePad.

Use this setting if you're trying to identify user agents with a service other
than TypePad that requires additional parameters to the OAuth identification
request. By default, no additional parameters are sent.

"""

BATCH_REQUESTS = not os.getenv('TYPEPAD_BATCHLESS')
"""Whether to use batch requests in TypePad API requests.

This boolean setting can be useful when debugging the request batching system.
Batch requests should always be used under normal conditions.

This setting defaults to `True`. The ``TYPEPAD_BATCHLESS`` environment
variable can be used to turn this setting off on a per-process basis.

"""

FRONTEND_CACHING = True
"""Setting that controls whether to use the Django caching framework for
caching object data retrieved from the TypePad API."""

LONG_TERM_CACHE_PERIOD = 60 * 60 * 24  # 1 day
"""Defines a cache timeout (in seconds) for cacheable items that can be
cached more aggressively."""

WELCOME_URL = None
"""A URL for a welcome page to which to send newly registered site members.

When group members register for the site from the home page, the authentication
system will redirect them to this URL instead. If the `WELCOME_URL` setting is
`None`, the new member is redirected back to the home page of the client site.
If new members click the "Sign in or register" link from a page other than the
home page, they are sent back to those pages to continue the action they wanted
to take there.

This setting defaults to `None` (no special welcome page).

"""

EVENTS_PER_PAGE = 25
"""The number of events to request from event fetching methods of
`typepad.models.User` instances.

This setting governs the number of objects requested by the `group_events()`,
`group_assets()`, and `group_notifications()` methods of
`typepadapp.models.User` instances, unless a ``max_results`` parameter is
specified by the caller.

By default, 25 events are requested by these methods.

"""

COMMENTS_PER_PAGE = 50
"""The number of comments to request from comment fetching methods of
`typepadapp.models` classes.

This setting governs the number of objects requested by the
`typepadapp.models.Asset.get_comments()` method, as well as the
`typepadapp.models.User.group_comments()` method, unless the caller specifies
a ``max_results`` parameter.

By default, 50 comments are requested by these methods.

"""

MEMBERS_PER_WIDGET = 30
"""The number of user accounts to request from member fetching methods of
`typepadapp.models.User` instances.

This setting governs the number of user accounts requested by the
`followers()` and `following()` methods of `typepadapp.models.User` instances,
unless a ``max_results`` parameter is specified by the caller.

By default, 30 user accounts are requested by these methods.

"""

# Logging

LOG_FORMAT = '%(name)-20s %(levelname)-8s %(message)s'
"""The format to use when logging messages.

By default, messages are logged as ``<logger name>        <level>  <log message>``.

"""

LOG_LEVEL = logging.INFO
"""The default log level at which to log messages.

For the root logger and other loggers for which a level is not specified in
the `LOG_LEVELS` setting, only messages at `LOG_LEVEL` or more important are
logged.

By default, messages of `INFO` level and more important are displayed.

"""

LOG_LEVELS = {
    'remoteobjects.http': logging.WARNING,
    'batchhttp.client': logging.WARNING,
    'typepad.oauthclient': logging.WARNING,
}
"""Additional log levels at which specific loggers should log messages.

This setting should be a dictionary of log levels keyed on logger name. Note
more specific names inherit levels from more general names; for example, if a
level for ``batchhttp.client.request`` isn't included in `LOG_LEVELS`, it will
inherit the level of the ``batchhttp.client`` logger (if set).

By default, the ``remoteobjects.http``, ``batchhttp.client``, and
``typepad.oauthclient`` loggers are set to display `WARNING` and more
important messages.

"""
