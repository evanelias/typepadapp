from django import template
from django.utils.safestring import mark_safe
from django.utils.html import strip_tags


register = template.Library()

@register.filter
def morelink(entry, wordcount):
    """
    Display a 'continue reading...' link if the entry contains
    more words than the supplied wordcount.
    """
    content = strip_tags(entry.content)
    if template.defaultfilters.wordcount(content) > wordcount:
        more = '<br/><br/><a href="%s">continue reading...</a>' % entry.get_absolute_url()
        return mark_safe(more)
    return ''


@register.filter
def greaterthan(num1, num2):
    try:
        return int(num1) > int(num2)
    except:
        return False
