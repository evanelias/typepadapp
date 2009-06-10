# Django settings for {{ project_name }} project.

# Import defaults from motion settings
import os
import logging
from motion.settings import *

DEBUG = False

ROOT_DIR = os.path.split(__file__)[0]
PROJECT_DIR = os.path.basename(os.path.dirname(__file__))

MEDIA_ROOT = os.path.join(ROOT_DIR, 'static')

TEMPLATE_DIRS = (
    ROOT_DIR,
)

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

# Make this unique, and don't share it with anybody.
SECRET_KEY = ''

ROOT_URLCONF = '{{ project_name }}.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
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

# Configure these based on settings.py and/or local_settings.py
TYPEPAD_API_KEY = OAUTH_CONSUMER_KEY

OAUTH_CALLBACK_URL = '%s/authorize/' % FRONTEND_URL

if 'TEMPLATE_DEBUG' not in locals():
    TEMPLATE_DEBUG = DEBUG

if DEBUG:
    LOG_LEVEL = logging.DEBUG
