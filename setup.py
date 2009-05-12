#!/usr/bin/env python
from distutils.core import setup
setup(
    name='typepadapp',
    version='1.0',
    description='Base for TypePad cloud apps',
    author='Six Apart',
    author_email='python@sixapart.com',
    url='http://code.sixapart.com/svn/typepadapp/',

    packages=['typepadapp'],
    provides=['typepadapp'],
    requires=['Django(>=1.0.2)', 'typepad'],
)
