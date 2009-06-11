import os
import unittest
from xml.dom import Node
from xml.dom.minidom import parse

from django.template import Context, Template


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
