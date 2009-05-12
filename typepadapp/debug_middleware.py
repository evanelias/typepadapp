import os
import django
import SocketServer
import traceback
import typepad
from time import time
from batchhttp import client
from django.utils.encoding import smart_unicode
from django.template.loader import render_to_string
from django.core.signals import request_started
from typepad import client as tp_client

try:
    import resource
except ImportError:
    pass # Will fail on Win32

"""
This module contains some stats tracking middleware that is useful in auditing
the number of requests being made per page and tracking down performance problems.
It is not thread-safe, and may expose sensitive information about your site.

Do NOT use this module in production.

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
        self.callback = callback
client.Request = RequestStatTracker


class BatchRequestStatTracker(client.BatchRequest):
    """
    Replacement for BatchRequest that stores stats in `self.stats`.
    """

    def process(self, *args, **kwargs):
        start = time()
        try:
            return super(BatchRequestStatTracker, self).process(*args, **kwargs)
        finally:
            stop = time()
            self.stats = {
                'count': len(self.requests),
                'subrequests': [request for request in self.requests if request.executed],
                'time': (stop - start),
            }
client.BatchRequest = BatchRequestStatTracker


class TypePadClientStatTracker(typepad.TypePadClient):
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
tp_client.__class__ = TypePadClientStatTracker
def reset_requests(*args, **kwargs):
    tp_client.requests = []
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
        self.total_time = (time() - self._start_time) * 1000
        if self.has_resource:
            self._end_rusage = resource.getrusage(resource.RUSAGE_SELF)

    def time_summary(self):
        if self.has_resource:
            utime = self._end_rusage.ru_utime - self._start_rusage.ru_utime
            stime = self._end_rusage.ru_stime - self._start_rusage.ru_stime
            return 'Time: %0.2fms, %0.2fms CPU' % (self.total_time, (utime + stime) * 1000.0)
        else:
            return 'Time: %0.2fms' % self.total_time

    def batch_request_count(self):
        return len(tp_client.requests)

    def subrequest_count(self):
        return sum([len(request.stats['subrequests']) for request in tp_client.requests])

    def request_time(self):
        return "%.3f" % (sum([request.stats['time'] for request in tp_client.requests]) * 1000.0)

    def requests(self):
        return tp_client.requests

    def render_toolbar(self):
        return render_to_string('debug_toolbar.html', {
            'toolbar': self,
        })


class DebugToolbarMiddleware(object):

    def process_request(self, request):
        """Setup the request monitor."""
        self.toolbar = DebugToolbar(request)
        self.toolbar.start_timer()

    def process_response(self, request, response):
        self.toolbar.stop_timer()
        if response['content-type'].split(';')[0] in _HTML_TYPES:
            response.content = replace_insensitive(smart_unicode(response.content), 
                                                   u'</body>', 
                                                   smart_unicode(self.toolbar.render_toolbar() + '</body>'))
        return response
