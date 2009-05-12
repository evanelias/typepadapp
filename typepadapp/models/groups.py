import typepad
from typepadapp.utils.cached import cached_property

class Group(typepad.Group):

    admin_list = []

    def admins(self):
        return self.admin_list
