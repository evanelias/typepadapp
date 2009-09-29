DEBUG = True
TEMPLATE_DEBUG = DEBUG

FRONTEND_URL = 'http://127.0.0.1:8000'

# TypePad API access configuration.
OAUTH_CONSUMER_KEY           = ''
OAUTH_CONSUMER_SECRET        = ''
OAUTH_GENERAL_PURPOSE_KEY    = ''
OAUTH_GENERAL_PURPOSE_SECRET = ''

# Database configuration.
DATABASE_ENGINE = 'sqlite3'                # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
DATABASE_NAME = '{{ project_name }}.db'    # Or path to database file if using sqlite3.
DATABASE_USER = ''                         # Not used with sqlite3.
DATABASE_PASSWORD = ''                     # Not used with sqlite3.
DATABASE_HOST = ''                         # Set to empty string for localhost. Not used with sqlite3.
DATABASE_PORT = ''                         # Set to empty string for default. Not used with sqlite3.
