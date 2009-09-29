Local Profiles
==============

TypePad applications support the use of *local profiles* for their TypePad
users. Local profiles are additional custom fields that are stored in the
project's own database, not in TypePad. While all TypePad profiles have the
same fields, individual TypePad app implementations can define their own local
profile data for their group members.


Defining the model
------------------

To store local profile data, use a Django model. The necessary functions for
linking profiles to users are provided by the
`typepadapp.models.profiles.UserProfile` model class, so you need only
subclass it and add the site's additional custom fields.

For example, if you're making the ``clientapp`` app, you would add a
`UserProfile` model to the ``clientapp.models`` module::

   from django.db import models

   import typepadapp.models.profiles

   class UserProfile(typepadapp.models.profiles.UserProfile):
       hiphop_name = models.CharField(max_length=80)

(Remember to have put ``clientapp`` in your ``INSTALLED_APPS``.) This model
will provide one "Hiphop name" field. See the Django documentation about
models [#models]_ for what fields and options are available to you.


Telling Django about the model
------------------------------

Once you've defined a local profile model, configure it in the settings as
your ``AUTH_PROFILE_MODULE``::

   AUTH_PROFILE_MODULE = 'clientapp.UserProfile'

See the Django documentation for ``AUTH_PROFILE_MODULE`` [#apm]_ for how to
use it. Note specifically that your ``AUTH_PROFILE_MODULE`` must be of the
form ``package.Class``, whereas your profile model is
``package.models.Class``. Your package must be a top-level app, and don't
include the word ``models``. (This is just how Django does it.)


Creating the database table
---------------------------

Because you added a new Django model, you'll have to create its table in the
database. Do that with the ``syncdb`` manager command::

   python manage.py syncdb

If you already have the table and modified the definition of the class, you'll
have to alter the table manually, as ``syncdb`` can only make new tables.


Customizing templates
---------------------

Once configured, a Django form called ``typepadapp.forms.UserProfileForm``
will be available for showing and editing the model content in templates. For
example, once defined, the Motion profile template will use it automatically.

See the Django documentation on forms [#forms]_ and model forms [#modelform]_
for how they work.


.. rubric:: Footnotes

.. [#models] `Models <http://docs.djangoproject.com/en/1.0/topics/db/models/>`__
.. [#apm] `User authentication in Django: Storing additional information about users <http://docs.djangoproject.com/en/1.0/topics/auth/#storing-additional-information-about-users>`_
.. [#forms] `Working with forms <http://docs.djangoproject.com/en/1.0/topics/forms/>`_
.. [#modelform] `Creating forms from models <http://docs.djangoproject.com/en/1.0/topics/forms/modelforms/>`_
