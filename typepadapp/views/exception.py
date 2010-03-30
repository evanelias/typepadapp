# Copyright (c) 2009-2010 Six Apart Ltd.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# * Neither the name of Six Apart Ltd. nor the names of its contributors may
#   be used to endorse or promote products derived from this software without
#   specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import logging
from django.http import HttpResponseServerError, HttpResponseNotFound
from django.template import RequestContext, loader

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
    content = loader.render_to_string('500.html', 
                                      context_instance=RequestContext(request))
    return HttpResponseServerError(content)

def page_not_found(request, *args, **kwargs):
    """
    Custom 404 handler for logging (non-debug mode only).
    """
    logging.warning('Page not found: %s' % request.path)
    content = loader.render_to_string('404.html',
                                      context_instance=RequestContext(request))
    return HttpResponseNotFound(content)
