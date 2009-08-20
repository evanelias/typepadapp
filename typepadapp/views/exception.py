import logging
from django import http
from django.shortcuts import render_to_response
from django.template import RequestContext


def server_error(request, *args, **kwargs):
    """
    Custom exception handler for exception logging
    (non-debug mode only).
    """
    # Get the latest exception from Python system service
    import sys
    exception = sys.exc_info()[0]

    # Use  Python logging module to log the exception
    # For more information see:
    # http://docs.python.org/lib/module-logging.html
    logging.error('Uncaught exception got through, rendering 500 page.')
    logging.exception(exception)

    return render_to_response('500.html', {
    }, context_instance=RequestContext(request))


def page_not_found(request, *args, **kwargs):
    """
    Custom 404 handler for logging (non-debug mode only).
    """
    logging.warning('Page not found: %s' % request.path)
    return render_to_response('404.html', {
    }, context_instance=RequestContext(request))