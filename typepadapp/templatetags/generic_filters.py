from django.template import defaultfilters
from django import template
import re

register = template.Library()

@register.filter
def regex_search(s, pattern):
    """Finds if a pattern in the string."""
    return re.search(pattern, s)

@register.filter
def regex_starts_with(s, pattern):
    """Finds if a pattern is at the start of a string.

    Used for finding URL prefixes.
    """
    if re.search(pattern, s):
        return re.search(pattern, s).start() == 0
    return None

@register.filter
def split(s, delim):
    """Python string split."""
    return s.split(delim)

@register.filter
def truncatechars(value, length):
    """Truncates a string after a certain number of characters (length).

    Also appends '...' to show that the string is actually
    longer than displayed.
    """
    try:
        length = int(length)
    except ValueError: # Invalid literal for int().
        return value # Fail silently.
    if len(value) <= length:
        return value
    return value[:length] + '...'
