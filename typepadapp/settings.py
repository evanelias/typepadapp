# Typepadapp application settings.
import os
import logging

TYPEPAD_COOKIES = {}

BATCH_REQUESTS = not os.getenv('TYPEPAD_BATCHLESS')

EVENTS_PER_PAGE = 25
COMMENTS_PER_PAGE = 50
MEMBERS_PER_WIDGET = 30

# Logging
LOG_FORMAT = '%(name)-20s %(levelname)-8s %(message)s'
LOG_LEVEL = logging.INFO
LOG_LEVELS = {
    'remoteobjects.http': logging.WARNING,
    'batchhttp.client': logging.WARNING,
    'typepad.oauthclient': logging.WARNING,
}