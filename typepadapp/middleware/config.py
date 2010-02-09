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
import os
from os.path import dirname, join
import re
from types import ModuleType

from django.conf import settings
from django.conf.urls.defaults import patterns, url
from django.contrib.sessions.models import Session
from django.core.urlresolvers import resolve, Resolver404
from django.core.exceptions import MiddlewareNotUsed
from django.http import HttpResponse, HttpResponseNotFound, Http404
from django.template import Template, Context


wizard_urlconf = ModuleType('wizard_urlconf')

wizard_urlconf.urlpatterns = patterns('typepadapp.middleware.config',
    url(r'^$', 'incomplete_configuration'),
    url(r'^save_keys$', 'save_keys'),
) + patterns('',
    url(r'^(?P<path>images/\w+\.png)$', 'django.views.static.serve',
        {'document_root': join(dirname(dirname(__file__)), 'static')}),
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
        return self.incomplete_configuration(request, reason='missing_keys')

    def check_local_database(self, request):
        # When running under Google AppEngine, skip this step
        if settings.DATABASE_ENGINE == 'appengine':
            return

        try:
            Session.objects.count()
        except Exception, exc:
            self.log.debug('Showing incomplete configuration response due to uninitialized database (%s.%s: %s)',
                type(exc).__module__, type(exc).__name__, str(exc))
            return self.incomplete_configuration(request, reason='missing_database')

    def incomplete_configuration(self, request, reason=None):
        try:
            view, args, kwargs = resolve(request.path, urlconf=wizard_urlconf)
        except Resolver404:
            return HttpResponseNotFound('not found', content_type='text/plain')

        request.reason = reason
        kwargs['request'] = request

        # We're returning this before session middleware runs, so fake the
        # session set for djangoflash's process_response().
        request.session = ()

        try:
            response = view(*args, **kwargs)
        except Http404:
            return HttpResponseNotFound('not found', content_type='text/plain')
        else:
            return response


def render_wizard_page(request, template, **kwargs):
    if not isinstance(template, Template):
        template = Template(template)

    base_template = Template(BASE_TEMPLATE, name='Configuration base template')
    c = Context(dict(
        base_template=base_template,
        project_name=settings.SETTINGS_MODULE.split('.')[0],
        **kwargs
    ))
    return HttpResponse(template.render(c), mimetype='text/html')


def incomplete_configuration(request):
    """Create an incomplete configuration error response."""
    if request.reason == 'missing_database':
        tmpl = MISSING_DATABASE_TEMPLATE
    elif request.reason == 'missing_keys':
        tmpl = MISSING_KEYS_TEMPLATE
    else:
        raise ValueError('Request has an unknown reason for incomplete configuration')

    return render_wizard_page(request, tmpl)


def save_keys(request):
    if request.method != 'POST':
        return HttpResponse('POST required to save keys', status=400, content_type='text/plain')

    # Find the keys inside the paste.
    paste = request.POST['keys']
    (csr_key, acc_key, acc_secret) = re.findall(r'\b\w{16}\b', paste)
    (csr_secret,) = re.findall(r'\b(?!Consumer)\w{8}\b', paste)

    # TODO: handle not finding all the keys?

    # Assume we want local settings in the CWD.
    local_settings_filename = os.path.abspath('local_settings.py')
    log = logging.getLogger('.'.join((__name__, 'save_keys')))
    log.debug('Saving keys into %r', local_settings_filename)

    key_settings = {
        'OAUTH_CONSUMER_KEY': csr_key,
        'OAUTH_CONSUMER_SECRET': csr_secret,
        'OAUTH_GENERAL_PURPOSE_KEY': acc_key,
        'OAUTH_GENERAL_PURPOSE_SECRET': acc_secret,
    }

    try:
        local_settings_file = open(local_settings_filename, 'r+')
        os.unlink(local_settings_filename)
        new_settings_file = open(local_settings_filename, 'w')
    except IOError:
        return render_wizard_page(request, MANUAL_SAVE_KEYS_TEMPLATE, local_settings=key_settings)

    def settings_line_for_match(mo):
        log.debug('Updating line with match %r', mo)
        key = mo.group(1)
        value = key_settings.get(key, '')
        return mo.expand(r'\1\2\3%s\3') % value

    for line in local_settings_file.xreadlines():
        line = re.sub(r'^(OAUTH_\w+)(\s*=\s*)([\'"])\3', settings_line_for_match, line)
        new_settings_file.write(line)

    new_settings_file.close()
    local_settings_file.close()
    return render_wizard_page(request, SAVED_KEYS_TEMPLATE)


BASE_TEMPLATE = """
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:at="http://www.sixapart.com/ns/at" id="sixapart-standard">
<head>
  <style type="text/css">
    html * { padding:0; margin:0; }
    body * * { padding:10px 20px; }
    body * * * { padding:0; }
    body { font:small sans-serif; }
    div#body>div { border-bottom:1px solid #ddd; }
    div#body { width: 500px; margin: 0 auto; }
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
    #banner {
        position: relative;
        height: 80px;
        background: #e0ebff url(/images/burst.png) no-repeat center bottom;
    }
    #logo {
        position: absolute;
        left: 215px;
        top: 45px;
        width: 70px;
        height: 70px;
        background: url(/images/typepad.png) no-repeat center center
    }
    #summary { display: none; }
    #explanation { background:#eee; }
    #instructions { background:#f6f6f6; padding-top: 30px }
    #instructions p { margin-bottom: 1em; }
    #instructions blockquote { margin-left: 2em; }
    #instructions a.arrow { text-decoration: none }
    #instructions textarea { width: 100%; height: 12em }
    #summary table { border:none; background:transparent; }
  </style>
</head>

<body>
<div id="body">

    <div id="banner">
        <div id="logo">&nbsp;</div>
    </div>

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
      </p>
        {% endblock %}
    </div>
</div>
</body>
</html>
"""

MISSING_DATABASE_TEMPLATE = """
{% extends base_template %}
{% block instructions %}

    <p>You seem to be <strong>missing a database</strong>. Try:</p>

    <blockquote><p><samp>python manage.py syncdb</samp></p></blockquote>

    <p>to initialize the database.</p>

    <p><button onclick="return document.location.reload()">Next &rarr;</button></p>

{% endblock %}
"""

MISSING_KEYS_TEMPLATE = """
{% extends base_template %}
{% block instructions %}

    <p>Your application <strong>needs TypePad API keys</strong> to talk to TypePad.</p>

    <p><big>
    <a href="http://www.typepad.com/account/access/api_key" target="_new">Get an application key</a>
    <a href="http://www.typepad.com/account/access/api_key" target="_new" class="arrow">&rarr;</a>
    </big></p>

    <p>Then paste <strong>all four parts</strong> of your key in below to save it:</p>

    <form method="post" action="/save_keys">
        <p><textarea name="keys"></textarea></p>
        <p><button>Save keys &rarr;</button></p>
    </form>

{% endblock %}
"""

SAVED_KEYS_TEMPLATE = """
{% extends base_template %}
{% block instructions %}

    <p>Your keys have been saved to your <samp>local_settings.py</samp> file. Let's see if this works!</p>

    <p><button onclick="window.location.href = '/'; return false">Continue &rarr;</button></p>

{% endblock %}
"""

MANUAL_SAVE_KEYS_TEMPLATE = """
{% extends base_template %}
{% block instructions %}

    <p>We couldn't save your keys to disk, so <strong>add these settings to your <samp>local_settings.py</samp> file</strong>:</p>

    <p><textarea>OAUTH_CONSUMER_KEY = '{{ local_settings.OAUTH_CONSUMER_KEY }}'
OAUTH_CONSUMER_SECRET = '{{ local_settings.OAUTH_CONSUMER_SECRET }}'
OAUTH_GENERAL_PURPOSE_KEY = '{{ local_settings.OAUTH_GENERAL_PURPOSE_KEY }}'
OAUTH_GENERAL_PURPOSE_SECRET = '{{ local_settings.OAUTH_GENERAL_PURPOSE_SECRET }}'</textarea></p>

    <p><button onclick="window.location.href = '/'; return false">Done &rarr;</button></p>

{% endblock %}
"""

