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
        ## TODO should this holler if you haven't defined the offset?
        return self.paginator.offset
