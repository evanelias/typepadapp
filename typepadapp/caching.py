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

import logging
from django.core.cache import cache

import typepad
from typepadapp.debug_middleware import RequestStatTracker

log = logging.getLogger('typepadapp.cache')


class CachingCallback(object):

    """A callback class used for cacheable subrequests.

    """

    def __init__(self, promise):
        self.promise = promise

    def __call__(self, *args, **kwargs):
        """When invoked as a callable, pass through control to
        the ``_cache_callback`` method of the promise object held."""

        self.promise._cache_callback(*args, **kwargs)

    def is_cached(self):
        """Yields a boolean result indicating if the subrequest in context can
        be satisfied from the cache."""
        return self.promise._deliver_from_cache()


class CachingTypePadClient(typepad.TypePadClient):

    """A TypePadClient subclass that is aware of front-end caching.

    When ``complete_batch`` is executed, this client will weed out any
    subrequests that can be provided from the cache. If any remain,
    a normal batch request is issued.

    """

    def complete_batch(self):
        # check to see if we can provide this from the cache
        requests = []
        for request in self.batchrequest.requests:
            cb = request.callback
            if not cb.alive():
                continue
            if isinstance(request, RequestStatTracker):
                # special case for RequestStatTracker, which
                # holds the actual originating callback in this
                # attribute.
                cb = cb.orig_callback
            if hasattr(cb, 'callback'):
                callback = cb.callback()
                if isinstance(callback, CachingCallback):
                    if callback.is_cached():
                        continue
            requests.append(request)

        self.batchrequest.requests = requests
        super(CachingTypePadClient, self).complete_batch()


class CachedTypePadLinkPromise(object):

    """A caching class for wrapping a TypePad `Link` field of a `ListObject`
    endpoint.

    Instances behave like the wrapped `ListObject` instance, and keeps track
    of any ranged requests issued using the `filter` method. A ``callback``
    parameter is made available to the `get` method to either cause the
    subrequest to be pre-empted (and delivered from cache) or causes the cache
    to populate with an API response.

    """

    def __init__(self, link, obj, type=None, **kwargs):
        self._inst = None
        self._link = link
        self._start = 1
        self._end = 51
        self._id_cache = None
        self._item_cache_key_pattern = None

        # ie: objectcache:Event:xid
        self._item_cache_key_pattern = ":".join(
            ["objectcache", self._link.cls.entries.fld.cls.__name__, "%s"])

        kwargs['callback'] = CachingCallback(self)
        self._inst = self._link.__get__(obj, type, **kwargs)
        self._inst._cache_callback = kwargs['callback']

    def _deliver_from_cache(self):
        """Attempts to provide the `ListObject` data from the cache.

        When a cached value is unavailable, returns ``False``; otherwise,
        populates the instance and returns ``True``.

        """

        cache_key = self.cache_key
        ids = cache.get(cache_key)

        start = self._start
        end = self._end
        items = None

        if ids is not None:
            items = []

            if ids[0] > 0:
                if end > ids[0] + 1:
                    end = ids[0] + 1

                subset = ids[start:end]
                itemkeys = []

                # if one of our elements is empty, don't bother building
                # list of ids; this cache is invalid
                if None not in subset:
                    for id in subset:
                        itemkeys.append(self._item_cache_key_pattern % id)

                if len(itemkeys) > 0:
                    itemdict = cache.get_many(itemkeys)
                    for key in itemkeys:
                        if itemdict.get(key) is None:
                            items = None
                            log.debug("cache partial miss for key %s" % cache_key)
                            break
                        item = itemdict[key]
                        if hasattr(item, 'object'):
                            # for things like Event objects that have an embedded object
                            # that has a cache_key, cache that also
                            obj = item.object
                            if hasattr(obj, 'cache_key'):
                                object_key = obj.cache_key
                                if cache.add(object_key, None, 1) > 0:
                                    log.debug("cache partial miss due to missing object reference %s for key %s" % (object_key, cache_key))
                                    cache.delete(object_key)
                                    items = None
                                    break
                        items.append(itemdict[key])
                else:
                    log.debug("cache subset miss for key %s; ids[0] %d, start %d, end %d" % (cache_key, ids[0], start, end))

            if (items is not None) and ((len(items) > 0) or (ids[0] == 0)):
                log.debug("cache hit for key %s" % cache_key)
                l = typepad.ListObject()
                l._delivered = True
                l.entries = items
                l.start_index = start
                l.total_results = ids[0]
                self._inst = l
                return True
        else:
            log.debug("cache key miss for key %s" % cache_key)

        return False

    def _cache_callback(self, *args, **kwargs):
        """Callback used to populate the cache from an API response.

        It will create 1 key (with a name of ``listcache:URL``, where
        ``URL`` is the endpoint that was retrieved) assigned with an array
        of TypePad identifiers that comprise the list. It also populates
        the cache with each individual object (using a key of
        ``objectcache:OBJECT_TYPE:OBJECT_ID``).

        """

        del self._inst._cache_callback

        self._inst.update_from_response(*args, **kwargs)
        ids = self._id_cache or []

        # _start is None or 0, we don't care; start-index can't be less than 1
        start = self._start
        end = self._end
        while len(ids) <= end:
            ids.append(None)

        ids[0] = self._inst.total_results
        idx = start
        for item in self._inst.entries:
            item_key = item.cache_key
            log.debug("setting key %s" % item_key)
            if hasattr(item, 'object'):
                # for things like Event objects that have an embedded object
                # that has a cache_key, cache that also
                obj = item.object
                if hasattr(obj, 'cache_key'):
                    object_key = obj.cache_key
                    log.debug("setting key %s" % object_key)
                    cache.set(object_key, obj)
            cache.set(item_key, item)
            ids[idx] = item.xid
            idx += 1
        self._id_cache = ids

        # hmm. we need to rebuild the list cache key based on the
        # originating url; httpobject changes the _location element
        # on us, like for member urls with a preferred username
        # (the username-based urls change to xid urls)
        # list_key = self.cache_key
        list_key = 'listcache:' + args[0].split('?')[0]
        log.debug("setting key %s" % list_key)

        cache.set(list_key, ids)

    @property
    def cache_key(self):
        """Builds a key identifier for caching the list itself.

        This is "listcache:URL", where URL is the location of the
        endpoint requested (minus any query arguments, which are
        only used for scoping record set).

        """

        # ie: listcache:https://api.typepad.com/noun/<id>/noun.json
        key = ":".join(
            ["listcache", self._inst._location.split("?")[0]])
        return key

    def __getattr__(self, name):
        return getattr(self._inst, name)

    def _get_entries(self):
        return self._inst.entries

    def _set_entries(self, val):
        self._inst.entries = val

    entries = property(fget=_get_entries, fset=_set_entries)

    def make_sequence_method(methodname):
        """Makes a new function that proxies calls to `methodname` to the
        `_inst` attribute of the instance on which the function is called as
        an instance method."""
        def seqmethod(self, *args, **kwargs):
            # Proxy these methods to self._inst.entries.
            return getattr(self._inst.entries, methodname)(*args, **kwargs)
        seqmethod.__name__ = methodname
        return seqmethod

    __len__      = make_sequence_method('__len__')
    __setitem__  = make_sequence_method('__setitem__')
    __delitem__  = make_sequence_method('__delitem__')
    __iter__     = make_sequence_method('__iter__')
    __reversed__ = make_sequence_method('__reversed__')
    __contains__ = make_sequence_method('__contains__')

    def __getitem__(self, *args, **kwargs):
        return self._inst.__getitem__(*args, **kwargs)

    def filter(self, *args, **kwargs):
        """Passes through the requested filter operation to the underlying
        `ListObject`, but keeps track of any ``start_index`` and
        ``max_results`` arguments.

        """

        if not kwargs.get('cache', True):
            # if 'cache' is passed and is False, don't cache
            del kwargs['cache']
            return self._inst.filter(*args, **kwargs)

        if 'start_index' in kwargs:
            self._start = kwargs['start_index']
        if 'max_results' in kwargs:
            self._end = self._start + kwargs['max_results']

        kwargs['callback'] = CachingCallback(self)
        self._inst = self._inst.filter(*args, **kwargs)
        self._inst._cache_callback = kwargs['callback']
        return self


class CachedTypePadObject(object):

    """A caching class for wrapping a method that returns a single
    `TypePadObject`.

    When invoked, the original bound method is called, along with a
    callback argument that causes our cache to populate. If the object
    is already in the cache, it is simply returned instead of causing
    a subrequest.

    """

    cache_key = "objectcache:%s:%%s"

    def __init__(self, func):
        self.func = func
        self.cls = func.im_self
        self.cache_key = self.cache_key % func.im_self.__name__

    def __call__(self, *args, **kwargs):
        if not kwargs.get('cache', True):
            # if 'cache' is passed and is False, don't cache
            return self.func(*args, **kwargs)

        key = self.cache_key % args[0]
        obj = cache.get(key)
        if obj is not None:
            return obj

        # okay, do the work
        def cache_callback(*args, **kwargs):
            del obj._cache_callback
            obj.update_from_response(*args, **kwargs)
            log.debug("setting key %s" % key)
            cache.set(key, obj)

        kwargs['callback'] = cache_callback
        obj = self.func(*args, **kwargs)
        # this is so our callback reference doesn't disappear
        obj._cache_callback = cache_callback
        return obj

cache_object = CachedTypePadObject

def make_tpobject_cache_key(self):
    """Property method we will graft to TypePadObject to construct
    a cache key suitable for our caching layer.

    """

    return "objectcache:%s:%s" % (self.cache_namespace, self.xid)

typepad.TypePadObject.cache_key = property(make_tpobject_cache_key)

def make_tpobject_cache_namespace(self):
    """Provides a namespace for caching a class of objects.
    
    """

    return self.__class__.__name__

typepad.TypePadObject.cache_namespace = property(make_tpobject_cache_namespace)

class CachedTypePadLink(object):

    def __init__(self, link):
        self.link = link

    def __get__(self, obj, type=None, **kwargs):
        if obj is None:
            return self
        return CachedTypePadLinkPromise(self.link, obj, type, **kwargs)

cache_link = CachedTypePadLink


def _expand_cache_keys(item):
    if hasattr(item, 'cache_key'):
        value = item.cache_key
    else:
        value = item
    if isinstance(value, list):
        result = []
        for v in value:
            v = _expand_cache_keys(v)
            if v is None: continue
            if not isinstance(v, list): v = [v]
            result.extend(v)
        return result
    elif value is None:
        return []
    else:
        return [value]


class CacheInvalidator(object):
    """General-purpose class for Django cache invalidation.

    """

    def __init__(self, key, signals=None, name=None):
        self.key = key
        self.name = name

        # If signals are provided, attach to each of them.
        if signals is not None:
            for signal in signals:
                signal.connect(self)

    def cache_key(self, sender, **kwargs):
        """Calculates a cache key for the signal issued.

        If the source ``key`` is callable, defer to it and return the result.
        Otherwise, use the ``key`` member attribute as-is.

        """

        key = None
        if callable(self.key):
            key = self.key(sender, **kwargs)
        else:
            key = self.key

        return _expand_cache_keys(key)

    def __call__(self, sender, **kwargs):
        keys = self.cache_key(sender, **kwargs)
        for key in keys:
            log.debug("invalidating key %s" % key)
            cache.delete(key)


invalidate_rule = CacheInvalidator
