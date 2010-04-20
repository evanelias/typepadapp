typepadapp Changelog
====================

1.1.3 (2010-04-20)
------------------

* Added a `UserProfile.get_profile()` method for finding someone's local profile model from a `UserProfile` instance.
* Made `Photo.save()` and `Audio.save()` methods raise appropriate exceptions when failing to upload a file.
* Changed the `Video.link` setter to create a new `VideoLink` instance when necessary.
* Added an `http_method` parameter to the `typepadapp.middleware.gp_signed_url()` helper function.


1.1.2 (2009-03-30)
------------------

* Updated for forward compatibility with the TypePad API.


1.1.1 (2009-12-16)
------------------

* Resolved some cache invalidation bugs around comment deletion.
* Fixed the HTTP status code for 500, 404 error handlers.


1.1 (2009-11-24)
----------------

* typepadapp now requires Django 1.1.1 or later.
* Support for front-end caching.
* Added support for cached Django templates.
* Added documentation of Django settings for typepadapp.
* Added additional signals to aid front-end caching and cache invalidation: asset_created, asset_deleted, favorite_created, favorite_deleted, member_joined, member_banned, member_unbanned (members of ``typepadapp.signals``).
* Added a 'refreshwsgi' Django management command to create or recreate the project app.wsgi script.
* The ``typepadapp.views.base.TypePadView.filter_object_list`` method now receives the Django request object.
* Relocation of 404, 500 error handlers from typepad-motion to typepadapp.
* Fix for error handling of video posts when TypePad returns a HTTP 400 or 500 error.
* Fix for 'typepadproject' and 'typepadapp' commands under Django 1.1 so all template files are processed (not just '.py' files).
* Fixed a bug that prevented issuing the 'post_save' signal for asset and comment posts.


1.0.2 (2009-10-12)
------------------

* Updated Django dependency for their security release.


1.0.1 (2009-10-02)
------------------

* Version bump for PyPi packaging issues.


1.0 (2009-09-30)
----------------

* Initial release.
