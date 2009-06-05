import os.path
from django.conf.urls.defaults import *

app_path = os.path.dirname(__file__)
media_dir = os.path.join(app_path, 'static')

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