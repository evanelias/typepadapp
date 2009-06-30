from django.conf.urls.defaults import *

handler500 = 'motion.views.handle_exception'
handler404 = 'motion.views.handle_not_found'

urlpatterns = patterns('',
    (r'^', include('motion.urls')),
    (r'^', include('typepadapp.urls')),
)
