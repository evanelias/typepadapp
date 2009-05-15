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
