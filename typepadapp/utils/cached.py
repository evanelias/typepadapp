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

import logging
from django.core.cache import cache


class CachedProperty(object):
    """ Cached property descriptor.
        The object with the cached property
        must also have an id property.
        This is still very much in-progress.
    """

    def __init__(self, func):
        self.func = func

    def key(self, obj):
        return 'CachedProperty_%s_%s_%s' % \
            (obj.__class__.__name__, self.func.__name__, obj._location)

    def __get__(self, obj, type=None):
        key = self.key(obj)
        # local memory
        if not hasattr(self, key):
            # cache system
            val = cache.get(key)
            if val is None:
                # expensive
                val = self.func(obj)
                cache.set(key, val)
                logging.debug('%s from db' % key)
            else:
                logging.debug('%s from cache' % key)
            setattr(self, key, val)
        else:
            logging.debug('%s from mem' % key)
        return getattr(self, key)

    def __delete__(self, obj):
        # hmm... use this to clear the cache
        key = self.key(obj)
        delattr(self, key)
        cache.delete(key)

# pretty decorator
cached_property = CachedProperty

def cached_function(func):
    """ Pretty decorator for functions. """

    cached = CachedProperty(func)

    def cached_func(self):
        return cached.__get__(self)

    return cached_func