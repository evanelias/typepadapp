from django.conf.urls.defaults import *

handler500 = 'motion.views.handle_exception'

urlpatterns = patterns('',
    (r'^', include('motion.urls')),
    (r'^', include('typepadapp.urls')),
)
