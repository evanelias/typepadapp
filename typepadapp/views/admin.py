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

import csv
import StringIO

from django import http
from django.conf import settings
from django.contrib.auth import get_user

import typepad
import typepadapp.forms
import typepadapp.templatetags.formfieldvalue


def export_members(request):
    """ Export a list of all members of a group as a CSV file."""
    
    response = http.HttpResponse(generate_members_csv(request), mimetype='text/csv')
    response['Content-Disposition'] = 'attachment; filename=membership.csv'
    return response


def generate_members_csv(request):
    """CSV file generator for member data."""

    # file-like obj for csv writing
    mfile = StringIO.StringIO()
    writer = csv.writer(mfile)

    # label header row
    labels = ['xid', 'display name', 'email', 'joined', 'gender', 'location', 'about me', 'homepage', 'interests']
    if settings.AUTH_PROFILE_MODULE:
        profile_form = typepadapp.forms.LocalProfileForm()
        for field in profile_form:
            labels.append(field.label)
    writer.writerow(labels)

    # start the download prompt!
    yield mfile.getvalue()

    # fetch typepad api data
    offset = 1
    typepad.client.batch_request()
    request.user = get_user(request)
    kwargs = {"start_index": offset, "member": True}
    if settings.FRONTEND_CACHING:
        kwargs['cache'] = False
    members = request.group.memberships.filter(**kwargs)
    typepad.client.complete_batch()

    # verify the user is an admin
    if request.user.is_superuser:

        # convert to user list
        ids = [member.target.id for member in members]

        # output csv
        mfile = get_members_csv(members)
        yield mfile.getvalue()

        # wiggle room
        new_offset = len(ids) - 4

        # more pages of members
        while new_offset > offset:

            offset = new_offset

            # fetch typepad api data
            typepad.client.batch_request()
            kwargs['start_index'] = offset
            more = request.group.memberships.filter(**kwargs)
            typepad.client.complete_batch()

            # stop if the result is an empty list
            if not more.entries:
                break

            # add members to list
            members = []
            for m in more:
                if m.target.id not in ids: # remove dupes
                    members.append(m)
                    ids.append(m.target.id)

            # output csv
            mfile = get_members_csv(members)
            yield mfile.getvalue()

            new_offset = len(ids) - 4


def get_members_csv(members):

    mfile = StringIO.StringIO()
    writer = csv.writer(mfile)

    for membership in members:
        member = membership.target

        member_types = membership.created
        join_date = None
        for member_type in member_types:
            if member_type == "tag:api.typepad.com,2009:Member":
                join_date = str(member_types[member_type])

        # member data from typepad
        member_data = [member.xid,
            member.display_name, member.email,
            join_date,
            member.gender, member.location, member.about_me,
            member.homepage, ', '.join(member.interests)]
        row = []
        for item in member_data:
            if item:
                # csv doesn't want unicode instances, so encode into str's
                row.append(item.encode("utf-8"))
            else:
                row.append('')

        # member data from local profile
        if settings.AUTH_PROFILE_MODULE:
            profile_form = typepadapp.forms.LocalProfileForm(instance=member.get_profile())
            for field in profile_form:
                value = typepadapp.templatetags.formfieldvalue.value_of_field(field)
                row.append(value)

        writer.writerow(row)

    return mfile
