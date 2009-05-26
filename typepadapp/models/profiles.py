from django.db import models
from typepadapp.models.users import User


class UserProfile(models.Model):
    """
        Abstract base class for a creating a custom local
        User profile for additional site-specific profile
        information.
        
        To create a local profile, just create your own local
        profile model that extends this one, and add it to your
        AUTH_PROFILE_MODULE setting.
    """
    # TypePad user XID, this field is required
    ## TODO how long does this need to be?
    user_id = models.CharField(max_length=100, unique=True, null=False, blank=False)

    @property
    def user(self):
        return User.get_by_id(self.user_id)

    class Meta:
        abstract = True
