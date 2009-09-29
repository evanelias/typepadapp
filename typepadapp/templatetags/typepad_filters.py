# Copyright (c) 2009 Six Apart Ltd.
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
