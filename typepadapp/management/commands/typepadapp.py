# Copyright (c) 2009 Six Apart Ltd.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# * Neither the name of Six Apart Ltd. nor the names of its contributors may
#   be used to endorse or promote products derived from this software without
#   specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

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
