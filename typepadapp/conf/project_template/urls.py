from django.conf.urls.defaults import *
from typepadapp.urls import handler500, handler404

urlpatterns = patterns('',
    (r'^', include('motion.urls')),
    (r'^', include('typepadapp.urls')),
)
