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

import logging

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
import httplib2

import typepad
from typepadapp.models import User


TYPEPAD_SESSION_KEY = '_auth_typepad_user_id'

log = logging.getLogger(__name__)


class TypePadBackend(object):
    """Custom User authentication backend for
    authenticating against the TypePad API.
    """

    def authenticate(self, oauth_client):
        """Verify authentication by calling get_self on the User.

        This will verify against the API endpoint for returning
        the authenticated user.
        """
        http = typepad.client
        http.clear_credentials()

        http.add_credentials(oauth_client.consumer, oauth_client.token)

        typepad.client.batch_request()
        u = User.get_self(http=http)
        try:
            typepad.client.complete_batch()
        except (User.Unauthorized, User.Forbidden):
            u = AnonymousUser()

        return u

    def get_user(self, user_id):
        """Return the authed TypePad user"""
        return User.get_by_id(user_id)


def authenticate(**credentials):
    backends = (TypePadBackend(),)

    for backend in backends:
        try:
            user = backend.authenticate(**credentials)
        except TypeError:
            continue
        if user is None:
            continue

        # Remember the backend in case we accidentally use a TypePadUser as a
        # conventional auth user.
        user.backend = '.'.join((backend.__module__, type(backend).__name__))
        return user

    # big fat nothing!
    return


def get_user(request):
    try:
        user_id = request.session[TYPEPAD_SESSION_KEY]
    except KeyError:
        pass
    else:
        return TypePadBackend().get_user(user_id) or AnonymousUser()

    return AnonymousUser()


def login(request, user):
    if TYPEPAD_SESSION_KEY in request.session:
        if request.session[TYPEPAD_SESSION_KEY] != user.id:
            # Make a new session like contrib.auth does in this case.
            request.session.flush()
    else:
        request.session.cycle_key()

    request.session[TYPEPAD_SESSION_KEY] = user.id
    if hasattr(request, 'typepad_user'):
        request.typepad_user = user

    # Does that typepad user map to a django user?
    try:
        from typepadapp.models.auth import UserForTypePadUser
    except ImportError:
        log.debug('Auth is not enabled, so not mapping to a django user')
        pass
    else:
        log.debug('Auth is enabled, so checking for user maps')
        import django.contrib.auth
        dj_user = None
        try:
            dj_user = django.contrib.auth.models.User.objects.filter(typepad_map__typepad_id=user.url_id)[0]
        except IndexError:
            log.debug('No map for that user; do we need to create one?')
            dj_user = _create_django_user(request, user)

        if dj_user is not None:
            log.debug('Found existing user map for %s to user #%d', user.url_id, dj_user.pk)
            if dj_user.is_active:
                dj_user.backend = 'django.contrib.auth.backends.ModelBackend'
                django.contrib.auth.login(request, dj_user)


def _create_django_user(request, tp_user):
    autocreate = getattr(settings, 'AUTO_CREATE_DJANGO_USERS', 'admin')
    if not autocreate:
        return
    autocreate = autocreate.lower()

    if autocreate not in ('none', 'admin', 'all'):
        raise ValueError('The AUTO_CREATE_DJANGO_USERS setting is set to an '
            ' unknown value %r; valid values are %r, %r and %r' % (autocreate,
            'none', 'admin', 'all'))

    if autocreate == 'none':
        log.debug('No one gets auto-created, especially not %s; not creating', tp_user.url_id)
        return

    # Is that TypePad user an admin?
    is_admin = False
    if log.isEnabledFor(logging.DEBUG):
        log.debug('Is our unmapped user one of admins %r?',
            [x.target.url_id for x in request.group.admins()])
    for admin_rel in request.group.admins():
        admin = admin_rel.target
        log.debug('Is user %s also %s?', tp_user.url_id, admin.url_id)
        if admin.url_id == tp_user.url_id:
            is_admin = True
            break

    if autocreate == 'admin' and not is_admin:
        log.debug('Only admins are auto-created and %s is not an admin; not creating', tp_user.url_id)
        return

    log.debug('Yes, creating a new User for tpuser %s', tp_user.url_id)

    # Create a new Django User for them.
    import django.contrib.auth
    dj_user = django.contrib.auth.models.User.objects.create_user(tp_user.url_id, tp_user.email)
    if is_admin:
        dj_user.is_staff = True
        dj_user.is_superuser = True
    dj_user.save()
    log.debug('Made a new user %r (%d)', dj_user, dj_user.pk)

    # And save a mapping for future use.
    from typepadapp.models.auth import UserForTypePadUser
    UserForTypePadUser(user=dj_user, typepad_id=tp_user.url_id).save()
    log.debug('Mapped new user %r to tpuser %s', dj_user, tp_user.url_id)

    return dj_user
