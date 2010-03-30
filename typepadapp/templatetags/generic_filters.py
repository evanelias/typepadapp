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

import re

from django import template
from django.utils.safestring import mark_safe

import feedparser


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


class Sanitizer(feedparser._HTMLSanitizer):

    nul_re = re.compile(r'\x00')
    comma_decimal_entity_re = re.compile(r'&#0*58[^0-9]')
    comma_hex_entity_re = re.compile(r'&#x0*3[Aa][^a-fA-F0-9]')
    space_re = re.compile(r'\s+')
    nonscheme_character_re = re.compile(r'[^a-zA-Z0-9\+]')
    ends_in_script_re = re.compile(r'script$')
    has_numeric_entity_re = re.compile(r'&#')

    def feed(self, value):
        value = re.sub(self.nul_re, '', value)
        feedparser._HTMLSanitizer.feed(self, value)

    def is_safe_href(self, href):
        href = re.sub(self.nul_re, '', href)
        href = re.sub(self.comma_decimal_entity_re, ':', href)
        href = re.sub(self.comma_hex_entity_re, ':', href)
        if ':' not in href:
            return True

        scheme = href.split(':', 1)[0]
        scheme = re.sub(self.space_re, '', scheme)
        if (re.search(self.nonscheme_character_re, scheme)
            or re.search(self.ends_in_script_re, scheme)
            or re.search(self.has_numeric_entity_re, scheme)):
            return False

        return True

    def normalize_attrs(self, attr):
        attr = feedparser._HTMLSanitizer.normalize_attrs(self, attr)
        attr = [(k, v) for k, v in attr
                if k not in ('href', 'src', 'dynsrc')
                    or self.is_safe_href(v)]
        return attr


@register.filter
def sanitizetags(value):
    s = Sanitizer('utf-8')
    s.feed(value)
    data = s.output().strip().replace('\r\n', '\n')
    return mark_safe(data)
