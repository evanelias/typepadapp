import csv

from django import http
from django.contrib.auth import get_user

import typepad


def export_members(request):
    """ Export a list of all members of a group as a CSV file."""
    
    offset = 1
    typepad.client.batch_request()
    request.user = get_user(request)
    members = request.group.memberships.filter(start_index=offset, member=True)
    typepad.client.complete_batch()
    
    if not request.user.is_superuser:
        # just pretend this page doesn't exist
        raise http.Http404
    
    # convert to user list
    members = [member.source for member in members]
    ids = [member.id for member in members] # xids of members, not needed if cmp did user ids

    # wiggle room
    new_offset = len(members) - 4
    while new_offset > offset:
        # moooooare
        offset = new_offset
        typepad.client.batch_request()
        more = request.group.memberships.filter(start_index=offset, member=True)
        typepad.client.complete_batch()
        # stop if the result is an empty list
        if not more.entries:
            break
        # add members to list
        for m in more:
            if m.source.id not in ids: # remove dupes
                members.append(m.source)
                ids.append(m.source.id)
        new_offset = len(members) - 4

    response = http.HttpResponse(mimetype='text/csv')
    response['Content-Disposition'] = 'attachment; filename=membership.csv'

    writer = csv.writer(response)

    labels = ['xid', 'display name', 'about me', 'interests']
    writer.writerow(labels)

    for member in members:
        member_data = [member.id, member.display_name, member.about_me, ' '.join(member.interests)]
        row = []
        for item in member_data:
            if item:
                # csv pukes on unicode, convert to utf-8
                row.append(item.encode("utf-8"))
            else:
                row.append('')
        writer.writerow(row)

    return response
