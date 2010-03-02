from django.conf.urls.defaults import *
from typepadapp.urls import handler500, handler404

urlpatterns = patterns('',
    (r'^', include('typepadapp.urls')),
    (r'^', include('motion.urls')),
)
