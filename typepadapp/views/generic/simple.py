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

from django.template import loader, RequestContext
from django.http import HttpResponse, HttpResponsePermanentRedirect, HttpResponseGone
from django.contrib.auth import get_user

import typepad

def direct_to_template(request, template, extra_context=None, mimetype=None, **kwargs):
    """
    Render a given template with any extra URL parameters in the context as
    ``{{ params }}``.
    """
    if extra_context is None: extra_context = {}
    dictionary = {'params': kwargs}
    for key, value in extra_context.items():
        if callable(value):
            dictionary[key] = value()
        else:
            dictionary[key] = value
    c = RequestContext(request, dictionary)

    if not hasattr(request, 'user') or not request.user:
        typepad.client.batch_request()
        user = get_user(request)
        typepad.client.complete_batch()
        request.user = user

    c.update({'user': request.user, 'request':request})

    t = loader.get_template(template)
    return HttpResponse(t.render(c), mimetype=mimetype)
