# Copyright (c) 2009 Six Apart Ltd.
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

from functools import wraps
import logging
from django.core.cache import cache
import typepad

log = logging.getLogger('typepadapp.cache')


class CachedTypePadObject(object):

    key_pattern = "objectcache:%s"

    def __init__(self, cls, invalidate_signals=None):
        if invalidate_signals is not None:
            for signal in invalidate_signals:
                signal.connect(self.clear_cache)

    def clear_cache(self, sender, **kwargs):
        key = self.key_pattern % kwargs['instance'].xid
        log.debug("Clearing objectcache for key %s" % key)
        cache.delete(key)

    def __call__(self, func):

        @classmethod
        @wraps(func)
        def wrapper(cls, *args, **kwargs):
            key = self.key_pattern % args[0]
            obj = cache.get(key)
            if obj is not None:
                log.debug("supplying object from cache for key %s" % key)
                return obj

            # okay, do the work
            def cache_callback(*args, **kwargs):
                del obj._cache_callback
                obj.update_from_response(*args, **kwargs)
                log.debug("populating object cache for key %s" % key)
                cache.set(key, obj)

            log.debug("calling filling function for object with key %s" % key)
            obj = func(*args, callback=cache_callback, **kwargs)
            # this is so our callback reference doesn't disappear
            obj._cache_callback = cache_callback
            return obj

        return wrapper

cached_object = CachedTypePadObject


class CachedTypePadList(object):

    # ie: listcache:LISTID:INSTANCEID:PREFIX
    list_key_pattern = "listcache:%s:%%s:%%s"
    # ie: objectcache:INSTANCEID
    item_key_pattern = "objectcache:%s"
    item_class = None
    by_group = False

    def __init__(self, cls, by_group=False, invalidate_signals=None):
        """This is the routine called with the arguments to the decorator.
        
        Ie; @decorator(1,2,3)

        """
        self.item_class = cls
        self.by_group = by_group

        if invalidate_signals is not None:
            for signal in invalidate_signals:
                signal.connect(self.clear_cache)

    def clear_cache(self, sender, **kwargs):
        obj = kwargs['instance']
        cache_key = self.item_key_pattern % obj.xid
        cache.delete(cache_key)

        # now, clear the cache for the list itself
        if self.by_group and 'group' in kwargs:
            group = kwargs['group']
            list_key = self.list_key_pattern % (group.xid, group.cache_prefix())
        elif 'parent' in kwargs:
            parent = kwargs['parent']

            cache_key = self.item_key_pattern % parent.xid
            log.debug("Clearing objectcache for parent asset; cache_key is %s" % cache_key)
            cache.delete(cache_key)
            # effectly reset any caches prefixed for this asset
            try:
                cache.incr(str('cacheprefix:%s:%s' % (self.item_class.__name__, parent.xid)))
            except ValueError:
                # ignore in the event that the prefix doesn't exist
                pass

            list_key = self.list_key_pattern % (parent.xid, parent.cache_prefix())
        else:
            list_key = self.list_key_pattern % (obj.xid, obj.cache_prefix())
        log.debug("Clearing listcache for key %s" % list_key)
        cache.delete(list_key)

    def __call__(self, func):
        """This is the routine called to wrap the function.
        
        The return value from this routine is the function wrapper that
        accepts the same signature as the wrapped function.
        """

        self.list_key_pattern = self.list_key_pattern % func.__name__

        @wraps(func)
        def wrapper(obj, *args, **kwargs):
            list_key = self.list_key_pattern % (obj.xid, obj.cache_prefix())
            group = kwargs.get('by_group', None)
            if group is not None:
                list_key += ':' + group.xid + ':' + group.cache_prefix()
            start = kwargs.get('start_index', 1)
            end = start + kwargs.get('max_results', 50)
            ids = cache.get(list_key)
            items = None

            if ids is not None:
                items = []

                if ids[0] > 0:
                    if end > ids[0]:
                        end = ids[0] + 1

                    subset = ids[start:end]
                    itemkeys = []
                    if None not in subset:
                        # if one of our elements is empty, we force a new
                        # request.
                        for id in subset:
                            itemkeys.append(self.item_key_pattern % id)
                    else:
                        log.debug("we had a None in our subset; start %d, end %d, key %s" % (start, end, list_key))

                    if len(itemkeys) > 0:
                        itemdict = cache.get_many(itemkeys)
                        for key in itemkeys:
                            if key not in itemdict or itemdict[key] is None:
                                log.debug("missing element for cached list, key %s" % list_key)
                                items = None
                                break
                            items.append(itemdict[key])

                if (items is not None) and ((len(items) > 0) or (ids[0] == 0)):
                    l = typepad.ListObject()
                    l._delivered = True
                    l.entries = items
                    l.start_index = start
                    l.total_results = ids[0]
                    log.debug("supplying list from cache for key %s" % list_key)
                    return l
            else:
                ids = [0]

            while len(ids) < end:
                ids.append(None)

            # okay, do the work
            def cache_callback(*args, **kwargs):
                del items._cache_callback
                items.update_from_response(*args, **kwargs)
                ids[0] = items.total_results
                idx = start
                log.debug("populating list cache for key %s" % list_key)
                for item in items.entries:
                    item_key = self.item_key_pattern % item.xid
                    cache.set(item_key, item)
                    ids[idx] = item.xid
                    idx += 1
                cache.set(list_key, ids)

            log.debug("calling filling function for list with key %s" % list_key)
            kwargs['callback'] = cache_callback
            items = func(obj, *args, **kwargs)
            # this is so our callback reference doesn't disappear
            items._cache_callback = cache_callback
            return items

        return wrapper

cached_list = CachedTypePadList
