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

import os
import SocketServer
import traceback
from time import time

import django
from django.conf import settings
from django.utils.encoding import smart_unicode
from django.template.loader import render_to_string
from django.template import RequestContext
from django.core.signals import request_started
from django.core.exceptions import MiddlewareNotUsed

from batchhttp import client

import typepad

from typepadapp.signals import post_start

try:
    import resource
except ImportError:
    pass # Will fail on Win32

"""
This module contains some stats tracking middleware that is useful in auditing
the number of requests being made per page and tracking down performance problems.
It is not thread-safe, and may expose sensitive information about your site.

Do NOT use this module in production. This middleware will disable itself
when DEBUG is set to False in your Django settings module.

"""


_HTML_TYPES = ('text/html', 'application/xhtml+xml')

# Figure out some paths
django_path = os.path.realpath(os.path.dirname(django.__file__))
socketserver_path = os.path.realpath(os.path.dirname(SocketServer.__file__))


def same_path_prefix(p1, p2):
    for part1, part2 in zip(os.path.dirname(os.path.realpath(p1)).split(os.sep),
                            os.path.dirname(os.path.realpath(p2)).split(os.sep)):
        if part1 != part2:
            return False
    return True


def tidy_stacktrace(strace, ignore_after=None):
    """ 
    Clean up stacktrace and remove all entries that:
    1. Are part of Django (except contrib apps)
    2. Are part of SocketServer (used in Django's dev server)
    3. Are the last entry (which is part of our stacktracing code)
    """
    # based on django-debug-toolbar: http://github.com/robhudson/django-debug-toolbar/tree/master
    if ignore_after is not None:
        ignore_after = ignore_after.__file__
    trace = []
    for s in strace[:-1]:
        s_path = os.path.realpath(s[0])
        if ignore_after is not None and same_path_prefix(ignore_after, s_path):
            break
        if s_path.startswith(django_path) and not 'django/contrib' in s_path:
            continue
        if s_path.startswith(socketserver_path):
            continue
        trace.append((s[0], s[1], s[2], s[3]))
    return trace


def replace_insensitive(string, target, replacement):
    """Case-insensitive string replace."""
    no_case = string.lower()
    index = no_case.rfind(target.lower())
    if index >= 0:
        return string[:index] + replacement + string[index + len(target):]
    else: # no results so return the original string
        return string


class RequestStatTracker(client.Request):
    """
    Replacement for Request that stores stats in `self.stats`.
    """

    def __init__(self, reqinfo, callback):
        super(RequestStatTracker, self).__init__(reqinfo, callback)
        self.opened_stack = tidy_stacktrace(traceback.extract_stack(), ignore_after=typepad)
        self.executed = False # Many requests are never executed.

        old_callback = self.callback
        def callback(uri, httpresponse, body):
            self.executed = True

            # Replace https:// with http:// so we can make links to the unauthed endpoints.
            if uri.startswith('https://'):
                http_uri = 'http://' + uri[8:]
            else:
                http_uri = uri

            self.stats = {
                'uri': uri,
                'http_uri': http_uri,
                'length': len(body),
                'body': body,
                'status': (httpresponse.status, 304)[httpresponse.fromcache],
                'content_type': httpresponse.get('content-type'),
            }
            return old_callback(uri, httpresponse, body)
        callback.alive = old_callback.alive
        callback.orig_callback = old_callback
        self.callback = callback
client.Request = RequestStatTracker


class BatchRequestStatTracker(client.BatchRequest):
    """
    Replacement for BatchRequest that stores stats in `self.stats`.
    """

    def __init__(self):
        super(BatchRequestStatTracker, self).__init__()
        self.stats = {}

    def process(self, *args, **kwargs):
        start = time()
        try:
            return super(BatchRequestStatTracker, self).process(*args, **kwargs)
        finally:
            stop = time()
            self.stats.update({
                'count': len(self.requests),
                'subrequests': [request for request in self.requests if request.executed],
                'time': (stop - start),
            })

    def handle_response(self, http, response, content):
        self.stats.update({
            'typepad_version': response.get('x-debug-version'),
            'typepad_revision': response.get('x-debug-revision'),
            'typepad_webserver': response.get('x-webserver'),
            'typepad_query_count': response.get('x-dbquery-count'),
            'typepad_time': response.get('x-tpx-time'),
            'typepad_db_queries': [value for key, value in response.iteritems() 
                                    if key.startswith('x-dbquery') and not key.endswith('-count')],
        })
        return super(BatchRequestStatTracker, self).handle_response(http, response, content)

client.BatchRequest = BatchRequestStatTracker


def get_typepad_client(superclass):
    class TypePadClientStatTracker(superclass):
        """
        Replacement for BatchClient that retains all executed requests in `self.requests`.
        """
        requests = []

        def batch_request(self):
            request = super(TypePadClientStatTracker, self).batch_request()
            request.opened_stack = tidy_stacktrace(traceback.extract_stack())

        def complete_batch(self):
            self.batchrequest.closed_stack = tidy_stacktrace(traceback.extract_stack())
            self.requests.append(self.batchrequest)
            super(TypePadClientStatTracker, self).complete_batch()
    return TypePadClientStatTracker


def reset_requests(*args, **kwargs):
    typepad.client.requests = []
request_started.connect(reset_requests)


class DebugToolbar(object):
    try:
        resource
    except NameError:
        has_content = False
        has_resource = False
    else:
        has_content = True
        has_resource = True

    def __init__(self, request):
        self.request = request

    def start_timer(self):
        self._start_time = time()
        if self.has_resource:
            self._start_rusage = resource.getrusage(resource.RUSAGE_SELF)

    def stop_timer(self):
        self.total_time = (time() - self._start_time)
        if self.has_resource:
            self._end_rusage = resource.getrusage(resource.RUSAGE_SELF)

    def cpu_time(self):
        if self.has_resource:
            utime = self._end_rusage.ru_utime - self._start_rusage.ru_utime
            stime = self._end_rusage.ru_stime - self._start_rusage.ru_stime
            return (utime + stime)
        return ''

    def batch_request_count(self):
        return len(typepad.client.requests)

    def subrequest_count(self):
        return sum([len(request.stats['subrequests']) for request in typepad.client.requests])

    def request_time(self):
        return sum([request.stats['time'] for request in typepad.client.requests])

    def requests(self):
        return typepad.client.requests

    def typepad_query_count(self):
        "The total number of queries performed by the backend for all batch requests."
        return sum([int(request.stats['typepad_query_count']) for request in typepad.client.requests if 'typepad_query_count' in request.stats])

    def typepad_time(self):
        return sum([float(request.stats['typepad_time']) for request in typepad.client.requests if 'typepad_time' in request.stats])

    def _get_typepad_stat(self, name):
        """Tries to find the stat identified by `name` in a request. Assumption is
        that the stat is the same for all subrequests so we return the first one."""
        for request in typepad.client.requests:
            try:
                return request.stats[name]
            except KeyError:
                pass

    def typepad_version(self):
        return self._get_typepad_stat('typepad_version')

    def typepad_revision(self):
        return self._get_typepad_stat('typepad_revision')

    def typepad_webserver(self):
        return self._get_typepad_stat('typepad_webserver')

    def render_toolbar(self, request):
        return render_to_string('debug_toolbar.html', {
            'toolbar': self,
        }, context_instance=RequestContext(request))


class DebugToolbarMiddleware(object):
    def __init__(self):
        # If we're not in debug mode, disable this middleware.
        if not settings.DEBUG:
            raise MiddlewareNotUsed
        else:
            # Remap typepad.client's class to TypePadClientStatTracker
            typepad.client.__class__ = get_typepad_client(typepad.client.__class__)

    def process_request(self, request):
        """Setup the request monitor."""
        request.toolbar = DebugToolbar(request)
        request.toolbar.start_timer()

    def process_response(self, request, response):
        # Request might not have a toolbar if process_request was bypassed by an 
        # earlier piece of middleware returning a response.
        if hasattr(request, 'toolbar'):
            request.toolbar.stop_timer()
            if response['content-type'].split(';')[0] in _HTML_TYPES:
                response.content = replace_insensitive(smart_unicode(response.content), 
                                                       u'</body>', 
                                                       smart_unicode(request.toolbar.render_toolbar(request) + '</body>'))
        return response
