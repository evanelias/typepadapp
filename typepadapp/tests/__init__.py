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

import cgi
import os
import unittest
from urllib import urlencode, quote
import urlparse
from xml.dom import Node
from xml.dom.minidom import parse

from django.conf import settings
from django.template import Context, Template
from oauth import oauth


class SanitizeTestsMeta(type):

    def __new__(cls, name, bases, attr):
        cls.add_feedparser_tests(attr)
        cls.add_mt_tests(attr)
        return type.__new__(cls, name, bases, attr)

    @classmethod
    def add_feedparser_tests(cls, attr):
        testdir = os.path.dirname(__file__)
        testpath = os.path.join(testdir, 'feedparser')
        for filename in os.listdir(testpath):
            # Only test with one set of tests.
            if not filename.startswith('entry_content_'):
                continue
            if not filename.endswith('.xml'):
                continue

            # Don't generate a test if we already have one by that name.
            testname = '_'.join(('test_feedparser', filename[14:].split('.', 1)[0]))
            if testname in attr:
                continue

            filepath = os.path.join(testpath, filename)

            def tester(filepath):
                def test(self):
                    self.run_feedparser_test(filepath)
                test.__name__ = testname
                return test

            attr[testname] = tester(filepath)

    @classmethod
    def add_mt_tests(cls, attr):
        mt_tests = attr.get('mt_tests', {})
        for key, value in mt_tests.iteritems():
            testname = '_'.join(('test_mt', key))
            if testname in attr:
                continue

            def tester(given, expected):
                def test(self):
                    self.run_test(given, expected)
                test.__name__ = testname
                return test

            attr[testname] = tester(*value)


class SanitizeTests(unittest.TestCase):

    __metaclass__ = SanitizeTestsMeta

    template = Template(
        '{% load generic_filters %}{% autoescape off %}'
        '{{ testcode|sanitizetags }}{% endautoescape %}'
    )

    mt_tests = {
        'unclosed_script': (
            '<script src="evil.js">',
            '',
        ),
        'strip_onclick': (
            '<a href="foo.html" onclick="runEvilJS()">kittens</a>',
            '<a href="foo.html">kittens</a>',
        ),
        'strip_onmouseover': (
            '<img onmouseover="killComputer()" src="foo.jpg">',
            '<img src="foo.jpg" />',
        ),
        'strip_javascript_href': (
            """<a href="javascript:alert('xxx')">boo</a>""",
            """<a>boo</a>""",
        ),
        'strip_js_href_with_encoded_lf': (
            """<a href="jav&#x0D;ascript:alert('xxx')">boo</a>""",
            """<a>boo</a>""",
        ),
        'preserve_javascript_filename': (
            '<a href="java&#x20;script.html">boo</a>',
            '<a href="java&#x20;script.html">boo</a>',
        ),
        'strip_js_href_with_interrupted_entity': (
            """<a href="javascript&#5\x008;alert('boo')">click</a>""",
            """<a>click</a>""",
        ),
        'strip_style_with_expression': (
            """<p><i style="x:expression:alert('xss')""",
            """<p>""",
        ),
        'strip_js_href_with_lf': (
            """<a href='\njavascript:alert(123)'>boo</a>""",
            """<a>boo</a>""",
        ),
    }

    def run_test(self, given, expected):
        # Build our testing template with the given HTML.
        context = Context({'testcode': given})
        built = self.template.render(context)

        # Check that the result is sanitized.
        self.assertEquals(built, expected)

    def run_feedparser_test(self, filepath):
        # Read the file normally to find what we expect.
        testfile = file(filepath)
        for x in testfile.xreadlines():
            if x.lstrip().startswith('Expect:'):
                expected = eval(x.split('==', 1)[1])
                break

        # Parse the document to get the test HTML out.
        testfile.seek(0)
        testdoc = parse(testfile)
        content = testdoc.getElementsByTagName('content')[0]
        content.normalize()
        testcode = ''.join([n.data for n in content.childNodes
                            if n.nodeType == Node.TEXT_NODE])

        self.run_test(testcode, expected)

    # These feedparser tests are about sanitizing content when the HTML is
    # encoded differently in the XML, so don't bother doing them.
    def test_feedparser_script_base64(self):
        pass

    def test_feedparser_script_inline(self):
        pass

    def test_feedparser_script_cdata(self):
        pass


class OAuthTests(unittest.TestCase):

    def build_oauth_url(self, callback_url):
        consumer = oauth.OAuthConsumer('dcca1df94b730d5c883bf29841a87b9a', 'y2t81yvi')
        token = oauth.OAuthToken('CstxlJQb9xx7zs0k', 'zlYiYGJcYO9Kn7HK')
        req = oauth.OAuthRequest.from_consumer_and_token(
            consumer,
            token=token,
            http_method='GET',
            http_url='http://example.com/',
            parameters=dict(callback_url=callback_url),
        )
        req.sign_request(oauth.OAuthSignatureMethod_HMAC_SHA1(), consumer, token)
        return req.to_url()

    def cb_from_url(self, oauth_url):
        parts = list(urlparse.urlparse(oauth_url))
        queryargs = cgi.parse_qs(parts[4], keep_blank_values=True)
        queryargs = dict([(k, v[0]) for k, v in queryargs.iteritems()])
        return queryargs['callback_url']

    def assertCallback(self, cb, reason=None):
        oauth_url = self.build_oauth_url(cb)
        if quote(cb, safe='') not in oauth_url:
            self.fail(reason)  # quoted cb url is not in oauth url
        if not cb == self.cb_from_url(oauth_url):
            self.fail(reason)  # cb url doesn't decode from oauth url

    def test_callback_url_encoding(self):
        self.assertCallback('moose', 'simple string (not an URL) encodes right')
        self.assertCallback('http://test.example.com/', 'simple url encodes right')
        self.assertCallback('http://test.example.com/?asfdasf=xy', 'url with query args encodes right')
        self.assertCallback('http://test.example.com/?next=http%3A%2F%2Ftest.example.com%2F%3Fawesome/',
            'url with encoded URL for a query arg encodes right')

        params = {
            'callback_nonce': 'awesomeface',
            'callback_next':  'http://test.example.com/some/full/request/?hi=a&param=here',
        }
        cb_url = '%s?%s' % ('http://test.example.com/', urlencode(params))
        self.assertCallback(cb_url, 'url with query encoded with urllib.urlencode encodes right')
