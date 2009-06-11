#!/usr/bin/env python
from setuptools import setup
setup(
    name='typepadapp',
    version='1.0',
    description='Base for TypePad cloud apps',
    author='Six Apart',
    author_email='python@sixapart.com',
    url='http://code.sixapart.com/svn/typepadapp/',

    packages=['typepadapp'],
    provides=['typepadapp'],
    include_package_data=True,
    zip_safe=False,
    requires=['Django(>=1.0.2)', 'typepad', 'FeedParser'],
)
