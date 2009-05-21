from django.conf.urls.defaults import *

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
