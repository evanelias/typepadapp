# Create your URLs here.

from django.conf.urls.defaults import *
import os.path

app_path = os.path.dirname(__file__)
app_dir = os.path.basename(app_path)
theme_dir = os.path.join(app_path, 'static', 'theme')

urlpatterns = patterns('%s.views' % app_dir,
    # put your custom views here
)

# Appends a static url for your theme
urlpatterns += patterns('',
    url(r'^static/themes/%s/(?P<path>.*)/?$' % app_dir, 'django.views.static.serve',
        kwargs={ 'document_root': theme_dir }),
)
