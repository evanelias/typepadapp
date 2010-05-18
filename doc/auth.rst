=======================================================
Using Django authentication and admin with `typepadapp`
=======================================================

You can use Django's authentication system with `typepadapp` to let you sign in users.

The `typepadapp` app provides plain authentication for TypePad accounts. These accounts are required to join your TypePad group in order to sign in for the first time, after which they are available as your group's `memberships` list. These users are available in your application code as `TypePadUser` instances.

As your TypePad application is also a Django app, you can use Django's authentication system to sign in local users too. This is most useful for having local administrator accounts that can operate other Django apps (such as `flatpages`_) that aren't aware of TypePad.

.. _flatpages: http://docs.djangoproject.com/en/1.1/ref/contrib/flatpages/

Enabling auth and the admin
===========================

Your other Django apps may depend on you being able to use the Django admin app. To use the admin, you can enable regular Django user authentication alongside TypePad authentication.

Add the apps
------------

To use Django users and the admin, you'll need to add the auth and admin apps to your project by adding them to the ``INSTALLED_APPS`` setting in your project's ``settings.py`` file. You'll also need to enable the `auth` app's model backend and middleware, by adding ``AUTHENTICATION_BACKENDS`` and ``MIDDLEWARE_CLASSES`` settings. If you've made no other modifications, that part of your ``settings.py`` file will look like this::

   INSTALLED_APPS += (
       'django.contrib.auth',
       'django.contrib.admin',
   )

   AUTHENTICATION_BACKENDS = (
      'django.contrib.auth.backends.ModelBackend',
   )

   MIDDLEWARE_CLASSES += (
      'django.contrib.auth.middleware.AuthenticationMiddleware',
   )

Run ``syncdb``
--------------

Once you've added the authentication app to your project, you'll need to run a ``syncdb`` to add the authentication app's tables to your database. It will ask you if you want to make a new superuser account::

   You just installed Django's auth system, which means you don't have any superusers defined.
   Would you like to create one now? (yes/no):

If you'd like to have a superuser account besides your TypePad group's admin accounts, answer "yes" and enter the account information.

Add the admin to your urlconf
-----------------------------

To enable the admin interface, you'll also need to add it to your urlconf. In your project's ``urls.py`` file, set up the admin app `as you would in a regular Django project`_. If you've made no other modifications to your project's ``urls.py`` file, it will look like this::

   from django.contrib import admin
   admin.autodiscover()

   urlpatterns = patterns('',
       (r'^', include('typepadapp.urls')),
       (r'^', include('motion.urls')),
       (r'^admin/', include(admin.site.urls)),
   )

.. _as you would in a regular Django project: http://docs.djangoproject.com/en/dev/intro/tutorial02/#activate-the-admin-site

Your project should then let you use the admin interface at ``/admin/`` on your site. On your site's home page, sign out and back in with a TypePad account that is a group admin, and you'll be automatically signed in to the admin site.

Using TypePad users in your app
===============================

When viewers are signed in with TypePad accounts, their accounts are available in your views and templates. Use ``request.typepad_user`` in a view and ``typepad_user`` in a template to get the associated `TypePadUser` instance.

If a viewer is also signed in as a local Django user, that account is available as a `django.contrib.auth.models.User` instance from ``request.user`` in a view or ``user`` in a template. This is how Django apps normally work, so other Django apps that aren't aware of TypePad should find your local user instances without modification.

If you use other Django apps that aren't aware of TypePad, they may think you're signed out when you are signed in as a TypePad user, but not signed in as a local user. You'll need to configure your views or design your site to account for that.

Creating local users for TypePad users
--------------------------------------

`typepadapp` provides several options for creating local users from your TypePad users. Choose which behavior you want by setting the `AUTO_CREATE_DJANGO_USERS` setting in your Django ``settings.py``. There are three choices:

* ``'admin'``, the default setting, creates local Django users when an administrator of your TypePad group signs in. Usually the only administrator of a TypePad group is the developer who created the application, so this setting allows only you the developer to sign in as a local user.
* ``'none'`` makes `typepadapp` create no new local users. If you need to add a local account, you'll have to create it manually through the Django admin with a local superuser account.
* ``'all'`` makes a new local Django user for every TypePad user who signs in. Only use this setting if you're using a Django app that provides functionality to readers of your site, but requires readers to register local Django accounts.

Local Django users created by `typepadapp` have no passwords; they can only sign in by using their TypePad accounts.

Group admins vs local superusers
--------------------------------

When the admins of your configured group sign in, the local accounts `typepadapp` creates for them are marked as local superuser accounts. These superuser accounts can use the admin to edit any local content accessible with the Django admin. (If you don't want your TypePad group's administrators to have local superuser access, disable local user creation by setting `AUTO_CREATE_DJANGO_USERS` to ``'none'``.)

You can use the same system to grant privileged local access to another TypePad user who has joined your group. Create a new local `User` account through the admin, then add a `UserForTypePadUser` mapping for it. Put the user's TypePad user `url_id` in the "TypePad ID" field. This TypePad user ID looks like::

   6p00d83451ce6b69e2

and can be found in the API responses related to that user. Once the `UserForTypePadUser` mapping is created, that TypePad user will be signed in as the associated local user when they sign in with their TypePad account—so you can make them a local superuser by making their local user account a local superuser manually.
