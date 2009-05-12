from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter
def morelink(entry, wordcount):
    """
    Display a 'continue reading...' link if the entry contains
    more words than the supplied wordcount.
    """
    if template.defaultfilters.wordcount(entry.content) > wordcount:
        more = '<br/><br/><a href="%s">continue reading...</a>' % entry.get_absolute_url()
        return mark_safe(more)
    return ''