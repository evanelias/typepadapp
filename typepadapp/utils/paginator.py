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

from django.core.paginator import Paginator, Page, PageNotAnInteger, EmptyPage

class FinitePaginator(Paginator):
    """Paginator for cases when the list of items is already finite.

    A good example is a list generated from an API call. This is a subclass of
    Paginator. The object_list should provide a ``count`` method so we know
    how many items exist.

    To accurately determine if the next page exists, a FinitePaginator MUST be
    created with an object_list_plus that may contain more items than the
    per_page count. Typically, you'll have an object_list_plus with one extra
    item (if there's a next page). You'll also need to supply the offset from
    the full collection in order to get the page start_index.

    This is a very silly class but useful if you love the Django pagination
    conventions.
    """

    def __init__(self, object_list, per_page, offset=None, allow_empty_first_page=True, link_template='/page/%d/'):
        orphans = 0 # no orphans
        super(FinitePaginator, self).__init__(object_list, per_page, orphans, allow_empty_first_page)
        # bonus links
        self.offset = offset
        self.link_template = link_template

    def validate_number(self, number):
        """Validates the given 1-based page number."""
        try:
            number = int(number)
        except ValueError:
            raise PageNotAnInteger('That page number is not an integer')
        if number < 1:
            raise EmptyPage('That page number is less than 1')
        return number

    def page(self, number):
        """Returns a Page object for the given 1-based page number."""
        number = self.validate_number(number)
        return FinitePage(self.object_list, number, self)

class FinitePage(Page):
    def next_link(self):
        """URL for the next page of results (or None)."""
        if self.has_next():
            return self.paginator.link_template % (self.number + 1)
        return None

    def previous_link(self):
        """URL for the previous page of results (or None)."""
        if self.has_previous():
            return self.paginator.link_template % (self.number - 1)
        return None

    def start_index(self):
        """Returns the 1-based index of the first object on this page,
        relative to total objects in the paginator.
        """
        offset = self.paginator.offset
        if offset is None:
            raise ValueError("Can't determine start index of paginator with no offset")
        return offset
