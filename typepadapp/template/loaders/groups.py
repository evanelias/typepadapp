from django.conf import settings
from django.template import TemplateDoesNotExist
import os, sys

def load_template_source(template_name, template_dirs=None):
    if settings.MULTIGROUP and hasattr(settings, 'group_host'):
        try:
            app = settings.APP_FOR_HOST[settings.group_host]
            mod = sys.modules[app]
            filepath = os.path.join(mod.__path__[0], 'templates',
                app, template_name)
            try:
                return (open(filepath).read().decode(settings.FILE_CHARSET),
                        filepath)
            except IOError:
                pass
        except KeyError:
            pass
    raise TemplateDoesNotExist, "Could not locate template %s" % template_name

load_template_source.is_usable = True
