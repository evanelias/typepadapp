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
def userpicbywidth(asset, width):
    try:
        return asset.links['rel__avatar'].link_by_width(int(width))
    except:
        return None


@register.filter
def enclosurebywidth(asset, width):
    try:
        return asset.links['rel__enclosure'].link_by_width(int(width))
    except:
        return None


@register.filter
def enclosurebysize(asset, size):
    try:
        return asset.links['rel__enclosure'].link_by_size(int(size))
    except:
        return None


@register.filter
def enclosurebymaxwidth(asset, width):
    try:
        return asset.links['rel__enclosure']['maxwidth__%d' % int(width)]
    except:
        return None


@register.filter
def greaterthan(num1, num2):
    try:
        return int(num1) > int(num2)
    except:
        return False
