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

import json
import uuid
from types import NoneType

from twisted.python import failure
from twisted.internet.defer import Deferred, maybeDeferred
from twisted.internet.defer import inlineCallbacks, returnValue
from walnut.utils import get_qualified_name, LogAdapter, wraps, make_key


default_skip_cache_on = ()
try:
    import txredisapi
except ImportError:
    pass
else:
    default_skip_cache_on += (txredisapi.ConnectionError,)
try:
    import txredis
except ImportError:
    pass
else:
    default_skip_cache_on += (txredis.ConnectionError,)


SENTINEL = object()


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


def async_cache(func=None, redis=None, ttl=None, max_wait=None, keymaker=None,
                skip_cache_on=None, namespace=None, json_encode_func=None,
                json_decode_func=None, id_tag=None, key_sep=':',
                lock_key_prefix='L', value_key_prefix='V'):

    if not ((ttl is None) or (ttl > 0)):
        raise ValueError('"ttl" must be greater than zero or None')

    if not ((max_wait is None) or (max_wait >= 0)):
        raise ValueError('"max_wait" must be greater than or equal to zero')

    if not ((keymaker is None) or callable(keymaker)):
        raise ValueError('"keymaker" must be a callable or None')

    if not isinstance(skip_cache_on, (type, tuple, NoneType)):
        raise ValueError('"skip_cache_on" must be an exception class, '
                         'a tuple of exception classes, or None')

    if not isinstance(namespace, (basestring, NoneType)):
        raise ValueError('"namespace" must be a string or None')

    if not ((json_encode_func is None) or callable(json_encode_func)):
        raise ValueError('"json_encode_func" must be a callable or None')

    if not ((json_decode_func is None) or callable(json_decode_func)):
        raise ValueError('"json_decode_func" must be a callable or None')

    if not isinstance(id_tag, (basestring, NoneType)):
        raise ValueError('"id_tag" must be a string or None')

    if not isinstance(key_sep, basestring):
        raise ValueError('"key_sep" must be a string')

    if not isinstance(lock_key_prefix, basestring):
        raise ValueError('"lock_key_prefix" must be a string')

    if not isinstance(value_key_prefix, basestring):
        raise ValueError('"value_key_prefix" must be a string')

    if lock_key_prefix == value_key_prefix:
        raise ValueError('"lock_key_prefix" cannot equal "value_key_prefix"')

    if not func:
        return functools.partial(async_cache, redis=redis, ttl=ttl,
                                 max_wait=max_wait, keymaker=keymaker,
                                 skip_cache_on=skip_cache_on, id_tag=id_tag,
                                 namespace=namespace, key_sep=key_sep,
                                 json_decode_func=json_decode_func,
                                 json_encode_func=json_encode_func,
                                 value_key_prefix=value_key_prefix,
                                 lock_key_prefix=lock_key_prefix)

    if max_wait is None:
        max_wait = 0

    if keymaker is None:
        keymaker = make_key

    if skip_cache_on is None:
        skip_cache_on = default_skip_cache_on

    if namespace is None:
        namespace = get_qualified_name(func)

    if json_decode_func is None:
        json_decode_func = json.loads

    if json_encode_func is None:
        json_encode_func = functools.partial(json.dumps, separators=(',',':'))

    if id_tag is None:
        id_tag = namespace + '.' + uuid.uuid4().hex

    lock_key_base = lock_key_prefix + key_sep + namespace
    value_key_base = value_key_prefix + key_sep + namespace

    EMPTY_JSON_MSG = json_encode_func({})

    local_waiters = dict()

    @inlineCallbacks
    def get_computed_or_redis_value(key, args, kwargs):

        def log_skip(name):
            log.exception('skipping cache for key {!r}: exception in "{}":',
                          value_key, name)

        @inlineCallbacks
        def get_lock_or_cached_value():
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
            try:
                own_lock, json_msg = yield redis.eval(GET_SCRIPT,
                                                      (lock_key, value_key),
                                                      (id_tag,))
            except skip_cache_on:
                log_skip('get_lock_or_cached_value')
                own_lock, json_msg = False, EMPTY_JSON_MSG

            returnValue((bool(int(own_lock)), json_msg))

        @inlineCallbacks
        def notify_waiters_and_release_lock():
            """
            Notify the waiters, with an empty message, to compute the value
            themselves, and delete the lock key.
            """
            try:
                result = yield redis.eval(PUSH_AND_DELETE_SCRIPT,
                                          (value_key, lock_key),
                                          (EMPTY_JSON_MSG,))
            except:
                log.exception('exception in '
                              'notify_waiters_and_release_lock():')
            else:
                # TODO: Only log something if the response is abnormal.
                msg = 'notify_waiters_and_release_lock(): redis response: {!r}'
                log.info(msg, result)

        @inlineCallbacks
        def cache_value(value):
            """
            Cache the value within the value key, which also pushes the value
            to all of the waiters, and set the time-to-live, if there is one,
            on the lock key.
            """
            json_msg = json_encode_func(dict(content=value))

            try:
                if ttl:
                    result = yield redis.eval(PUSH_AND_EXPIRE_SCRIPT,
                                              (value_key, lock_key),
                                              (json_msg, str(ttl)))
                else:
                    print 'caching {!r}'.format(json_msg)
                    result = yield redis.rpush(value_key, json_msg)
                    print 'caching result {!r}'.format(result)
            except skip_cache_on:
                # Nothing left to do but log the error and let
                # the waiters timeout.
                log_skip('cache_value')
            else:
                # TODO: Only log something if the response is abnormal.
                log.info('cache_value(): redis response: {!r}'.format(result))

        @inlineCallbacks
        def wait_for_cached_value():
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
                json_msg = yield redis.brpoplpush(value_key, value_key,
                                                  max_wait)
            except skip_cache_on:
                log_skip('wait_for_cached_value')
                json_msg = None

            if json_msg is None:
                # Either a connection error or timeout.
                json_msg = EMPTY_JSON_MSG

            returnValue(json_msg)

        # Build the redis keys for this invocation of func.
        lock_key = lock_key_base
        value_key = value_key_base

        if key is not None:
            lock_key += key_sep + key
            value_key += key_sep + key

        # Has someone else already produced or
        # started producing the value for this key?
        own_lock, json_msg = yield get_lock_or_cached_value()

        print 'own_lock={!r}, msg={!r}'.format(own_lock, json_msg)
        print 'value_key={!r}, lock_key={!r}'.format(value_key, lock_key)

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
                value = yield maybeDeferred(func, *args, **kwargs)
            except:
                try:
                    raise
                finally:
                    # Before the error is re-raised, delete the lock
                    # key and signal the waiters that they're on their
                    # own.
                    notify_waiters_and_release_lock()
            else:
                # Cache and push the value to the waiters, but don't wait.
                cache_value(value)

        else:
            if json_msg is None:
                # The value has not yet been cached, so let's wait.
                # If a max_wait was specified, only wait up to max_wait
                # seconds, after which an empty JSON object will be
                # returned
                json_msg = yield wait_for_cached_value()

            msg = json_decode_func(json_msg)
            value = msg.get('content', SENTINEL)

            if value is SENTINEL:
                value = yield maybeDeferred(func, *args, **kw)

        returnValue(value)

    def schedule_local_waiters(key, value=SENTINEL):
        """
        Schedule the callback or errback of each of the local
        waiters for this key.
        """
        deferreds = local_waiters.pop(key)
        if deferreds:
            from twisted.internet import reactor
            for deferred in deferreds:
                if value is SENTINEL:
                    reactor.callLater(0, deferred.errback, failure.Failure())
                else:
                    reactor.callLater(0, deferred.callback, value)

    @inlineCallbacks
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Get the key for this invocation of func.
        key = keymaker(func, args, kwargs)

        if key in local_waiters:
            # Within this process, there has already been a call of func
            # made with the same key, so a value is already being computed
            # or acquired from Redis.  Instead of initiating another
            # connection to Redis from this process for the same key, just
            # "wait" for the result already in progress.
            deferred = Deferred()
            local_waiters[key].append(deferred)
            value = yield deferred
        else:
            local_waiters[key] = []
            try:
                value = yield get_computed_or_redis_value(key, args, kwargs)
            except:
                try:
                    raise
                finally:
                    # Before the error is re-raised, schedule the error
                    # callbacks on all local waiters for this key, if any.
                    schedule_local_waiters(key)
            else:
                # Before returning the value, schedule the callbacks
                # for all local waiters for this key, if any.
                schedule_local_waiters(key, value)

        returnValue(value)

    return wrapper
