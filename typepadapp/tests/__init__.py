import os
import unittest
from xml.dom import Node
from xml.dom.minidom import parse

from django.template import Context, Template


class SanitizeTestsMeta(type):

    def __new__(cls, name, bases, attr):
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

        return type.__new__(cls, name, bases, attr)


class SanitizeTests(unittest.TestCase):

    __metaclass__ = SanitizeTestsMeta

    template = Template(
        '{% load generic_filters %}{% autoescape off %}'
        '{{ testcode|sanitizetags }}{% endautoescape %}'
    )

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

        # Build our testing template with the given HTML.
        context = Context({'testcode': testcode})
        built = self.template.render(context)

        # Check that the result is sanitized.
        self.assertEquals(built, expected)

    # These feedparser tests are about sanitizing content when the HTML is
    # encoded differently in the XML, so don't bother doing them.
    def test_feedparser_script_base64(self):
        pass

    def test_feedparser_script_inline(self):
        pass

    def test_feedparser_script_cdata(self):
        pass
