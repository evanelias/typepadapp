#!/usr/bin/python

import os, site, sys

# Remember original sys.path.
prev_sys_path = list(sys.path)

# Add project base directory to python path
site.addsitedir(os.path.realpath(os.path.dirname(os.path.dirname(__file__))))

# Set django settings module environmental variable
os.environ['DJANGO_SETTINGS_MODULE'] = '{{ project_name }}.settings'

# If the VIRTUAL_ENV environmental veriable is set, add it to the python path
if 'VIRTUAL_ENV' in os.environ:
    site.addsitedir(os.environ['VIRTUAL_ENV'])

# Reorder sys.path so new directories at the front.
new_sys_path = []
for item in list(sys.path):
    if item not in prev_sys_path:
        new_sys_path.append(item)
        sys.path.remove(item)
sys.path[:0] = new_sys_path

# Instantiate WSGI handler
import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()
