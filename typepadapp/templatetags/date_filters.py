import datetime, time
from gettext import ngettext
from django.utils.translation import ngettext
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
      (60 * 60 * 24 * 365, lambda n, d: preposition+defaultfilters.date(d, 'M j')+', '+defaultfilters.date(d, 'Y')), # 1 year+
      (60 * 60 * 24 * 7, lambda n, d: preposition+defaultfilters.date(d, 'M jS')), # 1 week+
      (60 * 60 * 24, lambda n, d: '%d %s' % (n // (60 * 60 * 24), ngettext('day', 'days', n // (60 * 60 * 24))+' ago')), # 1 day+
      (60 * 60, lambda n, d: '%d %s' % (n // (60 * 60), ngettext('hour', 'hours', n // (60 * 60))+' ago')), # 1 hour+
      (60 * 2, lambda n, d: '%d %s' % (n // 60, 'min ago')), # 2 minutes+
      (1, lambda n, d: 'just now!') # under 2 mins ago
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
def date_microformat(d):
    '''
        Microformat version of a date.
        2009-02-10T02:58:00+00:00 (ideal)
        2009-02-09T17:54:41.181868-08:00 (mine)
    '''
    if d is None:
        return None
    return d.isoformat()
