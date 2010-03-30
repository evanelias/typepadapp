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

import os.path
from django.conf.urls.defaults import *

app_path = os.path.dirname(__file__)
media_dir = os.path.join(app_path, 'static')

handler500 = 'typepadapp.views.exception.server_error'
handler404 = 'typepadapp.views.exception.page_not_found'

# auth pages
urlpatterns = patterns('typepadapp.views.auth',
    url(r'^login/?$', 'login', name='login'),
    url(r'^register/?$', 'register', name='register'),
    url(r'^authorize/?$', 'authorize', name='authorize'),
    url(r'^logout/?$', 'logout', name='logout'),
    url(r'^synchronize/?$', 'synchronize', name='synchronize'),
)

urlpatterns += patterns('typepadapp.views.admin',
    url(r'^admin/export/members/?$', 'export_members', name='export_members'),
)

urlpatterns += patterns('',
    url(r'^static/typepadapp/(?P<path>.*)/?$', 'django.views.static.serve',
        kwargs={ 'document_root': media_dir }),
)
