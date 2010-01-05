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

import logging
from types import ModuleType

from django.conf import settings
from django.conf.urls.defaults import patterns, url
from django.contrib.sessions.models import Session
from django.core.urlresolvers import resolve, Resolver404
from django.core.exceptions import MiddlewareNotUsed
from django.http import HttpResponse, HttpResponseNotFound
from django.template import Template, Context


wizard_urlconf = ModuleType('wizard_urlconf')

wizard_urlconf.urlpatterns = patterns('typepadapp.middleware.config',
    url(r'^$', 'incomplete_configuration'),
)


class ConfigurationMiddleware(object):

    log = logging.getLogger('.'.join((__name__, 'ConfigurationMiddleware')))

    def __init__(self):
        # If we're not in debug mode, disable this middleware.
        if not settings.DEBUG:
            raise MiddlewareNotUsed

    def process_request(self, request):
        return self.check_local_database(request) or self.check_keys(request)

    def check_keys(self, request):
        try:
            if (settings.OAUTH_CONSUMER_KEY and settings.OAUTH_CONSUMER_SECRET and
                settings.OAUTH_GENERAL_PURPOSE_KEY and settings.OAUTH_GENERAL_PURPOSE_SECRET):
                return
        except AttributeError:
            pass

        self.log.debug('Showing incomplete configuration response due to missing keys')
        return self.incomplete_configuration(request, missing_keys=True)

    def check_local_database(self, request):
        try:
            Session.objects.count()
        except Exception, exc:
            self.log.debug('Showing incomplete configuration response due to uninitialized database (%s.%s: %s)',
                type(exc).__module__, type(exc).__name__, str(exc))
            return self.incomplete_configuration(request, missing_database=True)

    def incomplete_configuration(self, request, **reasons):
        try:
            view, args, kwargs = resolve(request.path, urlconf=wizard_urlconf)
        except Resolver404:
            return HttpResponseNotFound()

        kwargs['request'] = request  # ??

        try:
            response = view(*args, **kwargs)
        except Http404:
            return HttpResponseNotFound()
        else:
            return response


def incomplete_configuration(request, **kwargs):
    """Create an incomplete configuration error response."""

    # We're returning this before session middleware runs, so fake the
    # session set for djangoflash's process_response().
    request.session = ()

    base_template = Template(BASE_TEMPLATE, name='Configuration base template')
    t = Template(CONFIGURATION_TEMPLATE, name='Incomplete configuration template')
    c = Context(dict(
        base_template = base_template,
        project_name=settings.SETTINGS_MODULE.split('.')[0],
        **kwargs
    ))
    return HttpResponse(t.render(c), mimetype='text/html')


BASE_TEMPLATE = """
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:at="http://www.sixapart.com/ns/at" id="sixapart-standard">
<head>
  <style type="text/css">
    html * { padding:0; margin:0; }
    body * { padding:10px 20px; }
    body * * { padding:0; }
    body { font:small sans-serif; }
    body>div { border-bottom:1px solid #ddd; }
    h1 { font-weight:normal; }
    h2 { margin-bottom:.8em; }
    h2 span { font-size:80%; color:#666; font-weight:normal; }
    h3 { margin:1em 0 .5em 0; }
    h4 { margin:0 0 .5em 0; font-weight: normal; }
    table { border:1px solid #ccc; border-collapse: collapse; width:100%; background:white; }
    tbody td, tbody th { vertical-align:top; padding:2px 3px; }
    thead th { padding:1px 6px 1px 3px; background:#fefefe; text-align:left; font-weight:normal; font-size:11px; border:1px solid #ddd; }
    tbody th { width:12em; text-align:right; color:#666; padding-right:.5em; }
    ul { margin-left: 2em; margin-top: 1em; }
    li.thisone span { background-color: #e8ff66; }
    #summary { background: #e0ebff; }
    #summary h2 { font-weight: normal; color: #666; }
    #explanation { background:#eee; }
    #instructions { background:#f6f6f6; }
    #summary table { border:none; background:transparent; }
  </style>
</head>

<body>
<div id="summary">
    {% block summary %}
  <h1>It worked!</h1>
  <h2>Congratulations on your new TypePad-powered website.</h2>
    {% endblock %}
</div>

<div id="instructions">
    {% block instructions %}
    {% endblock %}
</div>

<div id="explanation">
    {% block explanation %}
  <p>
    You're seeing this message because you have <code>DEBUG = True</code> in your
    Django settings file and you haven't finished configuring this installation.
    Get to work!
  </p>
    {% endblock %}
</div>
</body>
</html>
"""

CONFIGURATION_TEMPLATE = """
{% extends base_template %}
{% block instructions %}

    {% if missing_database %}
        <p>You seem to be <strong>missing a database</strong>. Try:</p>

        <blockquote><p><samp>python manage.py syncdb</samp></p></blockquote>

        <p>to initialize the database.</p>

        <p><button>Done!</button></p>
    {% else %}{% if missing_keys %}
        <p>Your application <strong>needs TypePad API keys</strong> to talk to TypePad.</p>

        <p>
        <a href="http://www.typepad.com/account/access/api_key">Get an application key</a>
        <a href="http://www.typepad.com/account/access/api_key" class="arrow">&rarr;</a>
        </p>

        <p>Then paste your keys in below to save them:</p>

        <form><textarea></textarea></form>

        <p><button>Done!</button></p>
    {% endif %}{% endif %}
{% endblock %}
"""
