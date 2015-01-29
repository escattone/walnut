#
# The MIT License (MIT)
#
# Copyright (c) 2014,2015 Ryan Johnson
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import uuid

try:
    # Prefer simplejson.
    import simplejson as json
except ImportError:
    import json

from twisted.internet.defer import inlineCallbacks, maybeDeferred, returnValue
from walnut.utils import get_qualified_name, LogAdapter, wraps, make_key

try:
    import txredisapi
except ImportError:
    try:
        import txredis
    except ImportError:
        default_skip_on_errors = ()
    else:
        default_skip_on_errors = (txredis.exceptions.ConnectionError,)
else:
    default_skip_on_errors = (txredisapi.ConnectionError,)


SENTINEL = object()
EMPTY_JSON_MSG = json.dumps({})


GET_SCRIPT = """\
local owned = redis.call('setnx', KEYS[1], ARGV[1])
if owned == 1 then redis.call('del', KEYS[2]) end
return {owned, redis.call('lindex', KEYS[2], 0)}
"""


PUSH_AND_EXPIRE_SCRIPT = """return \
{redis.call('rpush', KEYS[1], ARGV[1]), redis.call('expire', KEYS[2], ARGV[2])}
"""


PUSH_AND_DELETE_SCRIPT = """return \
{redis.call('rpush', KEYS[1], ARGV[1]), redis.call('delete', KEYS[2])}
"""


class AsyncRedisCache(object):

    def __init__(self, redis=None, ttl=None, max_wait=None, namespace=None,
                 keymaker=None, skip_on_errors=None, **kw):
        if skip_on_errors is None:
            skip_on_errors = default_skip_on_errors

        self.ttl = ttl
        self.redis = redis
        self.namespace = namespace
        self.skip_on_errors = skip_on_errors
        self.keymaker = keymaker or make_key
        self.max_wait = 0 if max_wait is None else max_wait

        # These defaults can be over-ridden via kw arguments.
        self.key_sep = kw.get('key_sep', ':')
        self.lock_key_prefix = kw.get('lock_key_prefix', 'L')
        self.value_key_prefix = kw.get('value_key_prefix', 'V')
        self.id = kw['id'] if 'id' in kw else uuid.uuid4().hex

        if self.lock_key_prefix == self.value_key_prefix:
            raise ValueError('the "lock_key_prefix" and '
                             '"value_key_prefix" must differ')

    def __call__(self, func=None, **kw):
        if not func:
            kw2 = self.__dict__.copy()
            kw2.pop('id', None)
            kw2.update(kw)
            return self.__class__(**kw2)

        if not self.redis:
            raise ValueError('no redis client has been provided')

        if self.namespace is None:
            namespace = get_qualified_name(func)
        else:
            namespace = self.namespace

        key_sep = self.key_sep

        lock_key_base = self.lock_key_prefix + key_sep + namespace
        value_key_base = self.value_key_prefix + key_sep + namespace

        @inlineCallbacks
        @wraps(func)
        def wrapper(*args, **kw):
            # Get the key for this invocation of func.
            lock_key = lock_key_base
            value_key = value_key_base

            key = self.keymaker(func, args, kw)

            if key is not None:
                lock_key += key_sep + key
                value_key += key_sep + key

            keys = (lock_key, value_key)

            # Has someone else already produced or
            # started producing the value for this key?
            own_lock, json_msg = yield self.get_lock_or_cached_value(*keys)

            print 'own_lock={!r}, msg={!r}, keys={!r}'.format(own_lock,
                                                              json_msg,
                                                              keys)

            # How do I handle the case where at the time I check the
            # lock key, it's not expired by on the edge of expiring
            # such that by the time I check the value key, the value
            # key (which has the same expiration...or slightly more)
            # has expired.  Then I'm stuck waiting for a result that
            # may never come!
            #
            # 1) Don't ever expire the value key, just the lock key.

            if own_lock:
                # Nope, we own the task of computing the value.
                try:
                    value = yield maybeDeferred(func, *args, **kw)
                except:
                    try:
                        raise
                    finally:
                        # Before the error is re-raised, delete the lock
                        # key and signal the waiters that they're on their
                        # own.
                        self.log_skip(value_key, 'compute_value')
                        self.notify_waiters_and_release_lock(*keys)

                # Cache and push the value to the waiters, but don't wait.
                self.cache_value(*keys, value=value)

            else:
                if json_msg is None:
                    # The value has not yet been cached, so let's wait.
                    # If a max_wait was specified, only wait up to max_wait
                    # seconds, after which an empty JSON object will be
                    # returned
                    json_msg = yield self.wait_for_cached_value(value_key)

                msg = json.loads(json_msg)
                value = msg.get('content', SENTINEL)

                if value is SENTINEL:
                    value = yield maybeDeferred(func, *args, **kw)

            returnValue(value)

        return wrapper

    @inlineCallbacks
    def get_lock_or_cached_value(self, lock_key, value_key):
        """
        Try to acquire the lock and also get the cached value, if any.
        A tuple of two items is returned, first a boolean indicating
        whether or not the lock was acquired, and second the cached
        value or None if there was no cached value.

        There are three possible cases here:

        1) (True, None) -- We acquired the lock, either because the lock
           key has expired or because it has never been acquired before.
           This means that we are reponsible for computing and then caching
           the value.  If we acquire the lock, the cached value returned
           will always be None.
        2) (False, None) -- We did not acquire the lock, and there is not
           yet a cached value.  This means that someone else is already
           working on computing and caching the value, and we need to
           "wait" for the value to be cached.
        3) (False, JSON string) -- We did not acquire the lock, but we got
           the value (as JSON) that had already been computed and cached.
        """
        redis = self.redis
        try:
            own_lock, json_msg = yield redis.eval(GET_SCRIPT,
                                                  (lock_key, value_key),
                                                  (self.id,))
        except self.skip_on_errors:
            self.log_skip(value_key, 'get_lock_or_cached_value')
            own_lock, json_msg = False, EMPTY_JSON_MSG

        returnValue((bool(int(own_lock)), json_msg))

    @inlineCallbacks
    def wait_for_cached_value(self, value_key):
        """
        Get the JSON value from the cache, or wait until a value
        is cached.  If a max_wait was specified and no value has
        been cached within max_wait seconds, an empty JSON message
        is returned.  It is highly recommended that the user specify
        a max_wait timeout.  It should be greater than the reasonable
        maximum time in seconds it would take to compute the value and
        push it to redis.
        """
        try:
            json_msg = yield self.redis.brpoplpush(value_key, value_key,
                                                   self.max_wait)
        except self.skip_on_errors:
            self.log_skip(value_key, 'wait_for_cached_value')
            json_msg = None

        if json_msg is None:
            # Either a connection error or timeout.
            json_msg = EMPTY_JSON_MSG

        returnValue(json_msg)

    @inlineCallbacks
    def cache_value(self, lock_key, value_key, value):
        """
        Cache the value within the value key, which also pushes the value
        to all of the waiters, and set the time-to-live, if there is one,
        on the lock key.
        """
        json_msg = json.dumps(dict(content=value))

        try:
            if self.ttl:
                result = yield self.redis.eval(PUSH_AND_EXPIRE_SCRIPT,
                                               (value_key, lock_key),
                                               (json_msg, str(self.ttl)))
            else:
                print 'caching {!r}'.format(json_msg)
                result = yield self.redis.rpush(value_key, json_msg)
                print 'caching result {!r}'.format(result)
        except self.skip_on_errors:
            # Nothing left to do but log the error and let
            # the waiters timeout.
            self.log_skip(value_key, 'cache_value')
        else:
            # TODO: Only log something if the response is abnormal.
            log.info('cache_value(): redis response: {!r}'.format(result))

    @inlineCallbacks
    def notify_waiters_and_release_lock(self, lock_key, value_key):
        """
        Notify the waiters, with an empty message, to compute the value
        themselves, and delete the lock key.
        """
        try:
            result = yield self.redis.eval(PUSH_AND_DELETE_SCRIPT,
                                           (value_key, lock_key),
                                           (EMPTY_JSON_MSG,))
        except:
            log.exception('exception in '
                          'notify_waiters_and_release_lock():')
        else:
            # TODO: Only log something if the response is abnormal.
            msg = 'notify_waiters_and_release_lock(): redis response: {!r}'
            log.info(msg.format(result))

    def log_skip(self, value_key, method):
        msg = 'skipping cache for key {!r}: exception in {}():'
        log.exception(msg.format(value_key, method))


async_cache = AsyncRedisCache()
