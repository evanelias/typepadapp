import os

from django.core.management.commands import startapp
from django.core.management.base import copy_helper

def my_copy_helper(style, app_or_project, name, directory, other_name=''):
    # we're assuming typepadapp application is two directories above our
    # command module file.
    typeapp_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

    # Less than ideal; copy_helper doesn't lend itself to specifying
    # the source location to copy from, so we're tricking it by
    # temporarily changing the location of django to our typepadapp
    # application directory where it's app project template resides.
    import django

    orig_path = django.__path__
    django.__path__ = [typeapp_path]
    try:
        copy_helper(style, app_or_project, name, directory, other_name='')
    finally:
        django.__path__ = orig_path

class Command(startapp.Command):

    help = "Creates a TypePad Django app directory structure for the given app name in the current directory."

    def handle_label(self, app_name, directory=None, **options):
        startapp.copy_helper = my_copy_helper
        super(Command, self).handle_label(app_name, directory, **options)
        startapp.copy_helper = copy_helper
