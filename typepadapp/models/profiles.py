from django.db import models
from typepadapp.models import User


class UserProfile(models.Model):
    '''
        Custom local User profile for additional site-specific
        profile information.
    '''
    # TypePad user XID, this field is required
    ## TODO how long does this need to be?
    user_id = models.CharField(max_length=100, unique=True, null=False, blank=False)

    # site-specific fields
    #favorite_band = models.CharField(max_length=100, blank=True)
    #favorite_cheese = models.CharField(max_length=100, blank=True)
    #lucky_number = models.IntegerField()

    @property
    def user(self):
        return User.get_user(self.user_id)

    class Meta:
        abstract = True
