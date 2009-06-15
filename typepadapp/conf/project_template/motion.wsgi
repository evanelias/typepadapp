#!/usr/bin/python

import os, site

# Add project base directory to python path
site.addsitedir(os.path.realpath(os.path.dirname(os.path.dirname(__file__))))

# Set django settings module environmental variable
os.environ['DJANGO_SETTINGS_MODULE'] = '{{ project_name }}.settings'

# If the VIRTUAL_ENV environmental veriable is set, add it to the python path
if 'VIRTUAL_ENV' in os.environ:
    site.addsitedir(os.environ['VIRTUAL_ENV'])

# Instantiate WSGI handler
import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()
