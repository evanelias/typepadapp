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

import datetime, time
from gettext import ngettext
from django.utils.translation import ngettext, ugettext as _
from django.template import defaultfilters
from django import template

register = template.Library()

@register.filter
def pithy_timesince(d, preposition=''):
    '''
        Concise timesince.
        Modified from Pownce pithy_timesince and django timesince.
    '''
    if d is None:
        return None
    chunks = (
      (60 * 60 * 24 * 365, lambda n, d: _('%(prep)s %(date)s') % { 'prep': preposition, 'date': defaultfilters.date(d, 'M j, Y') }), # 1 year+
      (60 * 60 * 24 * 7, lambda n, d: _('%(prep)s %(date)s') % { 'prep': preposition, 'date': defaultfilters.date(d, 'M jS') }), # 1 week+
      (60 * 60 * 24, lambda n, d: '%d %s' % (n // (60 * 60 * 24), ngettext('day ago', 'days ago', n // (60 * 60 * 24)))), # 1 day+
      (60 * 60, lambda n, d: '%d %s' % (n // (60 * 60), ngettext('hour ago', 'hours ago', n // (60 * 60)))), # 1 hour+
      (60 * 2, lambda n, d: '%d %s' % (n // 60, ngettext('minute ago', 'minutes ago', n // 60))), # 2 minutes+
      (1, lambda n, d: _('just now')) # under 2 mins ago
    )
    t = time.localtime()
    if d.tzinfo:
        tz = LocalTimezone(d)
    else:
        tz = None
    now = datetime.datetime(t[0], t[1], t[2], t[3], t[4], t[5], tzinfo=tz)
    # ignore microsecond part of 'd' since we removed it from 'now'
    delta = now - (d - datetime.timedelta(0, 0, d.microsecond))
    since = delta.days * 24 * 60 * 60 + delta.seconds

    for i, (seconds, label) in enumerate(chunks):
        count = since // seconds # truncated division
        if count != 0:
            break
    return label(since, d)

@register.filter
def is_relative(d):
    '''
        Filter to evaluate whether the given date is relative or not.
    '''
    if d is None:
        return False
    t = time.localtime()
    if d.tzinfo:
        tz = LocalTimezone(d)
    else:
        tz = None
    now = datetime.datetime(t[0], t[1], t[2], t[3], t[4], t[5], tzinfo=tz)
    # ignore microsecond part of 'd' since we removed it from 'now'
    delta = now - (d - datetime.timedelta(0, 0, d.microsecond))
    since = delta.days * 24 * 60 * 60 + delta.seconds
    # timestamp is one week or less old
    return since <= 60 * 60 * 24 * 7

@register.filter
def date_microformat(d):
    '''
        Microformat version of a date.
        2009-02-10T02:58:00+00:00 (ideal)
        2009-02-09T17:54:41.181868-08:00 (mine)
    '''
    if d is None:
        return None
    return d.isoformat()
