import os

from django.core.management.commands import startproject
from django.core.management.base import copy_helper

from typepadapp import my_copy_helper

class Command(startproject.Command):

    help = "Creates a TypePad Django project directory structure for the given project name in the current directory."

    def handle_label(self, project_name, **options):
        startproject.copy_helper = my_copy_helper
        super(Command, self).handle_label(project_name, **options)
        startproject.copy_helper = copy_helper
