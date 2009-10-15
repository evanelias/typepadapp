# Django settings for {{ project_name }} project.

# Import defaults from motion settings
import os
import logging
from motion.settings import *

# Setup template caching
from typepadapp import cached_templates
cached_templates.setup()

DEBUG = False

ROOT_DIR = os.path.split(__file__)[0]
PROJECT_DIR = os.path.basename(os.path.dirname(__file__))

MEDIA_ROOT = os.path.join(ROOT_DIR, 'static')

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

# Make this unique, and don't share it with anybody.
SECRET_KEY = ''

ROOT_URLCONF = '{{ project_name }}.urls'

THEME = 'motion'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.

    # Add file system path(s) to custom templates.
)

INSTALLED_APPS += (
)

# Import a local settings file
# Create a local_settings.py to override any settings in this file
# (such as DEBUG) on your local machine.
try:
    from local_settings import *
    logging.info("also using settings from '%s.local_settings'" % PROJECT_DIR)
except ImportError:
    pass

if 'TEMPLATE_DEBUG' not in locals():
    TEMPLATE_DEBUG = DEBUG

if DEBUG:
    LOG_LEVEL = logging.DEBUG
