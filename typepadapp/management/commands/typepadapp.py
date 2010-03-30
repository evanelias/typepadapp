# Copyright (c) 2009-2010 Six Apart Ltd.
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
import sys

from django.core.management.commands import startapp
from django.core.management import CommandError


def copy_helper(style, app_or_project, name, directory, other_name='', base_path=None):
    """
    Copies either a Django application layout template or a Django project
    layout template into the specified directory.

    Copied from django.core.management.base.copy_helper; modified to support
    a ``base_path`` keyword argument which was sorely missing to allow this
    routine to be reusable for custom Django commands like ours. Also,
    our project/app template contains non .py files, so we need to copy
    those also (Django 1.1 diverged on this; 1.1's copy_helper only copies
    .py files).
    """
    # style -- A color style object (see django.core.management.color).
    # app_or_project -- The string 'app' or 'project'.
    # name -- The name of the application or project.
    # directory -- The directory to which the layout template should be copied.
    # other_name -- When copying an application layout, this should be the name
    #               of the project.
    import re
    other = {'project': 'app', 'app': 'project'}[app_or_project]
    if not re.search(r'^[_a-zA-Z]\w*$', name): # If it's not a valid directory name.
        # Provide a smart error message, depending on the error.
        if not re.search(r'^[_a-zA-Z]', name):
            message = 'make sure the name begins with a letter or underscore'
        else:
            message = 'use only numbers, letters and underscores'
        raise CommandError("%r is not a valid %s name. Please %s." % (name, app_or_project, message))
    top_dir = os.path.join(directory, name)
    try:
        os.mkdir(top_dir)
    except OSError, e:
        raise CommandError(e)

    # Determine where the app or project templates are. Use
    # django.__path__[0] because we don't know into which directory
    # django has been installed.
    if base_path is None:
        import django
        base_path = django.__path__[0]

    template_dir = os.path.join(base_path, 'conf', '%s_template' % app_or_project)

    for d, subdirs, files in os.walk(template_dir):
        relative_dir = d[len(template_dir)+1:].replace('%s_name' % app_or_project, name)
        if relative_dir:
            os.mkdir(os.path.join(top_dir, relative_dir))
        for i, subdir in enumerate(subdirs):
            if subdir.startswith('.'):
                del subdirs[i]
        for f in files:
            if f.endswith('.pyc') or f.endswith('.pyo') or f.endswith('$py.class'):
                continue
            path_old = os.path.join(d, f)
            path_new = os.path.join(top_dir, relative_dir, f.replace('%s_name' % app_or_project, name))

            replaces = {
                app_or_project: name,
                other: other_name,
            }
            duplicate_file(path_old, path_new, replaces=replaces)


def duplicate_file(path_old, path_new, replaces=None):
    """Duplicates one file as per the copy helper."""
    import shutil
    if replaces is None:
        replaces = {}

    fp_old = open(path_old, 'r')
    fp_new = open(path_new, 'w')
    content = fp_old.read()
    for name, value in replaces.items():
        content = content.replace('{{ %s_name }}' % name, value)
    fp_new.write(content)
    fp_old.close()
    fp_new.close()
    try:
        shutil.copymode(path_old, path_new)
        _make_writeable(path_new)
    except OSError:
        sys.stderr.write(style.NOTICE("Notice: Couldn't set permission bits on %s. You're probably using an uncommon filesystem setup. No problem.\n" % path_new))


def _make_writeable(filename):
    """
    Make sure that the file is writeable. Useful if our source is
    read-only.

    """
    import stat
    if sys.platform.startswith('java'):
        # On Jython there is no os.access()
        return
    if not os.access(filename, os.W_OK):
        st = os.stat(filename)
        new_permissions = stat.S_IMODE(st.st_mode) | stat.S_IWUSR
        os.chmod(filename, new_permissions)


def my_copy_helper(style, app_or_project, name, directory, other_name=''):
    # we're assuming typepadapp application is two directories above our
    # command module file.
    typeapp_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

    # Less than ideal; copy_helper doesn't lend itself to specifying
    # the source location to copy from, so we're tricking it by
    # temporarily changing the location of django to our typepadapp
    # application directory where it's app project template resides.
    copy_helper(style, app_or_project, name, directory, other_name='', base_path=typeapp_path)


class Command(startapp.Command):

    help = "Creates a TypePad Django app directory structure for the given app name in the current directory."

    def handle_label(self, app_name, directory=None, **options):
        helper = startapp.copy_helper
        startapp.copy_helper = my_copy_helper
        try:
            super(Command, self).handle_label(app_name, directory, **options)
        finally:
            startapp.copy_helper = helper
