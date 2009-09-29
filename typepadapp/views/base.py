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

from urlparse import urljoin
from os import path
import re

from django import http
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.utils.http import urlquote
from django.contrib.auth.decorators import login_required
from django.contrib.syndication.feeds import Feed
from django.utils.feedgenerator import Atom1Feed

from typepadapp.utils.paginator import FinitePaginator, EmptyPage

import typepad


def parse_etags(etag_str):
    """
    Parses a string with one or several etags passed in If-None-Match and
    If-Match headers by the rules in RFC 2616. Returns a list of etags
    without surrounding double quotes (") and unescaped from \<CHAR>.
    """
    etags = re.findall(r'(?:W/)?"((?:\\.|[^"])*)"', etag_str)
    if not etags:
        # etag_str has wrong format, treat it as an opaque string then
        return [etag_str]
    etags = [e.decode('string_escape') for e in etags]
    return etags


class GenericView(http.HttpResponse):
    """
    A base view class for TypePadView.

    This class by default permits 'GET' requests, and will automatically
    handle conditional requests (respecting If-Modified-Since and Etag HTTP
    headers).

    This class inherits from ``HttpResponse``. When invoked, the view is
    instantiated, and given the request and url parameters just like a
    Django view function is. The resulting value is the response that is
    used for the active request.
    """
    methods = ('GET',)

    def __init__(self, request, *args, **kwargs):
        super(GenericView, self).__init__()

        self.context = RequestContext(request)

        obj = self.setup(request, *args, **kwargs)

        if not obj:
            obj = self.conditional_dispatch(request, *args, **kwargs)

        if isinstance(obj, http.HttpResponse):
            self._update(obj)
        else:
            self.content = obj

    def _update(self, response):
        """
        Merge the info from another response with this instance.

        This method simply copies the attributes from the given response to
        this instance, with the exceptions of the ``_headers`` and ``cookies``
        dictionaries, whose ``update`` methods are called. This means that any
        headers or cookies which are present in this response but not the
        argument are preserved.
        """
        self._charset = response._charset
        self._is_string = response._is_string
        self._container = response._container
        self._headers.update(response._headers)
        self.cookies.update(response.cookies)
        self.status_code = response.status_code
        self.content = response.content

        if self.status_code == 405:
            self.content = 'Allowed methods: %s' % self['Allow']

    def dispatch(self, request, *args, **kwargs):
        """
        This method dispatches the request to the appropriate method based on
        the HTTP request method.
        """
        allowed, response = self._check_request_allowed(request, *args, **kwargs)
        if not allowed:
            return response

        if not hasattr(self, request.method.lower()) or \
           not callable(getattr(self, request.method.lower())):
            raise Exception("Allowed view method %s does not exist." % request.method.lower())
        return getattr(self, request.method.lower())(request, *args, **kwargs)

    def _check_request_allowed(self, request, *args, **kwargs):
        """
        This method determines whether the user is allowed to perform the request
        method that was sent to the server.
        """
        if request.method.lower() not in (method.lower() for method in self.methods):
            return False, http.HttpResponseNotAllowed(self.methods)
        return True, None

    def conditional_dispatch(self, request, *args, **kwargs):
        """
        For GET, HEAD, and PUT requests, this method calls the ``etag()`` and
        ``last_modified()`` methods and then checks whether a the appropriate
        preconditions are satisfied before continuing.
        """
        allowed, response = self._check_request_allowed(request, *args,
                                                        **kwargs)
        if not allowed:
            return response

        if request.method not in ('GET', 'HEAD', 'PUT'):
            return self.dispatch(request, *args, **kwargs)

        last_modified = str(self.last_modified(request, *args, **kwargs))
        etag = self.etag(request, *args, **kwargs)

        if request.method in ('GET', 'HEAD'):
            # Get HTTP request headers
            if_modified_since = request.META.get('HTTP_IF_MODIFIED_SINCE', None)
            if_none_match = request.META.get('HTTP_IF_NONE_MATCH', None)
            if if_none_match:
                if_none_match = parse_etags(if_none_match)

            # Calculate "not modified" condition
            not_modified = (if_modified_since or if_none_match) and \
                           (not if_modified_since or \
                            last_modified == if_modified_since) and \
                           (not if_none_match or etag in if_none_match)

            # Create appropriate response
            if not_modified:
                response = http.HttpResponseNotModified()
            else:
                response = self.dispatch(request, *args, **kwargs)
        else: # method == 'PUT'
            # Get the HTTP request headers
            if_match = request.META.get('HTTP_IF_MATCH', None)
            if_unmodified_since = request.META.get('HTTP_IF_UNMODIFIED_SINCE', None)
            if if_match:
                if_match = parse_etags(if_match)

            # Calculate "modified" condition
            modified = (if_unmodified_since \
                        and last_modified != if_unmodified_since) or \
                       (if_match and etag not in if_match)

            # Create appropriate response
            if modified:
                response = http.HttpResponse(status=412) # precondition failed
            else:
                response = self.dispatch(request, *args, **kwargs)
        return response

    def last_modified(self, request, *args, **kwargs):
        """
        Returns a value representing the last modification timestamp of the
        view.

        To support If-Modified-Since headers, return a timestamp representing
        the last-modified date of the view. This may be based on a physical
        file timestamp, or the last modified element of the view being
        published.
        """
        return None

    def etag(self, request, *args, **kwargs):
        """
        Returns a value used as the Etag for the view.

        To support If-None-Match Etag HTTP headers, return an appropriate
        etag here.
        """
        return None

    def get(self, request, *args, **kwargs):
        """
        Handles ``GET`` requests.

        Subclasses should override this method to handle GET requests. The
        return value should be a HttpResponse instance.
        """
        return http.HttpResponse()

    def setup(self, request, *args, **kwargs):
        """
        Called for all invocation of the view to set up the view prior to
        dispatching to the appropriate handler.

        Subclasses can override this method which is invoked after the class
        has been initialized but prior to the dispatch to the ``GET``,
        ``POST``, etc. handler.
        """
        pass

    def render_to_response(self, template, more_context=None):
        """
        A shortcut method that runs the render_to_response
        Django shortcut.

        It will apply the view's context object as the context for rendering
        the template. Additional context variables may be passed in, similar
        to the render_to_response shortcut.
        """
        if more_context:
            self.context.push()
            self.context.update(more_context)
        results = render_to_response(template, self.context)
        if more_context:
            self.context.pop()
        return results


class TypePadView(GenericView):
    """
    A subclass of the ``GenericView`` class that adds TypePad-specific
    features and behavior.

    This class supports several members that make it easy to handle
    forms and pagination.

    In particular, a special method ``select_from_typepad()`` may be declared
    for a subclass of ``TypePadView``. When this method is present, a
    batch request is made to the TypePad API for all data elements requested
    in the ``select_from_typepad()`` method.

    View properties:

    paginate_by: specify this value if the view is to support pagination
        of a list of objects. An ``object_list`` member is expected to be
        assigned in order to provide context for pagination. A template
        context variable named ``page_obj`` is also set, being an instance
        of ``FinitePaginator``.
    object_list: Assign to this member when the view is to paginate a
        list of objects. This member is also assigned to the
    offset: When paginating a list of objects, this member is
        automatically assigned, based on the ``page`` parameter to the view
        and the value of the ``paginate_by`` property. This value may
        be used to control the selection of rows used to populate the
        ``object_list`` member during the ``setup()`` or
        ``select_from_typepad()`` methods.
    limit: Assigned as the number of rows to select for the ``object_list``
        member. This is typically set to ``paginate_by``.
    paginate_template: Assign a string to control the format of
        next, previous links.
    form: The Django form class that is to be used for any editable object
        the view is presenting. If this member is set, it is instantiated
        during the ``setup()`` method and during a ``POST`` request, the
        values of the ``POST`` are given to it. Once the form is instantiated
        it is assigned to a ``form_instance`` member. The form is also
        assigned to the template context as ``form``.
    template_name: Assign the name of a Django template file to be
        used for ``GET`` requests. The value of this property is stripped of
        any path and suffix and assigned to the 'view' template context
        variable.
    login_required: If the view requires an authenticated user to run,
        set this member to True. It relies on the settings.LOGIN_URL value
        for redirecting the user to a login form.

    Context variables:

    The following variables are assigned by default and available for any
    template.

    view: Assigned as the basename of the ``template_name`` member, minus any
        file path and extension.
    form: The value of the ``form_instance`` member.
    page_obj: Set when ``paginate_by`` member is assigned.
    """
    paginate_by = None
    paginate_template = None
    form = None
    template_name = None
    login_required = False

    def __init__(self, request, *args, **kwargs):
        self.form_instance = None
        super(TypePadView, self).__init__(request, *args, **kwargs)

    def select_typepad_user(self, request):
        """
        If a session token is found, returns the authenticated TypePad user,
        otherwise, returns the Django AnonymousUser. Replaces any authentication
        middleware.
        """
        from django.contrib.auth import get_user
        request.user = get_user(request)
        self.context.update({'user': request.user, 'request': request})

    def select_from_typepad(self, request, *args, **kwargs):
        """
        Empty method used for issuing TypePad API subrequests for the view.
        """
        pass

    def filter_object_list(self):
        """
        Empty method used for any filtering of objects returned by the API.
        """
        pass

    def _check_request_allowed(self, request, *args, **kwargs):
        """
        Enforces the ``login_required`` setting for the entire view.
        """
        allowed, response = \
            super(TypePadView, self)._check_request_allowed(request, *args,
                                                            **kwargs)
        if not allowed:
            return allowed, response
        if self.login_required:
            response = login_required(lambda r: False)(request)
            if response:
                return False, response
        return True, None

    def typepad_request(self, request, *args, **kwargs):
        """
        Issues a single TypePad batch request to render the current view.

        This method is a wrapping method for the ``select_from_typepad()``
        method which itself does individual TypePad API subrequests necessary
        for the view. If a session token is present, the authed user is also
        fetched with this batch request.

        In addition, the pagination state is set if the ``paginate_by``
        attribute is assigned.
        """
        # Pagination setup
        if self.paginate_by:
            self.object_list = None
            pagenum = int(kwargs.get('page', 1))
            self.offset = (pagenum - 1) * self.paginate_by + 1
            self.limit = self.paginate_by

        typepad.client.batch_request()

        self.select_typepad_user(request)
        # Issue this check here, since this is the earliest that
        # we have a user context available
        allowed, response = self._check_request_allowed(request, *args,
                                                        **kwargs)
        if not allowed:
            return response

        self.select_from_typepad(request, *args, **kwargs)
        typepad.client.complete_batch()

        # Page parameter assignment
        if self.paginate_by and self.object_list:
            self.filter_object_list()
            link_template = self.paginate_template or urljoin(request.path, '/page/%d')
            paginator = FinitePaginator(self.object_list, self.paginate_by,
                                        offset=self.offset,
                                        link_template=link_template)
            try:
                self.context['page_obj'] = paginator.page(pagenum)
            except EmptyPage:
                raise http.Http404

    def setup(self, request, *args, **kwargs):
        """
        Initializes a TypePadView instance.
        """
        super(TypePadView, self).setup(request, *args, **kwargs)

        # View parameter from view or template_name
        view = kwargs.get('view', None)
        if view is None and self.template_name:
            # foo/bar.html -> bar
            view = path.splitext(path.split(self.template_name)[1])[0]
        self.context['view'] = view

        if self.form:
            # We should also accept 'POST' for form support
            self.methods += ('POST', )

            if request.method == 'POST':
                self.form_instance = self.form(request.POST, request.FILES)
            else:
                self.form_instance = self.form()

            self.context['form'] = self.form_instance

        if request.method == 'GET':
            return self.typepad_request(request, *args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        """
        Dispatch for TypePadView, which handles invalid form POST requests.

        In the event that the form is invalid, the response is unset,
        the TypePad API requests for the view are issued and the 'get' handler
        is invoked to return a response.
        """
        response = super(TypePadView, self).dispatch(request, *args, **kwargs)
        if self.form and (request.method == 'POST') and (response is None):
            # If a form is present, but invalid, then issue the TypePad
            # requests for this view and invoke the GET handler for the
            # response.
            if not self.form_instance.is_valid() or request.flash.get('errors'):
                response = self.typepad_request(request, *args, **kwargs)
                if response:
                    return response
                response = self.get(request, *args, **kwargs)
        return response

    def get(self, request, *args, **kwargs):
        """
        Base handler for GET requests.

        When the ``template_name`` attribute is assigned, the template
        is rendered as the response to the request. Otherwise, an
        empty HttpResponse is returned.
        """
        template = view = kwargs.get('template_name', self.template_name)
        if template is None:
            return super(TypePadView, self).get(request, *args, **kwargs)
        return self.render_to_response(template)


class TypePadFeed(Feed):
    """ A subclass of the Django ``Feed`` class that handles selecting data
    from the TypePad client library. """

    feed_type = Atom1Feed

    def get_object(self, *args, **kwargs):
        typepad.client.batch_request()
        self.select_from_typepad(*args, **kwargs)
        typepad.client.complete_batch()
        return getattr(self, 'object', None)

    def select_from_typepad(self, *args, **kwargs):
        pass


class TypePadEventFeed(TypePadFeed):
    """ A subclass of the ``TypePadFeed`` class that handles serving
    Asset items. """

    def item_link(self, event):
        return event.object.get_absolute_url()

    def item_author_name(self, event):
        return event.actor.display_name

    def item_author_link(self, event):
        return event.actor.get_absolute_url()

    def item_pubdate(self, event):
        return event.published
