from django import forms
from django.conf import settings
from django.db import models


if settings.AUTH_PROFILE_MODULE:
    auth_profile_module = models.get_model(*settings.AUTH_PROFILE_MODULE.split('.'))

    class UserProfileForm(forms.ModelForm):
        """A form for editing a local user profile."""

        class Meta:
            model = auth_profile_module
            exclude = ('user_id',)
